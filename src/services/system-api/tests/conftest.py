from __future__ import annotations

import socket
import time
from typing import Iterator

import pytest

from system_api.grpc_server import serve


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def grpc_addr() -> Iterator[str]:
    port = _free_port()
    addr = f"127.0.0.1:{port}"

    server = serve(bind=addr)

    # Give the server a moment to start.
    time.sleep(0.05)

    yield addr

    server.stop(grace=None)
