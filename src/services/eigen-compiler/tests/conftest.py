from __future__ import annotations

import socket
import time
from typing import Iterator

import pytest

from eigen_compiler.grpc_server import serve


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def grpc_addr() -> Iterator[str]:
    addr = f"127.0.0.1:{_free_port()}"
    server = serve(bind=addr)
    time.sleep(0.05)
    yield addr
    server.stop(grace=None)
