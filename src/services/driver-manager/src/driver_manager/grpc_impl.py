"""gRPC implementation for DriverManagerService."""

from __future__ import annotations

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
        return self._drv_pb.ListDevicesResponse(devices=self._registry.list_devices())

    def GetDeviceStatus(self, request, context: grpc.ServicerContext):
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
        return self._drv_pb.DeviceStatusResponse(
            device_id=info.device_id,
            status=info.status,
            queue_depth=info.queue_depth,
            estimated_wait_sec=info.estimated_wait_sec,
            metadata=info.metadata,
        )

    def ExecuteCircuit(self, request, context: grpc.ServicerContext):
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

        return self._drv_pb.ExecuteCircuitResponse(
            counts=counts,
            execution_time_sec=execution_time_sec,
            metadata=metadata,
        )

    def CalibrateDevice(self, request, context: grpc.ServicerContext):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "CalibrateDevice is not implemented in MVP-2")
