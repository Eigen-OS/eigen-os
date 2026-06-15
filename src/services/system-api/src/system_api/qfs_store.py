"""QFS storage facade with pluggable local and S3-compatible blob backends."""

from __future__ import annotations

import os
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from datetime import UTC, datetime
from typing import Callable, Protocol


class BlobBackend(Protocol):
    """Backend contract for byte-oriented object storage."""

    def upload_bytes(self, ref: str, payload: bytes) -> None: ...

    def download_bytes(self, ref: str) -> bytes | None: ...

    def list_refs(self, prefix: str) -> list[str]: ...

    def delete_ref(self, ref: str) -> None: ...

    def delete_prefix(self, prefix: str) -> None: ...

    def clear(self) -> None: ...

    def atomic_write(self, ref: str, payload: bytes) -> None: ...


class LocalBlobBackend:
    """Thread-safe local filesystem backend for qfs:// refs."""

    def __init__(self):
        self._root = self._select_root()
        self._lock = threading.RLock()

    @staticmethod
    def _candidate_roots() -> list[Path]:
        roots: list[Path] = []
        env_root = os.getenv("EIGEN_QFS_LOCAL_ROOT")
        if env_root:
            roots.append(Path(env_root))
        roots.extend([
            Path("/tmp/eigen/qfs"),
            Path(tempfile.gettempdir()) / "eigen" / "qfs",
        ])
        return roots

    def _select_root(self) -> Path:
        last_exc: Exception | None = None
        for root in self._candidate_roots():
            try:
                root.mkdir(parents=True, exist_ok=True)
                probe = root / f".probe-{threading.get_ident()}-{time.monotonic_ns()}"
                probe.write_bytes(b"")
                probe.unlink(missing_ok=True)
                return root
            except Exception as exc:  # pragma: no cover - environment dependent
                last_exc = exc
        raise RuntimeError("unable to initialize writable QFS root") from last_exc


    def _ref_path(self, ref: str) -> Path:
        rel = ref[len("qfs://") :] if ref.startswith("qfs://") else ref
        path = (self._root / rel).resolve()
        root = self._root.resolve()
        if root not in path.parents and path != root:
            raise ValueError(f"invalid qfs ref: {ref}")
        return path

    def upload_bytes(self, ref: str, payload: bytes) -> None:
        with self._lock:
            path = self._ref_path(ref)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + f".tmp-{threading.get_ident()}-{time.monotonic_ns()}")
            tmp.write_bytes(payload)
            tmp.replace(path)

    def download_bytes(self, ref: str) -> bytes | None:
        with self._lock:
            path = self._ref_path(ref)
            return None if not path.exists() else path.read_bytes()

    def list_refs(self, prefix: str) -> list[str]:
        with self._lock:
            root = self._root.resolve()
            if not root.exists():
                return []
            refs: list[str] = []
            for path in root.rglob("*"):
                if path.is_file():
                    rel = path.relative_to(root).as_posix()
                    ref = f"qfs://{rel}"
                    if ref.startswith(prefix):
                        refs.append(ref)
            return sorted(refs)

    def delete_ref(self, ref: str) -> None:
        with self._lock:
            path = self._ref_path(ref)
            if path.exists():
                path.unlink()

    def delete_prefix(self, prefix: str) -> None:
        with self._lock:
            for ref in self.list_refs(prefix):
                self.delete_ref(ref)
    def clear(self) -> None:
        with self._lock:
            if self._root.exists():
                for path in sorted(self._root.rglob("*"), reverse=True):
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        try:
                            path.rmdir()
                        except OSError:
                            pass

    def atomic_write(self, ref: str, payload: bytes) -> None:
        with self._lock:
            self.upload_bytes(ref, payload)


class S3BlobBackend:
    """S3-compatible backend for qfs:// refs."""

    def __init__(self, *, bucket: str, endpoint_url: str | None = None, client=None):
        if client is None:
            try:
                import boto3
            except ModuleNotFoundError as exc:
                raise RuntimeError("boto3 is required for S3 backend") from exc
            client = boto3.client("s3", endpoint_url=endpoint_url)
        self._bucket = bucket
        self._client = client

    @staticmethod
    def _to_key(ref: str) -> str:
        return ref[len("qfs://") :] if ref.startswith("qfs://") else ref

    def upload_bytes(self, ref: str, payload: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=self._to_key(ref), Body=payload)

    def download_bytes(self, ref: str) -> bytes | None:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=self._to_key(ref))
        except Exception as exc:  # botocore exceptions are optional imports
            if exc.__class__.__name__ in {"NoSuchKey", "ClientError"}:
                code = getattr(exc, "response", {}).get("Error", {}).get("Code")
                if code in {"NoSuchKey", "404", "NotFound"}:
                    return None
            raise
        body = resp["Body"].read()
        return bytes(body)

    def list_refs(self, prefix: str) -> list[str]:
        s3_prefix = self._to_key(prefix)
        paginator = self._client.get_paginator("list_objects_v2")
        refs: list[str] = []
        for page in paginator.paginate(Bucket=self._bucket, Prefix=s3_prefix):
            for item in page.get("Contents", []):
                refs.append(f"qfs://{item['Key']}")
        refs.sort()
        return refs

    def delete_ref(self, ref: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=self._to_key(ref))

    def delete_prefix(self, prefix: str) -> None:
        for ref in self.list_refs(prefix):
            self.delete_ref(ref)

    def clear(self) -> None:
        for ref in self.list_refs("qfs://"):
            self.delete_ref(ref)

    def atomic_write(self, ref: str, payload: bytes) -> None:
        key = self._to_key(ref)
        tmp = f"{key}.tmp-{time.monotonic_ns()}"
        self._client.put_object(Bucket=self._bucket, Key=tmp, Body=payload)
        self._client.copy_object(
            Bucket=self._bucket,
            Key=key,
            CopySource={"Bucket": self._bucket, "Key": tmp},
        )
        self._client.delete_object(Bucket=self._bucket, Key=tmp)


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 3
    backoff_ms: int = 25


class QFSStore:
    """Retrying storage facade with optional backend failover."""

    def __init__(self, backends: list[BlobBackend], *, retry: RetryConfig = RetryConfig()):
        if not backends:
            raise ValueError("QFSStore requires at least one backend")
        self._backends = backends
        self._retry = retry

    def _run(self, op: Callable[[BlobBackend], object]) -> object:
        last_exc: Exception | None = None
        for attempt in range(self._retry.max_attempts):
            for backend in self._backends:
                try:
                    return op(backend)
                except Exception as exc:  # pragma: no cover - backend-dependent
                    last_exc = exc
            if attempt + 1 < self._retry.max_attempts:
                time.sleep(self._retry.backoff_ms / 1000)
        assert last_exc is not None
        raise last_exc

    def put_bytes(self, qfs_ref: str, payload: bytes) -> None:
        self._run(lambda backend: backend.upload_bytes(qfs_ref, payload))

    def atomic_write_bytes(self, qfs_ref: str, payload: bytes) -> None:
        self._run(lambda backend: backend.atomic_write(qfs_ref, payload))

    def get_bytes(self, qfs_ref: str) -> bytes | None:
        return self._run(lambda backend: backend.download_bytes(qfs_ref))  # type: ignore[return-value]

    def list_refs(self, prefix: str) -> list[str]:
        return self._run(lambda backend: backend.list_refs(prefix))  # type: ignore[return-value]

    def delete_bytes(self, qfs_ref: str) -> None:
        self._run(lambda backend: backend.delete_ref(qfs_ref))

    def delete_prefix(self, prefix: str) -> None:
        self._run(lambda backend: backend.delete_prefix(prefix))

    def clear(self) -> None:
        self._run(lambda backend: backend.clear())


def _build_qfs_store_from_env() -> QFSStore:
    backend_name = os.getenv("EIGEN_QFS_BACKEND", "local").lower()
    retry = RetryConfig(
        max_attempts=int(os.getenv("EIGEN_QFS_RETRY_ATTEMPTS", "3")),
        backoff_ms=int(os.getenv("EIGEN_QFS_RETRY_BACKOFF_MS", "25")),
    )

    primary: BlobBackend
    fallback: list[BlobBackend] = []

    if backend_name == "s3":
        bucket = os.getenv("EIGEN_QFS_S3_BUCKET", "eigen-qfs")
        endpoint = os.getenv("EIGEN_QFS_S3_ENDPOINT")
        primary = S3BlobBackend(bucket=bucket, endpoint_url=endpoint)
        fallback.append(LocalBlobBackend())
    else:
        primary = LocalBlobBackend()

    return QFSStore([primary, *fallback], retry=retry)


class _QFSStoreProxy:
    def _store(self) -> QFSStore:
        return _build_qfs_store_from_env()

    def put_bytes(self, qfs_ref: str, payload: bytes) -> None:
        self._store().put_bytes(qfs_ref, payload)

    def atomic_write_bytes(self, qfs_ref: str, payload: bytes) -> None:
        self._store().atomic_write_bytes(qfs_ref, payload)

    def get_bytes(self, qfs_ref: str) -> bytes | None:
        return self._store().get_bytes(qfs_ref)

    def list_refs(self, prefix: str) -> list[str]:
        return self._store().list_refs(prefix)

    def delete_bytes(self, qfs_ref: str) -> None:
        self._store().delete_bytes(qfs_ref)

    def delete_prefix(self, prefix: str) -> None:
        self._store().delete_prefix(prefix)

    def clear(self) -> None:
        self._store().clear()


QFS_STORE = _QFSStoreProxy()

QFS_L3_ARTIFACT_CONTRACT_VERSION = "1.0.0"

_JOB_LAYOUT_REQUIRED_REFS = (
    "input/job.yaml",
    "input/program.eigen.py",
    "compiled/circuit.aqo.json",
)


@dataclass(frozen=True)
class ArtifactMetadata:
    qfs_ref: str
    job_id: str
    trace_id: str
    stage: str
    artifact_type: str
    created_at_epoch_ms: int
    retention_until_epoch_ms: int


@dataclass(frozen=True)
class LayoutValidationResult:
    ok: bool
    diagnostics: list[str]
    missing_required: list[str]


@dataclass(frozen=True)
class RetentionCleanupEvent:
    qfs_ref: str
    reason_code: str


@dataclass(frozen=True)
class CheckpointArtifact:
    checkpoint_id: str
    qfs_ref: str
    payload: bytes
    created_at_epoch_ms: int
    retention_until_epoch_ms: int


class CheckpointQuotaExceededError(RuntimeError):
    """Deterministic quota failure for QFS-L2 checkpoint artifacts."""

    def __init__(self, *, reason_code: str, detail: str):
        super().__init__(f"{reason_code}:{detail}")
        self.reason_code = reason_code
        self.detail = detail


@dataclass(frozen=True)
class CheckpointQuotaPolicy:
    max_artifacts: int
    max_total_bytes: int


@dataclass(frozen=True)
class RestoreCacheEvent:
    checkpoint_id: str
    reason_code: str


class CheckpointCatalog:
    """In-memory checkpoint catalog with deterministic quota + retention semantics."""

    REASON_QUOTA_ARTIFACTS_EXCEEDED = "QUOTA_ARTIFACTS_EXCEEDED"
    REASON_QUOTA_BYTES_EXCEEDED = "QUOTA_BYTES_EXCEEDED"
    REASON_RETENTION_WINDOW_EXPIRED = "RETENTION_WINDOW_EXPIRED"

    def __init__(self, *, quota: CheckpointQuotaPolicy):
        self._quota = quota
        self._items: dict[str, CheckpointArtifact] = {}
        self._lock = threading.RLock()

    def upsert(self, artifact: CheckpointArtifact) -> None:
        if artifact.retention_until_epoch_ms < artifact.created_at_epoch_ms:
            raise ValueError(f"{self.REASON_RETENTION_WINDOW_EXPIRED}:retention_until must be >= created_at")
        with self._lock:
            existing = self._items.get(artifact.checkpoint_id)
            current_count = len(self._items) - (1 if existing is not None else 0)
            if current_count + 1 > self._quota.max_artifacts:
                raise CheckpointQuotaExceededError(
                    reason_code=self.REASON_QUOTA_ARTIFACTS_EXCEEDED,
                    detail=f"max_artifacts={self._quota.max_artifacts}",
                )
            current_bytes = sum(len(item.payload) for item in self._items.values()) - (len(existing.payload) if existing is not None else 0)
            projected_bytes = current_bytes + len(artifact.payload)
            if projected_bytes > self._quota.max_total_bytes:
                raise CheckpointQuotaExceededError(
                    reason_code=self.REASON_QUOTA_BYTES_EXCEEDED,
                    detail=f"max_total_bytes={self._quota.max_total_bytes};projected_bytes={projected_bytes}",
                )
            self._items[artifact.checkpoint_id] = artifact

    def get(self, checkpoint_id: str, *, now_epoch_ms: int | None = None) -> CheckpointArtifact | None:
        now_ms = now_epoch_ms if now_epoch_ms is not None else int(datetime.now(tz=UTC).timestamp() * 1000)
        with self._lock:
            artifact = self._items.get(checkpoint_id)
            if artifact is None:
                return None
            if now_ms >= artifact.retention_until_epoch_ms:
                del self._items[checkpoint_id]
                return None
            return artifact


class QFSRestoreCache:
    """Deterministic LRU restore cache with observable eviction diagnostics."""

    REASON_CACHE_EVICTED_LRU = "CACHE_EVICTED_LRU"
    REASON_CACHE_MISS = "CACHE_MISS"
    REASON_CACHE_HIT = "CACHE_HIT"

    def __init__(self, *, capacity: int):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self._capacity = capacity
        self._cache: dict[str, bytes] = {}
        self._last_access_ns: dict[str, int] = {}
        self._clock = 0
        self._lock = threading.RLock()
        self._events: list[RestoreCacheEvent] = []

    def put(self, checkpoint_id: str, payload: bytes) -> None:
        with self._lock:
            self._clock += 1
            self._cache[checkpoint_id] = bytes(payload)
            self._last_access_ns[checkpoint_id] = self._clock
            while len(self._cache) > self._capacity:
                evicted = min(self._last_access_ns, key=lambda key: (self._last_access_ns[key], key))
                del self._cache[evicted]
                del self._last_access_ns[evicted]
                self._events.append(RestoreCacheEvent(checkpoint_id=evicted, reason_code=self.REASON_CACHE_EVICTED_LRU))

    def get(self, checkpoint_id: str) -> bytes | None:
        with self._lock:
            payload = self._cache.get(checkpoint_id)
            if payload is None:
                self._events.append(RestoreCacheEvent(checkpoint_id=checkpoint_id, reason_code=self.REASON_CACHE_MISS))
                return None
            self._clock += 1
            self._last_access_ns[checkpoint_id] = self._clock
            self._events.append(RestoreCacheEvent(checkpoint_id=checkpoint_id, reason_code=self.REASON_CACHE_HIT))
            return bytes(payload)

    def consume_events(self) -> list[RestoreCacheEvent]:
        with self._lock:
            events = list(self._events)
            self._events.clear()
            return events


class QFSLayoutValidator:
    """Deterministic QFS-L3 layout validator with stable diagnostics."""

    @staticmethod
    def validate_job_layout(*, store: QFSStore, job_id: str, require_results: bool = False) -> LayoutValidationResult:
        base = f"qfs://jobs/{job_id}/"
        refs = set(store.list_refs(base))
        required = [f"{base}{suffix}" for suffix in _JOB_LAYOUT_REQUIRED_REFS]
        if require_results:
            required.append(f"{base}results.parquet")
        missing = sorted(ref for ref in required if ref not in refs)
        diagnostics = [f"MISSING_REQUIRED:{ref}" for ref in missing]
        return LayoutValidationResult(ok=not missing, diagnostics=diagnostics, missing_required=missing)

    @staticmethod
    def validate_metadata(meta: ArtifactMetadata) -> list[str]:
        violations: list[str] = []
        if not meta.qfs_ref.startswith(f"qfs://jobs/{meta.job_id}/"):
            violations.append("INVALID_REF_SCOPE:qfs_ref must be under job scope")
        if not meta.trace_id.strip():
            violations.append("INVALID_TRACE_ID:trace_id is required")
        if not meta.stage.strip():
            violations.append("INVALID_STAGE:stage is required")
        if not meta.artifact_type.strip():
            violations.append("INVALID_ARTIFACT_TYPE:artifact_type is required")
        if meta.retention_until_epoch_ms < meta.created_at_epoch_ms:
            violations.append("INVALID_RETENTION_WINDOW:retention_until must be >= created_at")
        return sorted(violations)


class QFSMetadataIndex:
    """In-memory metadata index for trace-linked artifact lookup paths."""

    def __init__(self):
        self._items: list[ArtifactMetadata] = []
        self._lock = threading.RLock()

    def upsert(self, meta: ArtifactMetadata) -> None:
        violations = QFSLayoutValidator.validate_metadata(meta)
        if violations:
            raise ValueError(f"INVALID_METADATA:{'|'.join(violations)}")
        with self._lock:
            self._items = [item for item in self._items if item.qfs_ref != meta.qfs_ref]
            self._items.append(meta)
            self._items.sort(key=lambda item: (item.job_id, item.trace_id, item.stage, item.qfs_ref))

    def find_by_trace(self, trace_id: str) -> list[ArtifactMetadata]:
        with self._lock:
            return [item for item in self._items if item.trace_id == trace_id]

    def find_by_job(self, job_id: str) -> list[ArtifactMetadata]:
        with self._lock:
            return [item for item in self._items if item.job_id == job_id]

    def all(self) -> list[ArtifactMetadata]:
        with self._lock:
            return list(self._items)


class QFSRetentionExecutor:
    """Retention cleanup executor with deterministic reason codes."""

    REASON_RETENTION_EXPIRED = "RETENTION_EXPIRED"
    REASON_ORPHAN_NOT_INDEXED = "ORPHAN_NOT_INDEXED"

    @staticmethod
    def run(
        *,
        store: QFSStore,
        index: QFSMetadataIndex,
        now_epoch_ms: int | None = None,
    ) -> list[RetentionCleanupEvent]:
        now_ms = now_epoch_ms if now_epoch_ms is not None else int(datetime.now(tz=UTC).timestamp() * 1000)
        events: list[RetentionCleanupEvent] = []
        indexed_refs = {item.qfs_ref: item for item in index.all()}
        for ref in sorted(store.list_refs("qfs://jobs/")):
            meta = indexed_refs.get(ref)
            if meta is None:
                store.delete_bytes(ref)
                events.append(RetentionCleanupEvent(qfs_ref=ref, reason_code=QFSRetentionExecutor.REASON_ORPHAN_NOT_INDEXED))
                continue
            if now_ms >= meta.retention_until_epoch_ms:
                store.delete_bytes(ref)
                events.append(RetentionCleanupEvent(qfs_ref=ref, reason_code=QFSRetentionExecutor.REASON_RETENTION_EXPIRED))
        return events
