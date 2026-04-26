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


QFS_STORE = InMemoryQFSStore()
