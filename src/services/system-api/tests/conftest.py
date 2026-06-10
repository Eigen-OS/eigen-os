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

from system_api.grpc_server import serve
from system_api.qfs_store import QFS_STORE


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def grpc_addr(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    port = _free_port()
    addr = f"127.0.0.1:{port}"
    previous_store_path = os.environ.get("SYSTEM_API_IDEMPOTENCY_STORE_PATH")
    os.environ["SYSTEM_API_IDEMPOTENCY_STORE_PATH"] = str(
        tmp_path_factory.mktemp("system-api") / "idempotency.json"
    )

    server = serve(bind=addr)

    # Give the server a moment to start.
    time.sleep(0.05)

    yield addr

    server.stop(grace=None)
    if previous_store_path is None:
        os.environ.pop("SYSTEM_API_IDEMPOTENCY_STORE_PATH", None)
    else:
        os.environ["SYSTEM_API_IDEMPOTENCY_STORE_PATH"] = previous_store_path


@pytest.fixture(autouse=True)
def _clean_qfs_store() -> Iterator[None]:
    QFS_STORE.clear()
    yield
    QFS_STORE.clear()

@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
