"""gRPC service implementations for System API (MVP skeleton)."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from .errors import abort_invalid_argument
from .observability import log_request_end, log_request_start, new_request_context
from .security import enforce_authn, enforce_authz
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
    """Implementation of eigen.api.v1.JobService."""

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
                state=self._types_pb.JOB_STATE_PENDING,
                stage="PENDING",
                progress=0.0,
                message="pending",
                event_seq=1,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_COMPILING,
                stage="COMPILING",
                progress=0.25,
                message="compiling",
                event_seq=2,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="RUNNING",
                progress=0.7,
                message="running",
                event_seq=3,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_DONE,
                stage="DONE",
                progress=1.0,
                message="done",
                event_seq=4,
            ),
        ]
    
    def _mk_vqe_updates(self, *, job_id: str, trace_id: str | None, max_iters: int) -> list:
        updates = [
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_PENDING,
                stage="PENDING",
                progress=0.0,
                message="pending",
                event_seq=1,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_COMPILING,
                stage="COMPILING",
                progress=0.2,
                message="compiling",
                event_seq=2,
            ),
        ]

        trace_suffix = f" trace_id={trace_id}" if trace_id else ""
        simulated_iters = max(2, min(max_iters, 3))
        for idx in range(1, simulated_iters + 1):
            progress = min(0.25 + (0.55 * idx / simulated_iters), 0.9)
            updates.append(
                self._mk_update(
                    job_id=job_id,
                    state=self._types_pb.JOB_STATE_RUNNING,
                    stage="RUNNING",
                    progress=progress,
                    message=f"vqe_iteration iteration={idx}{trace_suffix}",
                    event_seq=len(updates) + 1,
                )
            )

        updates.append(
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_DONE,
                stage="DONE",
                progress=1.0,
                message="done",
                event_seq=len(updates) + 1,
            )
        )
        return updates

    
    def _build_job_record(self, request, *, job_id: str, created_at: Timestamp) -> _JobRecord:
        metadata = dict(request.metadata)
        trace_id = metadata.get("trace_id")
        max_iters = int(metadata.get("max_iters", "0") or 0)

        if max_iters > 0:
            updates = self._mk_vqe_updates(job_id=job_id, trace_id=trace_id, max_iters=max_iters)
            objective_history = [round(1.0 - (0.08 * i), 6) for i in range(max_iters)]
        else:
            updates = self._mk_default_updates(job_id)
            objective_history = []

        results_metadata = {
            "backend": request.target or "sim:local",
            "qfs_compiled_aqo": f"qfs://jobs/{job_id}/compiled/circuit.aqo.json",
            "qfs_results_counts": f"qfs://jobs/{job_id}/results/counts.json",
            "qfs_metrics": f"qfs://jobs/{job_id}/results/metrics.json",
        }
        if objective_history:
            results_metadata["objective_history"] = json.dumps(objective_history)

        return _JobRecord(
            job_id=job_id,
            created_at=created_at,
            updates=updates,
            counts={"00": 512, "11": 512},
            results_metadata=results_metadata,
            terminal_state=self._types_pb.JOB_STATE_DONE,
        )

    def SubmitJob(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.SubmitJob")
        enforce_authz(context, required_permission="jobs:submit")
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
                state=self._types_pb.JOB_STATE_PENDING,
                stage="PENDING",
                progress=0.0,
                message="accepted",
                created_at=now,
                updated_at=now,
            ),
        )

        log_request_end("JobService.SubmitJob", rc)
        return resp

    def GetJobStatus(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetJobStatus")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.GetJobStatus", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        with self._lock:
            record = self._jobs.get(request.job_id)

        if record is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f"job_id not found: {request.job_id}")
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
        enforce_authn(context, method_name="JobService.CancelJob")
        enforce_authz(context, required_permission="jobs:cancel")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.CancelJob", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        accepted = False
        with self._lock:
            record = self._jobs.get(request.job_id)
            if record is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f"job_id not found: {request.job_id}")
            terminal_values = {getattr(self._types_pb, name) for name in TERMINAL_JOB_STATES}
            if record.updates[-1].state not in terminal_values:
                seq = int(record.updates[-1].event_seq) + 1
                record.updates.append(
                    self._mk_update(
                        job_id=request.job_id,
                        state=self._types_pb.JOB_STATE_CANCELLED,
                        stage="CANCELLED",
                        progress=1.0,
                        message="cancelled",
                        event_seq=seq,
                    )
                )
                accepted = True

        resp = self._job_pb.CancelJobResponse(accepted=accepted)
        log_request_end("JobService.CancelJob", rc)
        return resp

    def StreamJobUpdates(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.StreamJobUpdates")
        enforce_authz(context, required_permission="jobs:read")
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
                context.abort(grpc.StatusCode.NOT_FOUND, f"job_id not found: {request.job_id}")
            selected_updates = list(record.updates)

        for update in selected_updates:
            if int(update.event_seq) <= start_after_seq:
                continue
            yield self._job_pb.StreamJobUpdatesResponse(update=update)

        log_request_end("JobService.StreamJobUpdates", rc)

    def GetJobResults(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetJobResults")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.GetJobResults", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        with self._lock:
            record = self._jobs.get(request.job_id)

        if record is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f"job_id not found: {request.job_id}")
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
    """Implementation of eigen.api.v1.DeviceService."""

    def __init__(self, dev_pb, types_pb):
        self._dev_pb = dev_pb
        self._types_pb = types_pb

    def ListDevices(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="DeviceService.ListDevices")
        enforce_authz(context, required_permission="devices:list")
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
        enforce_authn(context, method_name="DeviceService.GetDeviceDetails")
        enforce_authz(context, required_permission="devices:list")
        rc = new_request_context(context)
        log_request_start("DeviceService.GetDeviceDetails", rc)

        violations = validate_device_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        resp = self._dev_pb.GetDeviceDetailsResponse(
            device=self._types_pb.DeviceInfo(
                device_id=request.device_id,
                name="Device",
                backend_type="simulator",
                status=self._types_pb.DEVICE_STATUS_ONLINE,
            )
        )

        log_request_end("DeviceService.GetDeviceDetails", rc)
        return resp

    def GetDeviceStatus(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="DeviceService.GetDeviceStatus")
        enforce_authz(context, required_permission="devices:list")
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
            metadata={},
        )

        log_request_end("DeviceService.GetDeviceStatus", rc)
        return resp

    def ReserveDevice(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="DeviceService.ReserveDevice")
        enforce_authz(context, required_permission="devices:reserve")
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
