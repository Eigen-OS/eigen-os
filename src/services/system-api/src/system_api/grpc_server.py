"""System API gRPC server (skeleton).

Issue #24 acceptance criteria:
- starts locally
- serves JobService + DeviceService
- validates requests (basic required fields)
- uses gRPC status codes (no `success=false`)
- BadRequest field violations for validation failures
- logs include trace_id/traceparent + request id
"""

from __future__ import annotations

import logging
import os
from concurrent import futures

import grpc

from .grpc_impl import DeviceService, JobService
from .proto_gen import ensure_generated

_LOG = logging.getLogger("system_api")


def serve(bind: str | None = None) -> grpc.Server:
    """Create, start and return the gRPC server."""

    # Ensure generated stubs exist (dev-friendly).
    ensure_generated()

    # Imports must happen after ensure_generated().
    from eigen_api.v1 import device_service_pb2 as dev_pb
    from eigen_api.v1 import device_service_pb2_grpc as dev_pb_grpc
    from eigen_api.v1 import job_service_pb2 as job_pb
    from eigen_api.v1 import job_service_pb2_grpc as job_pb_grpc
    from eigen_api.v1 import types_pb2 as types_pb

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))

    job_pb_grpc.add_JobServiceServicer_to_server(
        JobService(job_pb=job_pb, types_pb=types_pb),
        server,
    )
    dev_pb_grpc.add_DeviceServiceServicer_to_server(
        DeviceService(dev_pb=dev_pb, types_pb=types_pb),
        server,
    )

    addr = bind or os.getenv("SYSTEM_API_GRPC_BIND", "0.0.0.0:50051")
    server.add_insecure_port(addr)

    server.start()
    _LOG.info("system-api gRPC server started on %s", addr)

    return server
