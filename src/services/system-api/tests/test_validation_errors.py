from __future__ import annotations

import socket
import time

import grpc
import pytest
from google.rpc import error_details_pb2
from grpc_status import rpc_status

from system_api.proto_gen import ensure_generated
from system_api.grpc_server import serve

# Ensure python stubs are importable before importing them.
ensure_generated()

from eigen.api.v1 import device_service_pb2 as dev_pb  # noqa: E402
from eigen.api.v1 import device_service_pb2_grpc as dev_pb_grpc  # noqa: E402
from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _reserve(
    stub: dev_pb_grpc.DeviceServiceStub,
    *,
    device_id: str,
    ttl_seconds: int,
    purpose: str,
    metadata=None,
) -> dev_pb.ReserveDeviceResponse:
    return stub.ReserveDevice(
        dev_pb.ReserveDeviceRequest(device_id=device_id, ttl_seconds=ttl_seconds, purpose=purpose),
        metadata=metadata,
    )


def _extract_bad_request(err: grpc.RpcError) -> error_details_pb2.BadRequest:
    st = rpc_status.from_call(err)
    assert st is not None, "expected google.rpc.Status in trailing metadata"

    bad = error_details_pb2.BadRequest()
    assert len(st.details) >= 1
    assert any(detail.Unpack(bad) for detail in st.details)
    return bad


def test_submit_job_missing_required_fields_is_accepted(grpc_addr: str):
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    response = stub.SubmitJob(job_pb.SubmitJobRequest())
    assert response.job_id
    assert response.status.job_id == response.job_id
    assert response.status.state == job_pb.JOB_STATE_PENDING


def test_get_job_status_missing_job_id(grpc_addr: str):
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.GetJobStatus(job_pb.GetJobStatusRequest())

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    bad = _extract_bad_request(e.value)
    fields = {v.field for v in bad.field_violations}
    assert "job_id" in fields


def test_unknown_job_id_returns_not_found(grpc_addr: str):
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e_status:
        stub.GetJobStatus(job_pb.GetJobStatusRequest(job_id="job_missing_123"))
    assert e_status.value.code() == grpc.StatusCode.NOT_FOUND

    with pytest.raises(grpc.RpcError) as e_results:
        stub.GetJobResults(job_pb.GetJobResultsRequest(job_id="job_missing_123"))
    assert e_results.value.code() == grpc.StatusCode.NOT_FOUND


def test_reserve_device_invalid_ttl(grpc_addr: str):
    channel = grpc.insecure_channel(grpc_addr)
    stub = dev_pb_grpc.DeviceServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.ReserveDevice(dev_pb.ReserveDeviceRequest(device_id="", ttl_seconds=0))

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    bad = _extract_bad_request(e.value)
    fields = {v.field for v in bad.field_violations}

    assert "device_id" in fields
    assert "ttl_seconds" in fields


def test_reserve_device_creates_renews_and_survives_restart(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("SYSTEM_API_AUTH_MODE", "static_token")
    monkeypatch.setenv("SYSTEM_API_AUTH_TOKEN", "reserve-token")
    monkeypatch.setenv("SYSTEM_API_AUTH_SUBJECT", "reserve-user")
    monkeypatch.setenv("SYSTEM_API_AUTH_TENANT", "reserve-tenant")
    monkeypatch.setenv("SYSTEM_API_AUTH_ROLES", "admin")
    monkeypatch.setenv("SYSTEM_API_RESERVATION_STORE_PATH", str(tmp_path / "reservations.json"))

    addr = f"127.0.0.1:{_free_port()}"
    server = serve(bind=addr)
    time.sleep(0.05)
    try:
        channel = grpc.insecure_channel(addr)
        stub = dev_pb_grpc.DeviceServiceStub(channel)
        md = (("authorization", "Bearer reserve-token"),)
        first = stub.ReserveDevice(dev_pb.ReserveDeviceRequest(device_id="sim:local", ttl_seconds=2, purpose="job-a"), metadata=md)
        second = stub.ReserveDevice(dev_pb.ReserveDeviceRequest(device_id="sim:local", ttl_seconds=3, purpose="job-a"), metadata=md)
        assert first.reservation_id == second.reservation_id
        assert (second.expires_at.seconds, second.expires_at.nanos) >= (first.expires_at.seconds, first.expires_at.nanos)
    finally:
        server.stop(0)

    server = serve(bind=addr)
    time.sleep(0.05)
    try:
        channel = grpc.insecure_channel(addr)
        stub = dev_pb_grpc.DeviceServiceStub(channel)
        md = (("authorization", "Bearer reserve-token"),)
        recovered = stub.ReserveDevice(dev_pb.ReserveDeviceRequest(device_id="sim:local", ttl_seconds=3, purpose="job-a"), metadata=md)
        assert recovered.reservation_id == first.reservation_id
    finally:
        server.stop(0)


def test_reserve_device_rejects_double_booking(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("SYSTEM_API_AUTH_MODE", "static_token")
    monkeypatch.setenv("SYSTEM_API_AUTH_TOKEN", "reserve-token")
    monkeypatch.setenv("SYSTEM_API_AUTH_SUBJECT", "reserve-user")
    monkeypatch.setenv("SYSTEM_API_AUTH_TENANT", "reserve-tenant")
    monkeypatch.setenv("SYSTEM_API_AUTH_ROLES", "admin")
    monkeypatch.setenv("SYSTEM_API_RESERVATION_STORE_PATH", str(tmp_path / "reservations.json"))

    addr = f"127.0.0.1:{_free_port()}"
    server = serve(bind=addr)
    time.sleep(0.05)
    try:
        channel = grpc.insecure_channel(addr)
        stub = dev_pb_grpc.DeviceServiceStub(channel)
        md = (("authorization", "Bearer reserve-token"),)
        _reserve(stub, device_id="sim:local", ttl_seconds=2, purpose="job-a", metadata=md)
        with pytest.raises(grpc.RpcError) as exc:
            _reserve(stub, device_id="sim:local", ttl_seconds=2, purpose="job-b", metadata=md)
        assert exc.value.code() == grpc.StatusCode.FAILED_PRECONDITION
    finally:
        server.stop(0)


def test_reserve_device_expires_and_allows_reallocation(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("SYSTEM_API_AUTH_MODE", "static_token")
    monkeypatch.setenv("SYSTEM_API_AUTH_TOKEN", "reserve-token")
    monkeypatch.setenv("SYSTEM_API_AUTH_SUBJECT", "reserve-user")
    monkeypatch.setenv("SYSTEM_API_AUTH_TENANT", "reserve-tenant")
    monkeypatch.setenv("SYSTEM_API_AUTH_ROLES", "admin")
    monkeypatch.setenv("SYSTEM_API_RESERVATION_STORE_PATH", str(tmp_path / "reservations.json"))

    addr = f"127.0.0.1:{_free_port()}"
    server = serve(bind=addr)
    time.sleep(0.05)
    try:
        channel = grpc.insecure_channel(addr)
        stub = dev_pb_grpc.DeviceServiceStub(channel)
        md = (("authorization", "Bearer reserve-token"),)
        _reserve(stub, device_id="sim:local", ttl_seconds=1, purpose="job-expire-a", metadata=md)
        time.sleep(1.2)
        recovered = _reserve(
            stub,
            device_id="sim:local",
            ttl_seconds=1,
            purpose="job-expire-b",
            metadata=md,
        )
        assert recovered.reservation_id
    finally:
        server.stop(0)
