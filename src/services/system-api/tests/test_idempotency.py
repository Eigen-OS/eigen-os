from __future__ import annotations

import grpc
import pytest

from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def _request(
    *,
    metadata: dict[str, str] | None = None,
    source: bytes = b"fn main() {}\n",
    envelope: types_pb.ApiRequestEnvelope | None = None,
) -> job_pb.SubmitJobRequest:
    kwargs = {}
    if envelope is not None:
        kwargs["envelope"] = envelope
    return job_pb.SubmitJobRequest(
        name="idem-job",
        target="sim:local",
        eigen_lang=types_pb.EigenLangSource(
            source=source,
            entrypoint="main",
            sha256="abc123",
        ),
        metadata=metadata or {},
        **kwargs,
    )


def test_submit_job_is_idempotent_by_client_request_id(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    req = _request(metadata={"client_request_id": "req-001"})
    first = stub.SubmitJob(req)
    second = stub.SubmitJob(req)

    assert first.job_id
    assert second.job_id == first.job_id


def test_idempotency_key_reuse_with_different_payload_is_already_exists(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    first = _request(metadata={"client_request_id": "req-002"}, source=b"fn main() { a() }\n")
    second = _request(metadata={"client_request_id": "req-002"}, source=b"fn main() { b() }\n")

    ok = stub.SubmitJob(first)
    assert ok.job_id

    with pytest.raises(grpc.RpcError) as err:
        stub.SubmitJob(second)

    assert err.value.code() == grpc.StatusCode.ALREADY_EXISTS


def test_submit_job_is_idempotent_by_eigen_lang_sha256_fallback(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    req = _request()
    first = stub.SubmitJob(req)
    second = stub.SubmitJob(req)

    assert second.job_id == first.job_id

def test_submit_job_accepts_product_1_envelope_idempotency_key(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    req = _request(
        envelope=types_pb.ApiRequestEnvelope(
            contract_version="1.0.0",
            request_id="request-envelope-001",
            idempotency_key="idem-envelope-001",
            tenant_id="tenant-a",
            project_id="project-a",
        )
    )

    first = stub.SubmitJob(req)
    second = stub.SubmitJob(req)

    assert first.job_id
    assert second.job_id == first.job_id


def test_submit_job_rejects_malformed_contract_version(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    req = _request(envelope=types_pb.ApiRequestEnvelope(contract_version="not-semver"))

    with pytest.raises(grpc.RpcError) as err:
        stub.SubmitJob(req)

    assert err.value.code() == grpc.StatusCode.INVALID_ARGUMENT


def test_submit_job_rejects_unsupported_contract_version(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    req = _request(envelope=types_pb.ApiRequestEnvelope(contract_version="2.0.0"))

    with pytest.raises(grpc.RpcError) as err:
        stub.SubmitJob(req)

    assert err.value.code() == grpc.StatusCode.FAILED_PRECONDITION
