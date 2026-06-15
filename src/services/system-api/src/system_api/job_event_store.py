import json
import os
import uuid
import threading
from pathlib import Path
from .job_events import JobEvent


class JobEventStore:
     """
     APPEND-ONLY LOG = SINGLE SOURCE OF TRUTH
     """

     def __init__(self, root="/tmp/eigen/job-events"):
         self.root = Path(root)
         self.root.mkdir(parents=True, exist_ok=True)
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
     