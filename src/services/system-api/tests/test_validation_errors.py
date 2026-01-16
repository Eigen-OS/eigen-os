from __future__ import annotations

import grpc
import pytest
from google.rpc import error_details_pb2
from grpc_status import rpc_status

from system_api.proto_gen import ensure_generated

# Ensure python stubs are importable before importing them.
ensure_generated()

from eigen_api.v1 import device_service_pb2 as dev_pb  # noqa: E402
from eigen_api.v1 import device_service_pb2_grpc as dev_pb_grpc  # noqa: E402
from eigen_api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen_api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402


def _extract_bad_request(err: grpc.RpcError) -> error_details_pb2.BadRequest:
    st = rpc_status.from_call(err)
    assert st is not None, "expected google.rpc.Status in trailing metadata"

    bad = error_details_pb2.BadRequest()
    assert len(st.details) >= 1
    unpacked = st.details[0].Unpack(bad)
    assert unpacked
    return bad


def test_submit_job_missing_required_fields(grpc_addr: str):
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.SubmitJob(job_pb.SubmitJobRequest())

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    bad = _extract_bad_request(e.value)
    fields = {v.field for v in bad.field_violations}

    assert "name" in fields
    assert "target" in fields
    assert "program" in fields


def test_get_job_status_missing_job_id(grpc_addr: str):
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.GetJobStatus(job_pb.JobStatusRequest())

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    bad = _extract_bad_request(e.value)
    fields = {v.field for v in bad.field_violations}
    assert "job_id" in fields


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
