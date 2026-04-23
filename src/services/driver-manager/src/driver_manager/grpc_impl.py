"""gRPC implementation for DriverManagerService."""

from __future__ import annotations

import logging
import re

import grpc

from .errors import FieldViolation, abort_invalid_argument
from .registry import DriverRegistry
from .simulator_driver import DriverExecutionError


class DriverManagerService:
    """Kernel-facing service that delegates to registered drivers."""

    def __init__(self, drv_pb, types_pb, registry: DriverRegistry):
        self._drv_pb = drv_pb
        self._types_pb = types_pb
        self._registry = registry

    def ListDevices(self, request, context: grpc.ServicerContext):
        _log_start("DriverManagerService.ListDevices", "", context)
        return self._drv_pb.ListDevicesResponse(devices=self._registry.list_devices())

    def GetDeviceStatus(self, request, context: grpc.ServicerContext):
        _log_start("DriverManagerService.GetDeviceStatus", request.device_id, context)
        if not request.device_id:
            abort_invalid_argument(
                context,
                message="validation failed",
                violations=[FieldViolation(field="device_id", description="field is required")],
            )

        driver = self._registry.get_driver_for_device(request.device_id)
        if driver is None:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"device not registered: {request.device_id}",
            )

        info = driver.get_device_status(request.device_id)
        resp = self._drv_pb.DeviceStatusResponse(
            device_id=info.device_id,
            status=info.status,
            queue_depth=info.queue_depth,
            estimated_wait_sec=info.estimated_wait_sec,
            metadata=info.metadata,
        )
        _log_end("DriverManagerService.GetDeviceStatus", request.device_id, context)

    def ExecuteCircuit(self, request, context: grpc.ServicerContext):
        _log_start("DriverManagerService.ExecuteCircuit", request.job_id, context)
        violations: list[FieldViolation] = []
        if not request.device_id:
            violations.append(FieldViolation(field="device_id", description="field is required"))
        if request.payload.format == self._types_pb.CIRCUIT_FORMAT_UNSPECIFIED:
            violations.append(FieldViolation(field="payload.format", description="field is required"))
        if not request.payload.data:
            violations.append(FieldViolation(field="payload.data", description="field is required"))
        if request.shots <= 0:
            violations.append(FieldViolation(field="shots", description="must be > 0"))
        if violations:
            abort_invalid_argument(context, message="validation failed", violations=violations)

        driver = self._registry.get_driver_for_device(request.device_id)
        if driver is None:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"device not registered: {request.device_id}",
            )

        if request.payload.format != self._types_pb.CIRCUIT_FORMAT_AQO_JSON:
            context.abort(
                grpc.StatusCode.UNIMPLEMENTED,
                f"unsupported circuit payload format: {request.payload.format}",
            )

        try:
            counts, execution_time_sec, metadata = driver.execute_circuit(
                device_id=request.device_id,
                circuit=request.payload.data,
                shots=request.shots,
                options=dict(request.options),
            )
        except DriverExecutionError as err:
            context.abort(err.code, err.message)

        resp = self._drv_pb.ExecuteCircuitResponse(
            counts=counts,
            execution_time_sec=execution_time_sec,
            metadata=metadata,
        )
        _log_end("DriverManagerService.ExecuteCircuit", request.job_id, context)

        return resp

    def CalibrateDevice(self, request, context: grpc.ServicerContext):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "CalibrateDevice is not implemented in MVP-2")

_LOG = logging.getLogger("driver_manager")
_TRACEPARENT_RE = re.compile(r"^[0-9a-f]{2}-(?P<trace_id>[0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$")


def _trace_fields(context: grpc.ServicerContext) -> tuple[str | None, str | None]:
    md = {k.lower(): v for k, v in (context.invocation_metadata() or [])}
    traceparent = md.get("traceparent")
    trace_id = md.get("trace_id")
    if trace_id is None and traceparent:
        match = _TRACEPARENT_RE.match(traceparent)
        if match:
            trace_id = match.group("trace_id")
    return trace_id, traceparent


def _log_start(method: str, job_id: str, context: grpc.ServicerContext) -> None:
    trace_id, traceparent = _trace_fields(context)
    _LOG.info("rpc_start", extra={"method": method, "job_id": job_id, "trace_id": trace_id, "traceparent": traceparent})


def _log_end(method: str, job_id: str, context: grpc.ServicerContext) -> None:
    trace_id, _traceparent = _trace_fields(context)
    _LOG.info("rpc_end", extra={"method": method, "job_id": job_id, "trace_id": trace_id})
