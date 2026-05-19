from __future__ import annotations

import json
from pathlib import Path

import grpc

from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402

FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "contracts"
    / "system_api_rest_v1"
    / "parity_matrix_v1_0_0.json"
)


def _submit(stub: job_pb_grpc.JobServiceStub, *, target: str = "sim:local") -> str:
    req = job_pb.SubmitJobRequest(
        name="phase8d-rest-parity",
        target=target,
        eigen_lang=types_pb.EigenLangSource(source=b"fn main() {}\n", entrypoint="main"),
    )
    return stub.SubmitJob(req).job_id


def _as_rest_status(status) -> dict[str, object]:
    return {
        "job_id": status.job_id,
        "state": types_pb.JobState.Name(status.state).replace("JOB_STATE_", ""),
        "message": status.message,
    }


def _as_rest_results(results) -> dict[str, object]:
    return {
        "job_id": results.job_id,
        "state": types_pb.JobState.Name(results.state).replace("JOB_STATE_", ""),
        "counts": dict(results.counts),
        "metadata": dict(results.metadata),
    }


def test_phase8d_rest_parity_and_compatibility_matrix_fixture(grpc_addr: str) -> None:
    matrix = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert matrix["artifact_version"] == "1.0.0"
    assert matrix["rest_parity"]["paths"] == ["submit", "watch", "results", "cancel"]

    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    # submit + watch + results parity
    job_id = _submit(stub)
    updates = [item.update for item in stub.StreamJobUpdates(job_pb.StreamJobUpdatesRequest(job_id=job_id))]
    seqs = [int(u.event_seq) for u in updates]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs)

    status = stub.GetJobStatus(job_pb.GetJobStatusRequest(job_id=job_id)).status
    rest_status = _as_rest_status(status)
    assert rest_status["state"] in matrix["rest_parity"]["required_terminal_states"]

    results = stub.GetJobResults(job_pb.GetJobResultsRequest(job_id=job_id))
    rest_results = _as_rest_results(results)
    assert rest_results["state"] == "DONE"
    assert rest_results["counts"]

    # cancel parity
    cancellable_job_id = _submit(stub, target="emu:real-hifi")
    cancel = stub.CancelJob(job_pb.CancelJobRequest(job_id=cancellable_job_id))
    assert cancel.accepted is True
    cancel_status = stub.GetJobStatus(job_pb.GetJobStatusRequest(job_id=cancellable_job_id)).status
    rest_cancel = _as_rest_status(cancel_status)
    assert rest_cancel["state"] == "CANCELLED"
    