"""eigen-compiler gRPC server bootstrap."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import logging
import os
import sys
from concurrent import futures
import threading
from pathlib import Path

import grpc

from .advisor_boundary import NeuroSymbolicService, render_metrics_text
from .grpc_impl import CompilationService, reset_metrics
from .proto_gen import ensure_generated

_LOG = logging.getLogger("eigen_compiler")

class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in {"/", "/metrics"}:
            self.send_response(404)
            self.end_headers()
            return
        payload = render_metrics_text().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

def _start_metrics_server(bind: str) -> ThreadingHTTPServer:
    host, port_str = bind.rsplit(":", 1)
    server = ThreadingHTTPServer((host, int(port_str)), _MetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def serve(bind: str | None = None, metrics_bind: str | None = None) -> grpc.Server:
    reset_metrics()
    ensure_generated()
    _ensure_local_eigen_namespace()

    from eigen.internal.v1 import compilation_service_pb2 as comp_pb
    from eigen.internal.v1 import compilation_service_pb2_grpc as comp_pb_grpc
    from eigen.internal.v1 import neuro_symbolic_service_pb2 as nsc_pb
    from eigen.internal.v1 import neuro_symbolic_service_pb2_grpc as nsc_pb_grpc
    from eigen.internal.v1 import types_pb2 as types_pb

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    comp_pb_grpc.add_CompilationServiceServicer_to_server(
        CompilationService(comp_pb=comp_pb, types_pb=types_pb),
        server,
    )
    nsc_pb_grpc.add_NeuroSymbolicServiceServicer_to_server(
        NeuroSymbolicService(nsc_pb=nsc_pb),
        server,
    )

    addr = bind or os.getenv("EIGEN_COMPILER_GRPC_BIND", "0.0.0.0:50071")
    server.add_insecure_port(addr)
    server.start()
    metrics_addr = metrics_bind or os.getenv("EIGEN_COMPILER_METRICS_BIND", "127.0.0.1:50072")
    metrics_server = _start_metrics_server(metrics_addr)
    setattr(server, "_metrics_http_server", metrics_server)
    setattr(server, "_metrics_bind", metrics_addr)
    _LOG.info("eigen-compiler gRPC server started on %s", addr)
    _LOG.info("eigen-compiler metrics server started on %s", metrics_addr)
    return server


def _ensure_local_eigen_namespace() -> None:
    """Make generated ``eigen.internal`` stubs importable in mixed service envs."""
    local_src = Path(__file__).resolve().parents[1]
    local_eigen = str(local_src / "eigen")
    if str(local_src) not in sys.path:
        sys.path.insert(0, str(local_src))

    eigen_pkg = sys.modules.get("eigen")
    if eigen_pkg is None:
        importlib.import_module("eigen")
        eigen_pkg = sys.modules.get("eigen")

    package_path = getattr(eigen_pkg, "__path__", None)
    if package_path is not None and local_eigen not in package_path:
        package_path.insert(0, local_eigen)
