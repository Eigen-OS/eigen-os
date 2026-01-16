"""gRPC service implementations for System API (skeleton).

This is an MVP **skeleton server** for GitHub issue #24.
It provides stub implementations for:
- eigen.api.v1.JobService
- eigen.api.v1.DeviceService

The goal is to compile, run, and validate requests consistently.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

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


def _ts_now() -> Timestamp:
    ts = Timestamp()
    ts.FromDatetime(datetime.now(timezone.utc))
    return ts


class JobService:
    """Implementation of eigen.api.v1.JobService (stub)."""

    def __init__(self, job_pb, types_pb):
        self._job_pb = job_pb
        self._types_pb = types_pb

    def SubmitJob(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        log_request_start("JobService.SubmitJob", rc)

        violations = validate_submit_job(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = _ts_now()

        resp = self._job_pb.JobResponse(
            job_id=job_id,
            status=self._types_pb.JobStatus(
                job_id=job_id,
                state=self._types_pb.QUEUED,
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
        log_request_start("JobService.GetJobStatus", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        now = _ts_now()
        resp = self._job_pb.JobStatusResponse(
            status=self._types_pb.JobStatus(
                job_id=request.job_id,
                state=self._types_pb.QUEUED,
                stage="QUEUED",
                progress=0.0,
                message="stub status",
                created_at=now,
                updated_at=now,
            )
        )

        log_request_end("JobService.GetJobStatus", rc)
        return resp

    def CancelJob(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        log_request_start("JobService.CancelJob", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        resp = self._job_pb.CancelJobResponse(accepted=True)
        log_request_end("JobService.CancelJob", rc)
        return resp

    def StreamJobUpdates(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        log_request_start("JobService.StreamJobUpdates", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        # MVP skeleton: emit a small ordered sequence, no persistence.
        seq = max(1, int(request.last_event_seq) + 1)
        yield self._types_pb.JobUpdate(
            job_id=request.job_id,
            state=self._types_pb.QUEUED,
            stage="QUEUED",
            progress=0.0,
            message="queued (stub)",
            event_seq=seq,
            timestamp=_ts_now(),
        )

        # Small delay so clients can observe streaming locally.
        time.sleep(0.05)

        yield self._types_pb.JobUpdate(
            job_id=request.job_id,
            state=self._types_pb.DONE,
            stage="DONE",
            progress=1.0,
            message="done (stub)",
            event_seq=seq + 1,
            timestamp=_ts_now(),
        )

        log_request_end("JobService.StreamJobUpdates", rc)

    def GetJobResults(self, request, context: grpc.ServicerContext):
        rc = new_request_context(context)
        log_request_start("JobService.GetJobResults", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        resp = self._job_pb.JobResultsResponse(
            job_id=request.job_id,
            state=self._types_pb.DONE,
            counts={"00": 512, "11": 512},
            metadata={"stub": "true"},
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
                    status=self._types_pb.ONLINE,
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

        resp = self._dev_pb.DeviceDetailsResponse(
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

        resp = self._dev_pb.DeviceStatusResponse(
            device_id=request.device_id,
            status=self._types_pb.ONLINE,
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
