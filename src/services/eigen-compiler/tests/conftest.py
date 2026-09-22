from __future__ import annotations

import os
import subprocess
import socket
import sys
import time
from typing import Iterator
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

try:
    import google.rpc  # type: ignore
except ModuleNotFoundError:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "googleapis-common-protos>=1.72",
            "grpcio-status>=1.76",
        ],
        check=True,
    )

import pytest


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def compiler_server() -> Iterator[tuple[str, str, object]]:
    from eigen_compiler.grpc_impl import reset_metrics
    from eigen_compiler.grpc_server import serve

    reset_metrics()
    grpc = f"127.0.0.1:{_free_port()}"
    metrics = f"127.0.0.1:{_free_port()}"
    server = serve(bind=grpc, metrics_bind=metrics)
    time.sleep(0.05)
    yield grpc, metrics, server
    metrics_server = getattr(server, "_metrics_http_server", None)
    if metrics_server is not None:
        metrics_server.shutdown()
        metrics_server.server_close()
    server.stop(grace=None)

@pytest.fixture(autouse=True)
def _reset_compiler_metrics_between_tests() -> Iterator[None]:
    from eigen_compiler.grpc_impl import reset_metrics

    reset_metrics()
    yield
    reset_metrics()

@pytest.fixture(scope="module")
def grpc_addr(compiler_server: tuple[str, str, object]) -> Iterator[str]:
    yield compiler_server[0]


@pytest.fixture(scope="module")
def metrics_addr(compiler_server: tuple[str, str, object]) -> Iterator[str]:
    yield compiler_server[1]
