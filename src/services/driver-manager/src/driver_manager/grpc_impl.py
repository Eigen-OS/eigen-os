"""gRPC implementation for DriverManagerService (MVP skeleton)."""

from __future__ import annotations

import grpc

from .errors import FieldViolation, abort_invalid_argument
from .registry import DriverRegistry


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
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "ExecuteCircuit is not implemented in MVP-2")

    def CalibrateDevice(self, request, context: grpc.ServicerContext):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "CalibrateDevice is not implemented in MVP-2")
