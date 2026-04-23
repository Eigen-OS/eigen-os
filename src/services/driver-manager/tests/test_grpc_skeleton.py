from __future__ import annotations

import socket
import time
from typing import Iterator

import grpc
import pytest

from driver_manager.grpc_server import serve
from driver_manager.proto_gen import ensure_generated

ensure_generated()

from eigen_internal.v1 import driver_manager_service_pb2 as drv_pb  # noqa: E402
from eigen_internal.v1 import driver_manager_service_pb2_grpc as drv_pb_grpc  # noqa: E402


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


def test_list_devices_returns_stub_device(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    resp = stub.ListDevices(drv_pb.ListDevicesRequest())

    assert len(resp.devices) == 1
    assert resp.devices[0].device_id == "sim:stub"


def test_get_device_status_returns_stub_status(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    resp = stub.GetDeviceStatus(drv_pb.DeviceStatusRequest(device_id="sim:stub"))

    assert resp.device_id == "sim:stub"
    assert resp.metadata["stub"] == "true"


def test_get_device_status_validates_device_id(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        stub.GetDeviceStatus(drv_pb.DeviceStatusRequest())

    assert err.value.code() == grpc.StatusCode.INVALID_ARGUMENT
