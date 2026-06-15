from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterator

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

from system_api.qfs_store import QFS_STORE


REPO_ROOT = Path(__file__).resolve().parents[4]
RUST_ROOT = REPO_ROOT / "src" / "rust"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def kernel_addr(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    cargo = shutil.which("cargo")
    if cargo is None:
        pytest.skip("cargo is required to start the kernel integration test server")

    port = _free_port()
    addr = f"127.0.0.1:{port}"
    qfs_root = tmp_path_factory.mktemp("kernel-qfs")

    env = os.environ.copy()
    env.update(
        {
            "EIGEN_KERNEL_ADDR": addr,
            "KERNEL_ENDPOINT": addr,
            "KERNEL_GRPC_ENDPOINT": addr,
            "EIGEN_QFS_ROOT": str(qfs_root),
        }
    )

    proc = subprocess.Popen(
        [cargo, "run", "--quiet", "-p", "eigen-kernel", "--bin", "eigen-kernel"],
        cwd=str(RUST_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.time() + 120
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"kernel test server exited early with code {proc.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                break
        except OSError:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError(f"kernel test server did not start on {addr}")

    yield addr

    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=15)


@pytest.fixture(scope="module")
def grpc_addr(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    previous_kernel_addr = os.environ.get("EIGEN_KERNEL_ADDR")
    previous_kernel_endpoint = os.environ.get("KERNEL_ENDPOINT")
    previous_kernel_grpc_endpoint = os.environ.get("KERNEL_GRPC_ENDPOINT")
    previous_kernel_addr = os.environ.get("EIGEN_KERNEL_ADDR")
    previous_kernel_endpoint = os.environ.get("KERNEL_ENDPOINT")
    previous_kernel_grpc_endpoint = os.environ.get("KERNEL_GRPC_ENDPOINT")
    port = _free_port()
    addr = f"127.0.0.1:{port}"
    previous_store_path = os.environ.get("SYSTEM_API_IDEMPOTENCY_STORE_PATH")
    previous_qfs_root = os.environ.get("EIGEN_QFS_LOCAL_ROOT")
    os.environ["SYSTEM_API_IDEMPOTENCY_STORE_PATH"] = str(
        tmp_path_factory.mktemp("system-api") / "idempotency.json"
    )
    os.environ["EIGEN_QFS_LOCAL_ROOT"] = str(tmp_path_factory.mktemp("system-api-qfs") / "qfs")
    os.environ.pop("EIGEN_KERNEL_ADDR", None)
    os.environ.pop("KERNEL_ENDPOINT", None)
    os.environ.pop("KERNEL_GRPC_ENDPOINT", None)
    os.environ.pop("EIGEN_KERNEL_ADDR", None)
    os.environ.pop("KERNEL_ENDPOINT", None)
    os.environ.pop("KERNEL_GRPC_ENDPOINT", None)

    from system_api.grpc_server import serve

    server = serve(bind=addr)

    # Give the server a moment to start.
    time.sleep(0.05)

    yield addr

    server.stop(grace=None)
    if previous_store_path is None:
        os.environ.pop("SYSTEM_API_IDEMPOTENCY_STORE_PATH", None)
    else:
        os.environ["SYSTEM_API_IDEMPOTENCY_STORE_PATH"] = previous_store_path
    if previous_qfs_root is None:
        os.environ.pop("EIGEN_QFS_LOCAL_ROOT", None)
    else:
        os.environ["EIGEN_QFS_LOCAL_ROOT"] = previous_qfs_root

    if previous_kernel_addr is None:
        os.environ.pop("EIGEN_KERNEL_ADDR", None)
    else:
        os.environ["EIGEN_KERNEL_ADDR"] = previous_kernel_addr
    if previous_kernel_endpoint is None:
        os.environ.pop("KERNEL_ENDPOINT", None)
    else:
        os.environ["KERNEL_ENDPOINT"] = previous_kernel_endpoint
    if previous_kernel_grpc_endpoint is None:
        os.environ.pop("KERNEL_GRPC_ENDPOINT", None)
    else:
        os.environ["KERNEL_GRPC_ENDPOINT"] = previous_kernel_grpc_endpoint
 

    if previous_kernel_addr is None:
        os.environ.pop("EIGEN_KERNEL_ADDR", None)
    else:
        os.environ["EIGEN_KERNEL_ADDR"] = previous_kernel_addr
    if previous_kernel_endpoint is None:
        os.environ.pop("KERNEL_ENDPOINT", None)
    else:
        os.environ["KERNEL_ENDPOINT"] = previous_kernel_endpoint
    if previous_kernel_grpc_endpoint is None:
        os.environ.pop("KERNEL_GRPC_ENDPOINT", None)
    else:
        os.environ["KERNEL_GRPC_ENDPOINT"] = previous_kernel_grpc_endpoint


@pytest.fixture(autouse=True)
def _clean_qfs_store() -> Iterator[None]:
    QFS_STORE.clear()
    yield
    QFS_STORE.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
