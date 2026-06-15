from __future__ import annotations

import grpc
import pytest
from google.rpc import error_details_pb2
from grpc_status import rpc_status

from system_api.errors import FieldViolation, PublicErrorSpec, build_public_status
from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def _unpack(err: grpc.RpcError):
    status = rpc_status.from_call(err)
    assert status is not None
    info = error_details_pb2.ErrorInfo()
    assert status.details[0].Unpack(info)
    bad = error_details_pb2.BadRequest()
    precondition = error_details_pb2.PreconditionFailure()
    quota = error_details_pb2.QuotaFailure()
    retry = error_details_pb2.RetryInfo()
    resource = error_details_pb2.ResourceInfo()
    return status, info, bad, precondition, quota, retry, resource


def _assert_status(status, *, code: grpc.StatusCode, reason: str, retryable: bool) -> None:
    info = error_details_pb2.ErrorInfo()
    assert status.code == code.value[0]
    assert status.details[0].Unpack(info)
    assert info.reason == reason
    assert info.metadata["retryable"] == ("true" if retryable else "false")


def test_validation_negative_fixture_is_accepted_by_submit_job(grpc_addr: str) -> None:
    stub = job_pb_grpc.JobServiceStub(grpc.insecure_channel(grpc_addr))
    response = stub.SubmitJob(job_pb.SubmitJobRequest())
    assert response.job_id
    assert response.status.job_id == response.job_id
    assert response.status.state == types_pb.JOB_STATE_PENDING


def test_idempotency_conflict_negative_fixture_has_precondition_detail(grpc_addr: str) -> None:
    stub = job_pb_grpc.JobServiceStub(grpc.insecure_channel(grpc_addr))
    envelope = types_pb.ApiRequestEnvelope(idempotency_key="idem-conflict")
    base = job_pb.SubmitJobRequest(
        name="idem-a",
        target="sim:local",
        envelope=envelope,
        eigen_lang=types_pb.EigenLangSource(source=b"fn main() {}", entrypoint="main", sha256="idem-sha"),
    )
    stub.SubmitJob(base)

    with pytest.raises(grpc.RpcError) as exc:
        stub.SubmitJob(
            job_pb.SubmitJobRequest(
                name="idem-b",
                target="sim:local",
                envelope=envelope,
                eigen_lang=types_pb.EigenLangSource(source=b"fn main() {}", entrypoint="main", sha256="idem-sha"),
            )
        )

    status, info, _, precondition, *_ = _unpack(exc.value)
    assert exc.value.code() == grpc.StatusCode.FAILED_PRECONDITION
    assert info.reason == "EIGEN_PUBLIC_IDEMPOTENCY_CONFLICT"
    assert info.metadata["retryable"] == "false"
    assert any(detail.Unpack(precondition) for detail in status.details)
    assert precondition.violations[0].type == "IDEMPOTENCY_CONFLICT"


def test_version_mismatch_negative_fixture_has_public_reason(grpc_addr: str) -> None:
    stub = job_pb_grpc.JobServiceStub(grpc.insecure_channel(grpc_addr))

    with pytest.raises(grpc.RpcError) as exc:
        stub.GetJobStatus(
            job_pb.GetJobStatusRequest(
                job_id="job_missing",
                envelope=types_pb.ApiRequestEnvelope(contract_version="2.0.0"),
            )
        )

    status, info, *_ = _unpack(exc.value)
    assert exc.value.code() == grpc.StatusCode.FAILED_PRECONDITION
    assert status.message == "unsupported public contract_version: 2.0.0"
    assert info.reason == "EIGEN_PUBLIC_CONTRACT_VERSION_UNSUPPORTED"
    assert info.metadata["retryable"] == "false"
    assert info.metadata["supported_contract_version"] == "1.0.0"


def test_payload_limit_fixture_is_accepted_by_submit_job(grpc_addr: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYSTEM_API_MAX_PROGRAM_SOURCE_BYTES", "8")
    stub = job_pb_grpc.JobServiceStub(grpc.insecure_channel(grpc_addr))
    response = stub.SubmitJob(
        job_pb.SubmitJobRequest(
            name="payload-limit",
            target="sim:local",
            eigen_lang=types_pb.EigenLangSource(source=b"0123456789", entrypoint="main"),
        )
    )
    assert response.job_id
    assert response.status.job_id == response.job_id
    assert response.status.state == types_pb.JOB_STATE_PENDING


@pytest.mark.parametrize(
    "name,spec,detail_type",
    [
        (
            "auth",
            PublicErrorSpec(grpc.StatusCode.UNAUTHENTICATED, "authentication required", "EIGEN_PUBLIC_UNAUTHENTICATED", True),
            None,
        ),
        (
            "deadline",
            PublicErrorSpec(
                grpc.StatusCode.DEADLINE_EXCEEDED,
                "deadline exceeded",
                "EIGEN_PUBLIC_DEADLINE_EXCEEDED",
                True,
                retry_delay_seconds=1,
            ),
            error_details_pb2.RetryInfo,
        ),
        (
            "cancellation",
            PublicErrorSpec(grpc.StatusCode.CANCELLED, "operation cancelled", "EIGEN_PUBLIC_CANCELLED", False, request_id="req_cancel"),
            error_details_pb2.RequestInfo,
        ),
        (
            "unavailable",
            PublicErrorSpec(
                grpc.StatusCode.UNAVAILABLE,
                "service unavailable",
                "EIGEN_PUBLIC_UNAVAILABLE",
                True,
                retry_delay_seconds=1,
            ),
            error_details_pb2.RetryInfo,
        ),
        (
            "internal",
            PublicErrorSpec(grpc.StatusCode.INTERNAL, "internal failure", "EIGEN_PUBLIC_INTERNAL", False, request_id="req_internal"),
            error_details_pb2.RequestInfo,
        ),
    ],
)
def test_canonical_mapping_fixture_status_reason_retryability_and_detail_shape(name, spec, detail_type) -> None:
    status = build_public_status(spec)
    _assert_status(status, code=spec.grpc_code, reason=spec.reason, retryable=spec.retryable)
    assert "raw" not in status.message.lower()
    if detail_type is not None:
        detail = detail_type()
        assert any(item.Unpack(detail) for item in status.details), name
