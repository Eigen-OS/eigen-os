from __future__ import annotations

import socket
import time
import urllib.request

import grpc
import pytest
from google.rpc import error_details_pb2
from grpc_status import rpc_status

from system_api.grpc_server import serve
from system_api.observability import start_metrics_server
from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import device_service_pb2 as dev_pb  # noqa: E402
from eigen.api.v1 import device_service_pb2_grpc as dev_pb_grpc  # noqa: E402
from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _extract_bad_request(err: grpc.RpcError) -> error_details_pb2.BadRequest:
    st = rpc_status.from_call(err)
    assert st is not None
    bad = error_details_pb2.BadRequest()
    assert len(st.details) >= 1
    assert st.details[0].Unpack(bad)
    return bad


def test_auth_static_token_mode_requires_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYSTEM_API_AUTH_MODE", "static_token")
    monkeypatch.setenv("SYSTEM_API_AUTH_TOKEN", "test-token")

    addr = f"127.0.0.1:{_free_port()}"
    server = serve(bind=addr)
    time.sleep(0.05)

    try:
        channel = grpc.insecure_channel(addr)
        stub = dev_pb_grpc.DeviceServiceStub(channel)

        with pytest.raises(grpc.RpcError) as exc:
            stub.ListDevices(dev_pb.ListDevicesRequest())
        assert exc.value.code() == grpc.StatusCode.UNAUTHENTICATED

        with pytest.raises(grpc.RpcError) as exc_perm:
            stub.ListDevices(
                dev_pb.ListDevicesRequest(),
                metadata=(("authorization", "Bearer test-token"),),
            )
        assert exc_perm.value.code() == grpc.StatusCode.PERMISSION_DENIED

        ok = stub.ListDevices(
            dev_pb.ListDevicesRequest(),
            metadata=(
                ("authorization", "Bearer test-token"),
                ("x-eigen-permissions", "devices:list"),
            ),
        )
        assert len(ok.devices) == 1
    finally:
        server.stop(grace=None)


def test_submit_job_enforces_source_and_yaml_size_limits(
    grpc_addr: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SYSTEM_API_MAX_PROGRAM_SOURCE_BYTES", "8")
    monkeypatch.setenv("SYSTEM_API_MAX_JOBSPEC_YAML_BYTES", "10")

    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    with pytest.raises(grpc.RpcError) as exc:
        stub.SubmitJob(
            job_pb.SubmitJobRequest(
                name="size-check",
                target="sim:local",
                eigen_lang=types_pb.EigenLangSource(
                    source=b"def main():\n    return 1",
                    entrypoint="main",
                ),
                metadata={"jobspec_yaml": "a: 1\nb: 2\nc: 3"},
            )
        )

    assert exc.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(exc.value)
    fields = {v.field for v in bad.field_violations}
    assert "eigen_lang.source" in fields
    assert "metadata[jobspec_yaml]" in fields


def test_authz_readonly_cannot_submit_but_can_list_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYSTEM_API_AUTH_MODE", "static_token")
    monkeypatch.setenv("SYSTEM_API_AUTH_TOKEN", "readonly-token")
    monkeypatch.setenv("SYSTEM_API_AUTH_ROLES", "readonly")

    addr = f"127.0.0.1:{_free_port()}"
    server = serve(bind=addr)
    time.sleep(0.05)

    try:
        channel = grpc.insecure_channel(addr)
        job_stub = job_pb_grpc.JobServiceStub(channel)
        dev_stub = dev_pb_grpc.DeviceServiceStub(channel)
        md = (("authorization", "Bearer readonly-token"),)

        ok = dev_stub.ListDevices(dev_pb.ListDevicesRequest(), metadata=md)
        assert len(ok.devices) == 1

        with pytest.raises(grpc.RpcError) as exc:
            job_stub.SubmitJob(
                job_pb.SubmitJobRequest(
                    name="denied-submit",
                    target="sim:local",
                    eigen_lang=types_pb.EigenLangSource(source=b"def main():\n    return 0", entrypoint="main"),
                ),
                metadata=md,
            )
        assert exc.value.code() == grpc.StatusCode.PERMISSION_DENIED
    finally:
        server.stop(grace=None)


def test_metrics_include_authz_denied_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYSTEM_API_AUTH_MODE", "static_token")
    monkeypatch.setenv("SYSTEM_API_AUTH_TOKEN", "readonly-metrics")
    monkeypatch.setenv("SYSTEM_API_AUTH_ROLES", "readonly")
    metrics_port = _free_port()
    monkeypatch.setenv("SYSTEM_API_METRICS_PORT", str(metrics_port))

    addr = f"127.0.0.1:{_free_port()}"
    metrics_server = start_metrics_server(metrics_port)
    server = serve(bind=addr)
    time.sleep(0.05)

    try:
        channel = grpc.insecure_channel(addr)
        job_stub = job_pb_grpc.JobServiceStub(channel)
        md = (("authorization", "Bearer readonly-metrics"),)
        with pytest.raises(grpc.RpcError):
            job_stub.CancelJob(job_pb.CancelJobRequest(job_id="job_123"), metadata=md)

        with urllib.request.urlopen(f"http://127.0.0.1:{metrics_port}/metrics", timeout=2.0) as resp:
            body = resp.read().decode("utf-8")
        assert "eigen_api_authz_denied_total" in body
    finally:
        server.stop(grace=None)
        metrics_server.shutdown()
