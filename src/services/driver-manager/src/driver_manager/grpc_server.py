"""driver-manager gRPC server bootstrap."""

from __future__ import annotations

import logging
import os
from concurrent import futures

import grpc

from .grpc_impl import DriverManagerService
from .proto_gen import ensure_generated
from .qiskit_runtime_driver import QiskitRuntimeDriver
from .registry import DriverRegistry
from .simulator_driver import SimulatorDriver

_LOG = logging.getLogger("driver_manager")


def _driver_config_from_env(prefix: str) -> dict[str, str]:
    cfg: dict[str, str] = {}
    needle = f"{prefix}_"
    for key, value in os.environ.items():
        if key.startswith(needle):
            cfg[key[len(needle) :].lower()] = value
    return cfg


def _build_registry(types_pb) -> DriverRegistry:
    registry = DriverRegistry()

    simulator = SimulatorDriver(types_pb=types_pb)
    simulator.initialize(config={})
    registry.add_driver(simulator.name, simulator)

    if os.getenv("DRIVER_MANAGER_QISKIT_RUNTIME_ENABLED", "false").lower() in {"1", "true", "yes"}:
        qiskit = QiskitRuntimeDriver(types_pb=types_pb)
        qiskit.initialize(config=_driver_config_from_env("DRIVER_MANAGER_QISKIT_RUNTIME"))
        registry.add_driver(qiskit.name, qiskit)

    return registry


def serve(bind: str | None = None) -> grpc.Server:
    ensure_generated()

    from eigen_internal.v1 import driver_manager_service_pb2_grpc as drv_pb_grpc
    from eigen_internal.v1 import driver_manager_service_pb2 as drv_pb
    from eigen_internal.v1 import types_pb2 as types_pb

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    registry = _build_registry(types_pb)
    drv_pb_grpc.add_DriverManagerServiceServicer_to_server(
        DriverManagerService(drv_pb=drv_pb, types_pb=types_pb, registry=registry),
        server,
    )

    addr = bind or os.getenv("DRIVER_MANAGER_GRPC_BIND", "0.0.0.0:50061")
    server.add_insecure_port(addr)
    server.start()
    setattr(server, "driver_registry", registry)
    _LOG.info("driver-manager gRPC server started on %s", addr)
    return server
