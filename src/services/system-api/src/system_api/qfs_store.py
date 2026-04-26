"""In-memory QFS emulation used by runtime E2E tests."""

from __future__ import annotations

import threading


class InMemoryQFSStore:
    """Thread-safe byte-addressable storage for qfs:// refs."""

    def __init__(self):
        self._data: dict[str, bytes] = {}
        self._lock = threading.RLock()

    def put_bytes(self, qfs_ref: str, payload: bytes) -> None:
        with self._lock:
            self._data[qfs_ref] = payload

    def get_bytes(self, qfs_ref: str) -> bytes | None:
        with self._lock:
            value = self._data.get(qfs_ref)
            if value is None:
                return None
            return bytes(value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def delete_bytes(self, qfs_ref: str) -> None:
        with self._lock:
            self._data.pop(qfs_ref, None)

    def delete_prefix(self, prefix: str) -> None:
        with self._lock:
            keys = [key for key in self._data if key.startswith(prefix)]
            for key in keys:
                del self._data[key]


QFS_STORE = InMemoryQFSStore()
