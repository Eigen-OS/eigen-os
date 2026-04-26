from __future__ import annotations

import json
import time

import grpc

from system_api.proto_gen import ensure_generated
from system_api.qfs_store import QFS_STORE

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def _submit(stub: job_pb_grpc.JobServiceStub, *, target: str, metadata: dict[str, str] | None = None) -> str:
    resp = stub.SubmitJob(
        job_pb.SubmitJobRequest(
            name="e2e-real-backend",
            target=target,
            metadata=metadata or {},
            eigen_lang=types_pb.EigenLangSource(
                source=b"fn main() {}\n",
                entrypoint="main",
            ),
        )
    )
    return resp.job_id


def test_e2e_real_backend_success_persists_qfs_and_public_results(grpc_addr: str):
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)
    job_id = _submit(stub, target="emu:real-hifi")

    updates = [item.update for item in stub.StreamJobUpdates(job_pb.StreamJobUpdatesRequest(job_id=job_id))]
    assert updates[-1].state == types_pb.JOB_STATE_DONE

    results = stub.GetJobResults(job_pb.GetJobResultsRequest(job_id=job_id))
    assert results.state == types_pb.JOB_STATE_DONE
    assert dict(results.counts) == {"00": 512, "11": 512}

    qfs_results_ref = results.metadata["qfs_results_parquet"]
    stored = QFS_STORE.get_bytes(qfs_results_ref)
    assert stored is not None
    assert len(stored) == int(results.metadata["qfs_results_parquet_bytes"])


def test_e2e_real_backend_error_is_mapped_to_standard_runtime_error(grpc_addr: str):
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)
    job_id = _submit(
        stub,
        target="emu:fail",
        metadata={"backend_error_kind": "unavailable"},
    )

    updates = [item.update for item in stub.StreamJobUpdates(job_pb.StreamJobUpdatesRequest(job_id=job_id))]
    assert updates[-1].state == types_pb.JOB_STATE_ERROR

    status = stub.GetJobStatus(job_pb.GetJobStatusRequest(job_id=job_id)).status
    assert status.state == types_pb.JOB_STATE_ERROR
    assert status.error_code == "RUNTIME_BACKEND_UNAVAILABLE"

    results = stub.GetJobResults(job_pb.GetJobResultsRequest(job_id=job_id))
    assert results.state == types_pb.JOB_STATE_ERROR
    assert results.error_code == "RUNTIME_BACKEND_UNAVAILABLE"
    assert results.error_summary == "backend unavailable"
    assert results.error_details_ref.startswith(f"qfs://jobs/{job_id}/errors/")

    payload = QFS_STORE.get_bytes(results.error_details_ref)
    assert payload is not None
    details = json.loads(payload.decode("utf-8"))
    assert details["error_code"] == "RUNTIME_BACKEND_UNAVAILABLE"
    assert details["job_id"] == job_id


def test_cancel_transitions_to_terminal_state_and_cleans_temp_artifacts(grpc_addr: str):
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)
    job_id = _submit(
        stub,
        target="emu:real-hifi",
        metadata={"simulate_runtime_sec": "5"},
    )

    cancel = stub.CancelJob(job_pb.CancelJobRequest(job_id=job_id))
    assert cancel.accepted is True

    status = stub.GetJobStatus(job_pb.GetJobStatusRequest(job_id=job_id)).status
    assert status.state == types_pb.JOB_STATE_CANCELLED
    assert "cancelled" in status.message

    results = stub.GetJobResults(job_pb.GetJobResultsRequest(job_id=job_id))
    assert results.state == types_pb.JOB_STATE_CANCELLED
    assert dict(results.counts) == {}
    assert QFS_STORE.get_bytes(f"qfs://jobs/{job_id}/tmp/request.json") is None


def test_timeout_transitions_to_terminal_state_without_hanging(grpc_addr: str):
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)
    job_id = _submit(
        stub,
        target="emu:real-hifi",
        metadata={
            "simulate_runtime_sec": "5",
            "timeout_seconds": "0.05",
        },
    )

    deadline = time.time() + 1.0
    state = types_pb.JOB_STATE_UNSPECIFIED
    while time.time() < deadline:
        state = stub.GetJobStatus(job_pb.GetJobStatusRequest(job_id=job_id)).status.state
        if state == types_pb.JOB_STATE_TIMEOUT:
            break
        time.sleep(0.01)
    assert state == types_pb.JOB_STATE_TIMEOUT

    results = stub.GetJobResults(job_pb.GetJobResultsRequest(job_id=job_id))
    assert results.state == types_pb.JOB_STATE_TIMEOUT

