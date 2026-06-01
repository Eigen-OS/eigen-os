from __future__ import annotations

import grpc
import pytest
from google.rpc import error_details_pb2
from grpc_status import rpc_status

from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import device_service_pb2 as dev_pb  # noqa: E402
from eigen.api.v1 import device_service_pb2_grpc as dev_pb_grpc  # noqa: E402
from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def _submit_request(envelope: types_pb.ApiRequestEnvelope | None = None) -> job_pb.SubmitJobRequest:
    kwargs = {}
    if envelope is not None:
        kwargs["envelope"] = envelope
    return job_pb.SubmitJobRequest(
        name="versioned-envelope-job",
        target="sim:local",
        eigen_lang=types_pb.EigenLangSource(source=b"fn main() {}\n", entrypoint="main", sha256="env-v1"),
        **kwargs,
    )


def _error_info(err: grpc.RpcError) -> error_details_pb2.ErrorInfo:
    status = rpc_status.from_call(err)
    assert status is not None
    info = error_details_pb2.ErrorInfo()
    assert status.details
    assert status.details[0].Unpack(info)
    return info


def test_missing_contract_version_defaults_to_product_1(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    job_stub = job_pb_grpc.JobServiceStub(channel)
    dev_stub = dev_pb_grpc.DeviceServiceStub(channel)

    submitted = job_stub.SubmitJob(_submit_request())
    assert submitted.job_id

    status = job_stub.GetJobStatus(job_pb.GetJobStatusRequest(job_id=submitted.job_id))
    assert status.status.job_id == submitted.job_id

    devices = dev_stub.ListDevices(dev_pb.ListDevicesRequest())
    assert [device.device_id for device in devices.devices] == ["sim:local"]


@pytest.mark.parametrize(
    "rpc_request, code, reason",
    [
        (
            job_pb.GetJobStatusRequest(
                job_id="job_missing",
                envelope=types_pb.ApiRequestEnvelope(contract_version="not-semver"),
            ),
            grpc.StatusCode.INVALID_ARGUMENT,
            "EIGEN_PUBLIC_CONTRACT_VERSION_MALFORMED",
        ),
        (
            job_pb.GetJobStatusRequest(
                job_id="job_missing",
                envelope=types_pb.ApiRequestEnvelope(contract_version="2.0.0"),
            ),
            grpc.StatusCode.FAILED_PRECONDITION,
            "EIGEN_PUBLIC_CONTRACT_VERSION_UNSUPPORTED",
        ),
        (
            job_pb.GetJobStatusRequest(
                job_id="job_missing",
                envelope=types_pb.ApiRequestEnvelope(contract_version="1.1.0"),
            ),
            grpc.StatusCode.FAILED_PRECONDITION,
            "EIGEN_PUBLIC_CONTRACT_VERSION_UNSUPPORTED",
        ),
    ],
)
def test_job_read_requests_reject_malformed_future_and_unsupported_versions(
    grpc_addr: str,
    rpc_request: job_pb.GetJobStatusRequest,
    code: grpc.StatusCode,
    reason: str,
) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        stub.GetJobStatus(rpc_request)

    assert err.value.code() == code
    assert _error_info(err.value).reason == reason


def test_metadata_contract_version_is_validated_before_device_dispatch(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = dev_pb_grpc.DeviceServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        stub.ListDevices(
            dev_pb.ListDevicesRequest(),
            metadata=(("x-eigen-contract-version", "9.0.0"),),
        )

    assert err.value.code() == grpc.StatusCode.FAILED_PRECONDITION
    info = _error_info(err.value)
    assert info.reason == "EIGEN_PUBLIC_CONTRACT_VERSION_UNSUPPORTED"
    assert info.metadata["supported_contract_version"] == "1.0.0"
    