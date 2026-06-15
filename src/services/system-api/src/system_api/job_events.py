from dataclasses import dataclass
from typing import Literal, Optional
import time


EventType = Literal[
     "JOB_CREATED",
     "JOB_STATE_CHANGED",
     "JOB_REPLAYED",
     "JOB_STREAMED",
 ]


@dataclass
class JobEvent:
     event_id: str
     job_id: str
     tenant_id: str
     event_type: EventType
     timestamp_ms: int
     payload: dict
     