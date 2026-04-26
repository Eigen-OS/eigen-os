"""QFS storage facade with pluggable local and S3-compatible blob backends."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
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
    """Thread-safe local (in-memory) backend for qfs:// refs."""

    def __init__(self):
        self._data: dict[str, bytes] = {}
        self._lock = threading.RLock()

    def upload_bytes(self, ref: str, payload: bytes) -> None:
        with self._lock:
            self._data[ref] = payload

    def download_bytes(self, ref: str) -> bytes | None:
        with self._lock:
            value = self._data.get(ref)
            return None if value is None else bytes(value)

    def list_refs(self, prefix: str) -> list[str]:
        with self._lock:
            return sorted(key for key in self._data if key.startswith(prefix))

    def delete_ref(self, ref: str) -> None:
        with self._lock:
            self._data.pop(ref, None)

    def delete_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in [key for key in self._data if key.startswith(prefix)]:
                del self._data[key]
    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def atomic_write(self, ref: str, payload: bytes) -> None:
        with self._lock:
            tmp = f"{ref}.tmp-{threading.get_ident()}-{time.monotonic_ns()}"
            self._data[tmp] = payload
            self._data[ref] = self._data[tmp]
            del self._data[tmp]


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


QFS_STORE = _build_qfs_store_from_env()
