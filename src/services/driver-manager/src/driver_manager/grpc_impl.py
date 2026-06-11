"""gRPC implementation for DriverManagerService."""

from __future__ import annotations

import logging
import re

import grpc

from .errors import FieldViolation, abort_invalid_argument, abort_normalized, map_backend_error
from .main import record_backend_failure, record_driver_request, record_driver_session
from .registry import DriverRegistry
from .simulator_driver import DriverExecutionError
import time


def _circuit_format_value(types_pb, *names: str) -> int:
    for name in names:
        if hasattr(types_pb, name):
            return int(getattr(types_pb, name))
    raise AttributeError(f"None of the enum names exist: {names}")


def _circuit_format_name(types_pb, value: int) -> str:
    for name, enum_value in vars(types_pb).items():
        if name.startswith("CIRCUIT_FORMAT_") and isinstance(enum_value, int) and int(enum_value) == int(value):
            return name
    return str(value)


def _normalize_counts(counts: dict[str, int]) -> dict[str, int]:
    return {str(bitstring): int(value) for bitstring, value in sorted(counts.items(), key=lambda item: str(item[0]))}


def _normalize_metadata(metadata: dict[str, str]) -> dict[str, str]:
    return {str(key): str(value) for key, value in sorted(metadata.items(), key=lambda item: str(item[0]))}


def _normalize_execution_time_sec(execution_time_sec: float) -> float:
    return round(max(0.0, float(execution_time_sec)), 6)


class DriverManagerService:
    """Kernel-facing service that delegates to registered drivers."""

    def __init__(self, drv_pb, types_pb, registry: DriverRegistry):
        self._drv_pb = drv_pb
        self._types_pb = types_pb
        self._registry = registry

    def ListDevices(self, request, context: grpc.ServicerContext):
        start = time.perf_counter()
        _log_start("DriverManagerService.ListDevices", "", context)
        resp = self._drv_pb.ListDevicesResponse(devices=self._registry.list_devices())
        record_driver_request("ListDevices", "OK", (time.perf_counter() - start) * 1000.0)
        _log_end("DriverManagerService.ListDevices", "", context)
        return resp

    def GetDeviceStatus(self, request, context: grpc.ServicerContext):
        start = time.perf_counter()
        _log_start("DriverManagerService.GetDeviceStatus", request.device_id, context)
        if not request.device_id:
            abort_invalid_argument(
                context,
                message="validation failed",
                violations=[FieldViolation(field="device_id", description="field is required")],
            )

        driver = self._registry.get_driver_for_device(request.device_id)
        if driver is None:
            abort_normalized(
                context,
                normalized=map_backend_error(grpc.StatusCode.INVALID_ARGUMENT, f"device not registered: {request.device_id}"),
                provider="driver_registry",
            )

        info = driver.get_device_status(request.device_id)
        resp = self._drv_pb.DeviceStatusResponse(
            device_id=info.device_id,
            status=info.status,
            queue_depth=info.queue_depth,
            estimated_wait_sec=info.estimated_wait_sec,
            metadata=info.metadata,
        )
        record_driver_request("GetDeviceStatus", "OK", (time.perf_counter() - start) * 1000.0)
        _log_end("DriverManagerService.GetDeviceStatus", request.device_id, context)
        return resp

    def ExecuteCircuit(self, request, context: grpc.ServicerContext):
        start = time.perf_counter()
        _log_start("DriverManagerService.ExecuteCircuit", request.job_id, context)
        violations: list[FieldViolation] = []
        if not request.device_id:
            violations.append(FieldViolation(field="device_id", description="field is required"))
        if request.payload.format == _circuit_format_value(self._types_pb, "CIRCUIT_FORMAT_UNSPECIFIED"):
            violations.append(FieldViolation(field="payload.format", description="field is required"))
        if not request.payload.data:
            violations.append(FieldViolation(field="payload.data", description="field is required"))
        if request.shots <= 0:
            violations.append(FieldViolation(field="shots", description="must be > 0"))
        if violations:
            abort_invalid_argument(context, message="validation failed", violations=violations)

        driver = self._registry.get_driver_for_device(request.device_id)
        if driver is None:
            abort_normalized(
                context,
                normalized=map_backend_error(grpc.StatusCode.INVALID_ARGUMENT, f"device not registered: {request.device_id}"),
                provider="driver_registry",
            )

        aqo_json_format = _circuit_format_value(self._types_pb, "CIRCUIT_FORMAT_AQO_JSON", "AQO_JSON")
        if request.payload.format != aqo_json_format:
            abort_normalized(
                context,
                normalized=map_backend_error(
                    grpc.StatusCode.UNIMPLEMENTED,
                    f"unsupported circuit payload format: {_circuit_format_name(self._types_pb, request.payload.format)}",
                ),
                job_id=request.job_id,
                provider="driver_manager",
            )

        try:
            counts, execution_time_sec, metadata = driver.execute_circuit(
                device_id=request.device_id,
                circuit=request.payload.data,
                shots=request.shots,
                options=dict(request.options),
            )
        except DriverExecutionError as err:
            record_backend_failure("driver_manager", err.code.name.lower())
            abort_normalized(
                context,
                normalized=map_backend_error(err.code, err.message),
                job_id=request.job_id,
                provider=getattr(driver, "name", "unknown"),
            )

        resp = self._drv_pb.ExecuteCircuitResponse(
            counts=_normalize_counts(counts),
            execution_time_sec=_normalize_execution_time_sec(execution_time_sec),
            metadata=_normalize_metadata(metadata),
        )
        record_driver_session(getattr(driver, "name", "unknown"), "active")
        record_driver_request("ExecuteCircuit", "OK", (time.perf_counter() - start) * 1000.0)
        _log_end("DriverManagerService.ExecuteCircuit", request.job_id, context)

        return resp

    def CalibrateDevice(self, request, context: grpc.ServicerContext):
        start = time.perf_counter()
        driver = self._registry.get_driver_for_device(request.device_id)

        if driver is None:
            abort_normalized(
                context,
                normalized=map_backend_error(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"device not registered: {request.device_id}",
                ),
                provider="driver_registry",
            )

        artifact = driver.calibrate_device(
            request.device_id,
            dict(request.options),
        )

        return self._drv_pb.CalibrateDeviceResponse(
            calibration_artifact_ref=artifact,
        )

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
