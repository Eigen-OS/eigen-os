"""neuro-symbolic-service gRPC server bootstrap."""

from __future__ import annotations

import logging
import os
from concurrent import futures

import grpc

from .grpc_impl import NeuroSymbolicService
from .observability import set_ready

_LOG = logging.getLogger("neuro_symbolic_service")


def serve(bind: str | None = None, metrics_bind: str | None = None) -> grpc.Server:
    from eigen.internal.v1 import neuro_symbolic_service_pb2_grpc as nsc_pb_grpc

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    nsc_pb_grpc.add_NeuroSymbolicServiceServicer_to_server(NeuroSymbolicService(), server)
    addr = bind or os.getenv("NEURO_SYMBOLIC_GRPC_BIND", "0.0.0.0:50081")
    server.add_insecure_port(addr)
    server.start()
    set_ready(True)
    _LOG.info("neuro-symbolic-service gRPC server started on %s", addr)
    if metrics_bind is not None:
        _LOG.info("metrics bind requested on %s", metrics_bind)
    return server
