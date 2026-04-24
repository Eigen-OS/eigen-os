from __future__ import annotations

import grpc
import pytest

from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def _request(*, metadata: dict[str, str] | None = None, source: bytes = b"fn main() {}\n") -> job_pb.SubmitJobRequest:
    return job_pb.SubmitJobRequest(
        name="idem-job",
        target="sim:local",
        eigen_lang=types_pb.EigenLangSource(
            source=source,
            entrypoint="main",
            sha256="abc123",
        ),
        metadata=metadata or {},
    )


def test_submit_job_is_idempotent_by_client_request_id(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    req = _request(metadata={"client_request_id": "req-001"})
    first = stub.SubmitJob(req)
    second = stub.SubmitJob(req)

    assert first.job_id
    assert second.job_id == first.job_id


def test_idempotency_key_reuse_with_different_payload_is_invalid_argument(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    first = _request(metadata={"client_request_id": "req-002"}, source=b"fn main() { a() }\n")
    second = _request(metadata={"client_request_id": "req-002"}, source=b"fn main() { b() }\n")

    ok = stub.SubmitJob(first)
    assert ok.job_id

    with pytest.raises(grpc.RpcError) as err:
        stub.SubmitJob(second)

    assert err.value.code() == grpc.StatusCode.INVALID_ARGUMENT


def test_submit_job_is_idempotent_by_eigen_lang_sha256_fallback(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    req = _request()
    first = stub.SubmitJob(req)
    second = stub.SubmitJob(req)

    assert second.job_id == first.job_id
