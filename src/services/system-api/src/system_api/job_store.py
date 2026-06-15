from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict
from hashlib import sha256


@dataclass
class JobRecord:
     job_id: str
     tenant_id: str
     name: str
     state: str
     created_at_unix_ms: int
     updated_at_unix_ms: int
     idempotency_key: Optional[str] = None


class JobStore:
     """
     SINGLE SOURCE OF TRUTH (System API layer).
     Replaces any in-memory or kernel-side tracking for API visibility.
     """

     @staticmethod
     def _candidate_roots(root: str | None) -> list[Path]:
         candidates: list[Path] = []
         if root:
             candidates.append(Path(root))
         env_root = os.getenv("SYSTEM_API_JOB_STORE_PATH")
         if env_root:
             candidates.append(Path(env_root))
         # Backward-compatible default first, then safer fallbacks that do not
         # depend on /tmp/eigen being writable.
         candidates.extend([
             Path("/tmp/eigen/system_api_jobs"),
             Path.cwd() / ".eigen" / "system_api_jobs",
             Path(tempfile.gettempdir()) / f"eigen-system-api-jobs-{os.getpid()}",
         ])
         return candidates

     @staticmethod
     def _select_root(candidates: list[Path]) -> Path:
         last_exc: Exception | None = None
         for candidate in candidates:
             try:
                 candidate.mkdir(parents=True, exist_ok=True)
                 probe = candidate / f".probe-{os.getpid()}-{threading.get_ident()}-{time.monotonic_ns()}"
                 probe.write_text("ok", encoding="utf-8")
                 probe.unlink(missing_ok=True)
                 return candidate
             except Exception as exc:  # pragma: no cover - environment dependent
                 last_exc = exc
         raise RuntimeError("unable to initialize writable JobStore root") from last_exc    
     def __init__(self, root: str = "/tmp/eigen/system_api_jobs"):
         self._root = self._select_root(self._candidate_roots(root))
         self._lock = threading.RLock()
         self._idempotency_index: Dict[str, str] = {}

     # ---------- idempotency ----------

     def resolve_idempotency(self, key: str) -> Optional[str]:
         return self._idempotency_index.get(key)

     def bind_idempotency(self, key: str, job_id: str) -> None:
         self._idempotency_index[key] = job_id

     # ---------- persistence ----------

     def _path(self, job_id: str) -> Path:
         return self._root / f"{job_id}.json"

     def create(self, job: JobRecord) -> JobRecord:
         with self._lock:
             self._write(job)
             if job.idempotency_key:
                 self.bind_idempotency(job.idempotency_key, job.job_id)
             return job

     def get(self, job_id: str) -> Optional[JobRecord]:
         path = self._path(job_id)
         if not path.exists():
             return None
         return JobRecord(**json.loads(path.read_text()))

     def _write(self, job: JobRecord) -> None:
         tmp = self._path(job.job_id).with_suffix(".tmp")
         tmp.write_text(json.dumps(asdict(job)))
         os.replace(tmp, self._path(job.job_id))  # atomic commit
