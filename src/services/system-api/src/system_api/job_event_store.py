import json
import os
import tempfile
import uuid
import threading
import time
from pathlib import Path
from .job_events import JobEvent


class JobEventStore:
     """
     APPEND-ONLY LOG = SINGLE SOURCE OF TRUTH
     """

     @staticmethod
     def _candidate_roots(root: str | None) -> list[Path]:
         candidates: list[Path] = []
         if root:
             candidates.append(Path(root))
         env_root = os.getenv("SYSTEM_API_JOB_EVENT_STORE_PATH")
         if env_root:
             candidates.append(Path(env_root))
         candidates.extend([
             Path("/tmp/eigen/job-events"),
             Path.cwd() / ".eigen" / "job-events",
             Path(tempfile.gettempdir()) / f"eigen-job-events-{os.getpid()}",
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
         raise RuntimeError("unable to initialize writable JobEventStore root") from last_exc

     def __init__(self, root="/tmp/eigen/job-events"):
         self.root = self._select_root(self._candidate_roots(root))
         self.lock = threading.RLock()

     def append(self, event: JobEvent):
         with self.lock:
             path = self.root / f"{event.job_id}.log"
             with open(path, "a") as f:
                 f.write(json.dumps(event.__dict__) + "\n")

     def read(self, job_id: str):
         path = self.root / f"{job_id}.log"
         if not path.exists():
             return []

         return [
             json.loads(line)
             for line in path.read_text().splitlines()
             if line.strip()
         ]
     