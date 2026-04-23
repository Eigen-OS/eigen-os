"""eigen-compiler gRPC server bootstrap."""

from __future__ import annotations

import logging
import os
from concurrent import futures

import grpc

from .grpc_impl import CompilationService
from .proto_gen import ensure_generated

_LOG = logging.getLogger("eigen_compiler")


def serve(bind: str | None = None) -> grpc.Server:
    ensure_generated()

    from eigen.internal.v1 import compilation_service_pb2 as comp_pb
    from eigen.internal.v1 import compilation_service_pb2_grpc as comp_pb_grpc
    from eigen.internal.v1 import types_pb2 as types_pb

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    comp_pb_grpc.add_CompilationServiceServicer_to_server(
        CompilationService(comp_pb=comp_pb, types_pb=types_pb),
        server,
    )

    addr = bind or os.getenv("EIGEN_COMPILER_GRPC_BIND", "0.0.0.0:50071")
    server.add_insecure_port(addr)
    server.start()
    _LOG.info("eigen-compiler gRPC server started on %s", addr)
    return server
