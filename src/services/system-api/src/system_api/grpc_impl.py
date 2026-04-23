"""gRPC service implementations for System API (skeleton).

This is an MVP **skeleton server** for GitHub issue #24.
It provides stub implementations for:
- eigen.api.v1.JobService
- eigen.api.v1.DeviceService

The goal is to compile, run, and validate requests consistently.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
import json

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from .errors import abort_invalid_argument
from .observability import log_request_end, log_request_start, new_request_context
from .validation import (
    validate_device_id,
    validate_job_id,
    validate_reserve_device,
    validate_submit_job,
)

TERMINAL_JOB_STATES = {
    "JOB_STATE_DONE",
    "JOB_STATE_ERROR",
    "JOB_STATE_CANCELLED",
    "JOB_STATE_TIMEOUT",
}


def _ts_now() -> Timestamp:
    ts = Timestamp()
    ts.FromDatetime(datetime.now(timezone.utc))
    return ts


@dataclass
class _JobRecord:
    job_id: str
    created_at: Timestamp
    updates: list
    counts: dict[str, int]
    results_metadata: dict[str, str]
    terminal_state: int


class JobService:
    """Implementation of eigen.api.v1.JobService (stub)."""

    def __init__(self, job_pb, types_pb):
        self._job_pb = job_pb
        self._types_pb = types_pb
        self._jobs: dict[str, _JobRecord] = {}
        self._lock = threading.RLock()

    def _mk_update(self, *, job_id: str, state: int, stage: str, progress: float, message: str, event_seq: int):
        return self._types_pb.JobUpdate(
            job_id=job_id,
            state=state,
            stage=stage,
            progress=progress,
            message=message,
            event_seq=event_seq,
            timestamp=_ts_now(),
        )

    def _mk_default_updates(self, job_id: str) -> list:
        return [
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_QUEUED,
                stage="QUEUED",
                progress=0.0,
                message="queued (stub)",
                event_seq=1,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="RUNNING",
                progress=0.5,
                message="running (stub)",
                event_seq=2,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_DONE,
                stage="DONE",
                progress=1.0,
                message="done (stub)",
                event_seq=3,
            ),
        ]
    
    def _mk_vqe_updates(
        self,
        *,
        job_id: str,
        max_iters: int,
        trace_id: str,
    ) -> tuple[list, list[float]]:
        objective_history: list[float] = []
        updates = [
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_QUEUED,
                stage="QUEUED",
                progress=0.0,
                message=f"queued vqe job trace_id={trace_id}",
                event_seq=1,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="RUNNING",
                progress=0.1,
                message=f"starting hybrid loop trace_id={trace_id} iteration=0",
                event_seq=2,
            ),
        ]

        current = -0.22
        for iter_idx in range(1, max_iters + 1):
            # Deterministic synthetic convergence curve for CI stability.
            current = round(current - (0.08 / (iter_idx + 1)), 6)
            objective_history.append(current)
            progress = min(0.1 + (0.8 * iter_idx / max_iters), 0.95)
            updates.append(
                self._mk_update(
                    job_id=job_id,
                    state=self._types_pb.JOB_STATE_RUNNING,
                    stage="RUNNING",
                    progress=progress,
                    message=(
                        "vqe_iteration "
                        f"trace_id={trace_id} iteration={iter_idx} objective={current}"
                    ),
                    event_seq=2 + iter_idx,
                )
            )

        best = min(objective_history) if objective_history else current
        updates.append(
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_DONE,
                stage="DONE",
                progress=1.0,
                message=f"vqe complete trace_id={trace_id} best_objective={best}",
                event_seq=3 + max_iters,
            )
        )
        return updates, objective_history

    def _build_job_record(self, request, *, job_id: str, created_at: Timestamp) -> _JobRecord:
        source_text = ""
        if request.WhichOneof("program") == "eigen_lang":
            source_text = request.eigen_lang.source.decode("utf-8", errors="ignore").lower()

        is_vqe = "vqe" in request.name.lower() or "vqe" in source_text
        if not is_vqe:
            updates = self._mk_default_updates(job_id)
            return _JobRecord(
                job_id=job_id,
                created_at=created_at,
                updates=updates,
                counts={"00": 512, "11": 512},
                results_metadata={"stub": "true"},
                terminal_state=self._types_pb.JOB_STATE_DONE,
            )

        max_iters = int(request.metadata.get("max_iters", "6"))
        max_iters = max(2, min(max_iters, 12))
        trace_id = request.metadata.get("trace_id", "trace-vqe-ci")
        updates, objective_history = self._mk_vqe_updates(job_id=job_id, max_iters=max_iters, trace_id=trace_id)

        qfs_base = f"/circuit_fs/{job_id}"
        metadata = {
            "workload": "vqe",
            "objective_history": json.dumps(objective_history),
            "best_objective": str(min(objective_history)),
            "qfs_compiled_aqo": f"{qfs_base}/compiled/circuit.aqo.json",
            "qfs_results_counts": f"{qfs_base}/results/counts.json",
            "qfs_results_metadata": f"{qfs_base}/results/metadata.json",
            "qfs_metrics": f"{qfs_base}/results/metrics.json",
        }
        return _JobRecord(
            job_id=job_id,
            created_at=created_at,
            updates=updates,
            counts={"00": 590, "11": 434},
            results_metadata=metadata,
            terminal_state=self._types_pb.JOB_STATE_DONE,
        )

    def SubmitJob(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        log_request_start("JobService.SubmitJob", rc)

        violations = validate_submit_job(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        rc.job_id = job_id
        now = _ts_now()

        with self._lock:
            record = self._build_job_record(request, job_id=job_id, created_at=now)
            self._jobs[job_id] = record

        resp = self._job_pb.SubmitJobResponse(
            job_id=job_id,
            status=self._types_pb.JobStatus(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_QUEUED,
                stage="QUEUED",
                progress=0.0,
                message="accepted (stub)",
                created_at=now,
                updated_at=now,
            ),
        )

        log_request_end("JobService.SubmitJob", rc)
        return resp

    def GetJobStatus(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.GetJobStatus", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        with self._lock:
            record = self._jobs.get(request.job_id)

        if record is None:
            latest = self._types_pb.JobUpdate(
                job_id=request.job_id,
                state=self._types_pb.JOB_STATE_QUEUED,
                stage="QUEUED",
                progress=0.0,
                message="stub status",
                event_seq=0,
                timestamp=_ts_now(),
            )
            created_at = _ts_now()
        else:
            latest = record.updates[-1]
            created_at = record.created_at

        resp = self._job_pb.GetJobStatusResponse(
            status=self._types_pb.JobStatus(
                job_id=request.job_id,
                state=latest.state,
                stage=latest.stage,
                progress=latest.progress,
                message=latest.message,
                created_at=created_at,
                updated_at=latest.timestamp,
            )
        )

        log_request_end("JobService.GetJobStatus", rc)
        return resp

    def CancelJob(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.CancelJob", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        accepted = False
        with self._lock:
            record = self._jobs.get(request.job_id)
            if record is not None:
                terminal_values = {getattr(self._types_pb, name) for name in TERMINAL_JOB_STATES}
                if record.updates[-1].state not in terminal_values:
                    seq = int(record.updates[-1].event_seq) + 1
                    record.updates.append(
                        self._mk_update(
                            job_id=request.job_id,
                            state=self._types_pb.JOB_STATE_CANCELLED,
                            stage="CANCELLED",
                            progress=1.0,
                            message="cancelled (stub)",
                            event_seq=seq,
                        )
                    )
                    accepted = True

        resp = self._job_pb.CancelJobResponse(accepted=accepted)
        log_request_end("JobService.CancelJob", rc)
        return resp

    def StreamJobUpdates(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.StreamJobUpdates", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        start_after_seq = int(request.last_event_seq)
        with self._lock:
            record = self._jobs.get(request.job_id)
            if record is None:
                updates = self._mk_default_updates(request.job_id)
                self._jobs[request.job_id] = _JobRecord(
                    job_id=request.job_id,
                    created_at=_ts_now(),
                    updates=updates,
                    counts={"00": 512, "11": 512},
                    results_metadata={"stub": "true"},
                    terminal_state=self._types_pb.JOB_STATE_DONE,
                )
                selected_updates = updates
            else:
                selected_updates = list(record.updates)

        for update in selected_updates:
            if int(update.event_seq) <= start_after_seq:
                continue
            yield self._job_pb.StreamJobUpdatesResponse(update=update)

        log_request_end("JobService.StreamJobUpdates", rc)

    def GetJobResults(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.GetJobResults", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        with self._lock:
            record = self._jobs.get(request.job_id)

        if record is None:
            resp = self._job_pb.GetJobResultsResponse(
                job_id=request.job_id,
                state=self._types_pb.JOB_STATE_DONE,
                counts={"00": 512, "11": 512},
                metadata={"stub": "true"},
                completed_at=_ts_now(),
            )
        else:
            resp = self._job_pb.GetJobResultsResponse(
                job_id=request.job_id,
                state=record.terminal_state,
                counts=record.counts,
                metadata=record.results_metadata,
                completed_at=_ts_now(),
            )

        log_request_end("JobService.GetJobResults", rc)
        return resp


class DeviceService:
    """Implementation of eigen.api.v1.DeviceService (stub)."""

    def __init__(self, dev_pb, types_pb):
        self._dev_pb = dev_pb
        self._types_pb = types_pb

    def ListDevices(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        log_request_start("DeviceService.ListDevices", rc)

        # backend_type is optional
        resp = self._dev_pb.ListDevicesResponse(
            devices=[
                self._types_pb.DeviceInfo(
                    device_id="sim:local",
                    name="Local simulator",
                    backend_type="simulator",
                    status=self._types_pb.DEVICE_STATUS_ONLINE,
                    queue_depth=0,
                    estimated_wait_sec=0,
                    capabilities={"shots": "1024"},
                )
            ]
        )

        log_request_end("DeviceService.ListDevices", rc)
        return resp

    def GetDeviceDetails(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        log_request_start("DeviceService.GetDeviceDetails", rc)

        violations = validate_device_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        resp = self._dev_pb.GetDeviceDetailsResponse(
            device=self._types_pb.DeviceInfo(
                device_id=request.device_id,
                name="Device (stub)",
                backend_type="simulator",
                status=self._types_pb.ONLINE,
            )
        )

        log_request_end("DeviceService.GetDeviceDetails", rc)
        return resp

    def GetDeviceStatus(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        log_request_start("DeviceService.GetDeviceStatus", rc)

        violations = validate_device_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        resp = self._dev_pb.GetDeviceStatusResponse(
            device_id=request.device_id,
            status=self._types_pb.DEVICE_STATUS_ONLINE,
            queue_depth=0,
            estimated_wait_sec=0,
            metadata={"stub": "true"},
        )

        log_request_end("DeviceService.GetDeviceStatus", rc)
        return resp

    def ReserveDevice(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        log_request_start("DeviceService.ReserveDevice", rc)

        violations = validate_reserve_device(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        resp = self._dev_pb.ReserveDeviceResponse(
            reservation_id=f"rsv_{uuid.uuid4().hex[:12]}",
            expires_at=_ts_now(),
        )

        log_request_end("DeviceService.ReserveDevice", rc)
        return resp
