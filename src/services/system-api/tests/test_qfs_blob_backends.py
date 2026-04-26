from __future__ import annotations

import io

from system_api.qfs_store import LocalBlobBackend, QFSStore, RetryConfig, S3BlobBackend


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
