"""gRPC implementation for DriverManagerService."""

from __future__ import annotations

import json
import logging
import os
import re
import time

import grpc

from .driver_selection import DriverSelectionError, resolve_execution_target
from .errors import FieldViolation, abort_invalid_argument, abort_normalized, map_backend_error
from .registry import DriverRegistry
from .simulator_driver import DriverExecutionError


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
        self._selection_mode = os.getenv("DRIVER_MANAGER_DRIVER_SELECTION", "explicit").strip().lower()
        if self._selection_mode not in {"explicit", "auto"}:
            raise ValueError("DRIVER_MANAGER_DRIVER_SELECTION must be explicit or auto")

    def ListDevices(self, request, context: grpc.ServicerContext):
        start = time.perf_counter()
        _log_start("DriverManagerService.ListDevices", "", context)
        resp = self._drv_pb.ListDevicesResponse(devices=self._registry.list_devices())
        from . import main as driver_manager_main

        driver_manager_main.record_driver_request("ListDevices", "OK", (time.perf_counter() - start) * 1000.0)
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
        from . import main as driver_manager_main

        driver_manager_main.record_driver_request("GetDeviceStatus", "OK", (time.perf_counter() - start) * 1000.0)
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

        options = dict(request.options)
        option_noise_model = options.get("noise_model", "")
        if request.noise_model and option_noise_model and request.noise_model != option_noise_model:
            abort_invalid_argument(
                context,
                message="validation failed",
                violations=[
                    FieldViolation(
                        field="noise_model",
                        description="must match options.noise_model when both are supplied",
                    )
                ],
            )
        # `options.noise_model` is retained for older callers.  Treat it as
        # the same execution-affecting input as the typed field so that it
        # cannot bypass capability negotiation or be silently overwritten.
        effective_noise_model = request.noise_model or option_noise_model
        if effective_noise_model:
            options["noise_model"] = effective_noise_model
        for name, value in request.parameter_bindings.items():
            options[f"param.{name}"] = str(value)
        if request.observable_measurement_plan.terms:
            options["observable_measurement_plan"] = json.dumps(
                {
                    "measurement_basis": request.observable_measurement_plan.measurement_basis,
                    "terms": [
                        {
                            "term_id": term.term_id,
                            "operator": term.operator,
                            "qubits": list(term.qubits),
                            "coefficient": term.coefficient,
                        }
                        for term in request.observable_measurement_plan.terms
                    ],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        try:
            target = resolve_execution_target(
                self._registry,
                device_id=request.device_id,
                driver_name=options.get("driver", ""),
                selection=options.get("driver_selection", self._selection_mode),
            )
        except DriverSelectionError as err:
            abort_normalized(
                context,
                normalized=map_backend_error(grpc.StatusCode.INVALID_ARGUMENT, str(err)),
                job_id=request.job_id,
                provider="driver_selection",
            )
        driver = target.driver
        device = next((item for item in driver.get_devices() if item.device_id == target.device_id), None)
        capabilities = dict(device.capabilities) if device is not None else {}
        required_capabilities = []
        if request.parameter_bindings:
            required_capabilities.append(("parameter_binding", "parameter binding"))
        if request.observable_measurement_plan.terms:
            required_capabilities.extend((("measurement_basis", "observable measurement basis"), ("observable_expectation", "observable expectation")))
        if effective_noise_model and effective_noise_model != "ideal":
            model = effective_noise_model.partition(":")[0]
            supported = {value.strip() for value in capabilities.get("noise_models", "").split(",") if value.strip()}
            if model not in supported:
                required_capabilities.append(("noise_models", f"noise model {model}"))
        missing = [label for key, label in required_capabilities if capabilities.get(key, "").lower() not in {"true", "pauli"} and key != "noise_models"]
        if missing or any(key == "noise_models" for key, _label in required_capabilities):
            labels = missing or [label for key, label in required_capabilities if key == "noise_models"]
            abort_normalized(
                context,
                normalized=map_backend_error(grpc.StatusCode.FAILED_PRECONDITION, f"backend {target.device_id} does not support: {', '.join(labels)}"),
                job_id=request.job_id,
                provider=target.driver_name,
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
                device_id=target.device_id,
                circuit=request.payload.data,
                shots=request.shots,
                options=options,
            )
        except DriverExecutionError as err:
            from . import main as driver_manager_main

            driver_manager_main.record_backend_failure(target.driver_name, err.code.name.lower())
            abort_normalized(
                context,
                normalized=map_backend_error(err.code, err.message),
                job_id=request.job_id,
                provider=target.driver_name,
            )


        normalized_metadata = _normalize_metadata(metadata)
        try:
            expectations = json.loads(normalized_metadata.get("expectations", "{}"))
        except json.JSONDecodeError:
            expectations = {}
        resp = self._drv_pb.ExecuteCircuitResponse(
            counts=_normalize_counts(counts),
            execution_time_sec=_normalize_execution_time_sec(execution_time_sec),
            metadata=normalized_metadata,
            expectations={str(key): float(value) for key, value in expectations.items()},
        )
        from . import main as driver_manager_main

        driver_manager_main.record_driver_session(target.driver_name, "active")
        driver_manager_main.record_driver_request("ExecuteCircuit", "OK", (time.perf_counter() - start) * 1000.0)
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
