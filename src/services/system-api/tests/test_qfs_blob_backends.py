from __future__ import annotations

import io

from system_api.qfs_store import (
    ArtifactMetadata,
    LocalBlobBackend,
    QFSLayoutValidator,
    QFSMetadataIndex,
    QFSRetentionExecutor,
    QFSStore,
    RetryConfig,
    S3BlobBackend,
)


class _FlakyBackend(LocalBlobBackend):
    def __init__(self, failures: int):
        super().__init__()
        self._failures = failures

    def upload_bytes(self, ref: str, payload: bytes) -> None:
        if self._failures > 0:
            self._failures -= 1
            raise RuntimeError("transient")
        super().upload_bytes(ref, payload)


class _MockPaginator:
    def __init__(self, client):
        self._client = client

    def paginate(self, *, Bucket: str, Prefix: str):
        yield {
            "Contents": [
                {"Key": key}
                for key in sorted(self._client.storage)
                if key.startswith(Prefix)
            ]
        }


class _MockS3Client:
    def __init__(self):
        self.storage: dict[str, bytes] = {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes):
        self.storage[Key] = bytes(Body)

    def get_object(self, *, Bucket: str, Key: str):
        if Key not in self.storage:
            err = Exception("NoSuchKey")
            err.response = {"Error": {"Code": "NoSuchKey"}}
            raise err
        return {"Body": io.BytesIO(self.storage[Key])}

    def delete_object(self, *, Bucket: str, Key: str):
        self.storage.pop(Key, None)

    def copy_object(self, *, Bucket: str, Key: str, CopySource: dict[str, str]):
        self.storage[Key] = self.storage[CopySource["Key"]]

    def get_paginator(self, name: str):
        assert name == "list_objects_v2"
        return _MockPaginator(self)


def test_qfs_store_retries_and_succeeds_on_primary_backend():
    flaky = _FlakyBackend(failures=2)
    store = QFSStore([flaky], retry=RetryConfig(max_attempts=3, backoff_ms=0))

    store.put_bytes("qfs://jobs/retry.bin", b"ok")

    assert store.get_bytes("qfs://jobs/retry.bin") == b"ok"


def test_qfs_store_fails_over_to_secondary_backend():
    broken = _FlakyBackend(failures=10)
    fallback = LocalBlobBackend()
    store = QFSStore([broken, fallback], retry=RetryConfig(max_attempts=1, backoff_ms=0))

    store.put_bytes("qfs://jobs/fallback.bin", b"ok")

    assert fallback.download_bytes("qfs://jobs/fallback.bin") == b"ok"


def test_s3_backend_upload_download_list_and_atomic_write():
    mock = _MockS3Client()
    backend = S3BlobBackend(bucket="test-bucket", client=mock)

    backend.upload_bytes("qfs://jobs/1/file.bin", b"payload")
    backend.atomic_write("qfs://jobs/1/results.parquet", b"rows")

    assert backend.download_bytes("qfs://jobs/1/file.bin") == b"payload"
    assert backend.download_bytes("qfs://jobs/1/results.parquet") == b"rows"
    assert backend.list_refs("qfs://jobs/1/") == [
        "qfs://jobs/1/file.bin",
        "qfs://jobs/1/results.parquet",
    ]

def test_qfs_layout_validator_has_stable_diagnostics():
    store = QFSStore([LocalBlobBackend()])
    job_id = "job-layout"
    store.put_bytes(f"qfs://jobs/{job_id}/input/job.yaml", b"a")

    result = QFSLayoutValidator.validate_job_layout(store=store, job_id=job_id, require_results=True)

    assert result.ok is False
    assert result.missing_required == [
        f"qfs://jobs/{job_id}/compiled/circuit.aqo.json",
        f"qfs://jobs/{job_id}/input/program.eigen.py",
        f"qfs://jobs/{job_id}/results.parquet",
    ]
    assert result.diagnostics == [
        f"MISSING_REQUIRED:qfs://jobs/{job_id}/compiled/circuit.aqo.json",
        f"MISSING_REQUIRED:qfs://jobs/{job_id}/input/program.eigen.py",
        f"MISSING_REQUIRED:qfs://jobs/{job_id}/results.parquet",
    ]


def test_qfs_retention_executor_uses_deterministic_reason_codes():
    store = QFSStore([LocalBlobBackend()])
    index = QFSMetadataIndex()
    now = 2_000
    kept_ref = "qfs://jobs/j1/results.parquet"
    expired_ref = "qfs://jobs/j1/logs/dispatch.log"
    orphan_ref = "qfs://jobs/j2/tmp/request.json"
    store.put_bytes(kept_ref, b"k")
    store.put_bytes(expired_ref, b"e")
    store.put_bytes(orphan_ref, b"o")
    index.upsert(
        ArtifactMetadata(
            qfs_ref=kept_ref,
            job_id="j1",
            trace_id="tr-1",
            stage="execute",
            artifact_type="results",
            created_at_epoch_ms=1_000,
            retention_until_epoch_ms=5_000,
        )
    )
    index.upsert(
        ArtifactMetadata(
            qfs_ref=expired_ref,
            job_id="j1",
            trace_id="tr-1",
            stage="execute",
            artifact_type="log",
            created_at_epoch_ms=1_000,
            retention_until_epoch_ms=1_500,
        )
    )

    events = QFSRetentionExecutor.run(store=store, index=index, now_epoch_ms=now)

    assert [(item.qfs_ref, item.reason_code) for item in events] == [
        (expired_ref, QFSRetentionExecutor.REASON_RETENTION_EXPIRED),
        (orphan_ref, QFSRetentionExecutor.REASON_ORPHAN_NOT_INDEXED),
    ]
    assert store.get_bytes(kept_ref) == b"k"
    assert store.get_bytes(expired_ref) is None
    assert store.get_bytes(orphan_ref) is None
    