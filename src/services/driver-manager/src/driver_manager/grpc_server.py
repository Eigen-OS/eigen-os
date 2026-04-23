"""driver-manager gRPC server bootstrap."""

from __future__ import annotations

import logging
import os
from concurrent import futures

import grpc

from .grpc_impl import DriverManagerService
from .proto_gen import ensure_generated
from .registry import DriverRegistry
from .simulator_driver import SimulatorDriver

_LOG = logging.getLogger("driver_manager")


def _default_registry(types_pb) -> DriverRegistry:
    registry = DriverRegistry()
    simulator = SimulatorDriver(types_pb=types_pb)
    simulator.initialize(config={})
    registry.add_driver(simulator.name, simulator)
    return registry


def serve(bind: str | None = None) -> grpc.Server:
    ensure_generated()

    from eigen_internal.v1 import driver_manager_service_pb2_grpc as drv_pb_grpc
    from eigen_internal.v1 import driver_manager_service_pb2 as drv_pb
    from eigen_internal.v1 import types_pb2 as types_pb

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    drv_pb_grpc.add_DriverManagerServiceServicer_to_server(
        DriverManagerService(drv_pb=drv_pb, types_pb=types_pb, registry=_default_registry(types_pb)),
        server,
    )

    addr = bind or os.getenv("DRIVER_MANAGER_GRPC_BIND", "0.0.0.0:50061")
    server.add_insecure_port(addr)
    server.start()
    _LOG.info("driver-manager gRPC server started on %s", addr)
    return server
