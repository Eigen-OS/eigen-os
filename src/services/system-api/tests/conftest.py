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


@pytest.fixture(scope="session", autouse=True)
def _shared_qfs_root(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    previous_local_root = os.environ.get("EIGEN_QFS_LOCAL_ROOT")
    previous_root = os.environ.get("EIGEN_QFS_ROOT")
    previous_backend = os.environ.get("EIGEN_QFS_BACKEND")
    qfs_root = tmp_path_factory.mktemp("system-api-qfs")
    os.environ["EIGEN_QFS_LOCAL_ROOT"] = str(qfs_root)
    os.environ["EIGEN_QFS_ROOT"] = str(qfs_root)
    os.environ["EIGEN_QFS_BACKEND"] = "local"
    try:
        yield
    finally:
        if previous_local_root is None:
            os.environ.pop("EIGEN_QFS_LOCAL_ROOT", None)
        else:
            os.environ["EIGEN_QFS_LOCAL_ROOT"] = previous_local_root
        if previous_root is None:
            os.environ.pop("EIGEN_QFS_ROOT", None)
        else:
            os.environ["EIGEN_QFS_ROOT"] = previous_root
        if previous_backend is None:
            os.environ.pop("EIGEN_QFS_BACKEND", None)
        else:
            os.environ["EIGEN_QFS_BACKEND"] = previous_backend


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _start_python_service(module: str, cwd: Path, env: dict[str, str], ready_port: int) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", module],
        cwd=str(cwd),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 120
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"{module} exited early with code {proc.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", ready_port), timeout=0.25):
                break
        except OSError:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError(f"{module} did not start on port {ready_port}")
    return proc


@pytest.fixture(scope="session")
def kernel_addr(_shared_qfs_root: None) -> Iterator[str]:
    cargo = shutil.which("cargo")
    if cargo is None:
        pytest.skip("cargo is required to start the kernel integration test server")

    kernel_port = _free_port()
    compiler_port = _free_port()
    compiler_metrics_port = _free_port()
    driver_port = _free_port()
    driver_metrics_port = _free_port()
    addr = f"127.0.0.1:{kernel_port}"
    compiler_addr = f"127.0.0.1:{compiler_port}"
    driver_addr = f"127.0.0.1:{driver_port}"
    qfs_root = Path(os.environ["EIGEN_QFS_LOCAL_ROOT"])

    env = os.environ.copy()
    env.update(
        {
            "EIGEN_KERNEL_ADDR": addr,
            "KERNEL_ENDPOINT": addr,
            "KERNEL_GRPC_ENDPOINT": addr,
            "EIGEN_QFS_ROOT": str(qfs_root),
            "EIGEN_COMPILER_ENDPOINT": f"http://{compiler_addr}",
            "DRIVER_MANAGER_ENDPOINT": f"http://{driver_addr}",
            "EIGEN_COMPILER_GRPC_BIND": compiler_addr,
            "EIGEN_COMPILER_METRICS_PORT": str(compiler_metrics_port),
            "DRIVER_MANAGER_GRPC_BIND": driver_addr,
            "DRIVER_MANAGER_METRICS_PORT": str(driver_metrics_port),
            "PYTHONPATH": os.pathsep.join(
                [
                    str(REPO_ROOT / "src" / "services" / "eigen-compiler" / "src"),
                    str(REPO_ROOT / "src" / "services" / "driver-manager" / "src"),
                    env.get("PYTHONPATH", ""),
                ]
            ).strip(os.pathsep),
        }
    )

    compiler_proc = _start_python_service(
        "eigen_compiler.main",
        REPO_ROOT / "src" / "services" / "eigen-compiler" / "src",
        env,
        compiler_metrics_port,
    )
    driver_proc = _start_python_service(
        "driver_manager.main",
        REPO_ROOT / "src" / "services" / "driver-manager" / "src",
        env,
        driver_metrics_port,
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
            with socket.create_connection(("127.0.0.1", kernel_port), timeout=0.25):
                break
        except OSError:
            time.sleep(0.1)
    else:
        proc.terminate()
        driver_proc.terminate()
        compiler_proc.terminate()
        raise RuntimeError(f"kernel test server did not start on {addr}")

    try:
        yield addr
    finally:
        proc.terminate()
        driver_proc.terminate()
        compiler_proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=15)
        for child in (driver_proc, compiler_proc):
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=15)


@pytest.fixture(scope="module")
def grpc_addr(kernel_addr: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    previous_store_path = os.environ.get("SYSTEM_API_IDEMPOTENCY_STORE_PATH")
    previous_kernel_addr = os.environ.get("EIGEN_KERNEL_ADDR")
    previous_kernel_endpoint = os.environ.get("KERNEL_ENDPOINT")
    previous_kernel_grpc_endpoint = os.environ.get("KERNEL_GRPC_ENDPOINT")
    port = _free_port()
    addr = f"127.0.0.1:{port}"
    os.environ["SYSTEM_API_IDEMPOTENCY_STORE_PATH"] = str(
        tmp_path_factory.mktemp("system-api") / "idempotency.json"
    )
    os.environ["EIGEN_KERNEL_ADDR"] = kernel_addr
    os.environ["KERNEL_ENDPOINT"] = kernel_addr
    os.environ["KERNEL_GRPC_ENDPOINT"] = kernel_addr

    from system_api.grpc_server import serve

    server = serve(bind=addr)

    time.sleep(0.05)

    yield addr

    server.stop(grace=None)
    if previous_store_path is None:
        os.environ.pop("SYSTEM_API_IDEMPOTENCY_STORE_PATH", None)
    else:
        os.environ["SYSTEM_API_IDEMPOTENCY_STORE_PATH"] = previous_store_path
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
def _clean_qfs_store(_shared_qfs_root: None) -> Iterator[None]:
    QFS_STORE.clear()
    yield
    QFS_STORE.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
