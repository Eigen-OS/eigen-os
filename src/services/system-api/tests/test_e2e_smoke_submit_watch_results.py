from __future__ import annotations

import grpc
import pytest

from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def _submit_bell_state_job(stub: job_pb_grpc.JobServiceStub) -> str:
    req = job_pb.SubmitJobRequest(
        name="e2e-smoke-bell-state",
        target="sim:local",
        eigen_lang=types_pb.EigenLangSource(
            source=b"""# Bell-state placeholder program for simulator smoke test\nfn main() {}\n""",
            entrypoint="main",
        ),
    )
    resp = stub.SubmitJob(req)
    return resp.job_id


def test_e2e_smoke_submit_watch_results(grpc_addr: str):
    """High-signal MVP smoke: submit -> watch -> status -> results."""

    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    job_id = _submit_bell_state_job(stub)

    with pytest.raises(grpc.RpcError) as err:
        stub.GetJobResults(job_pb.GetJobResultsRequest(job_id=job_id))
    assert err.value.code() == grpc.StatusCode.FAILED_PRECONDITION

    # submit -> watch
    stream = stub.StreamJobUpdates(job_pb.StreamJobUpdatesRequest(job_id=job_id))
    updates = [item.update for item in stream]

    assert len(updates) >= 3

    # watch stream must be monotonic by event_seq and terminal at the end
    seqs = [int(u.event_seq) for u in updates]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs)

    terminal = {
        types_pb.JOB_STATE_DONE,
        types_pb.JOB_STATE_ERROR,
        types_pb.JOB_STATE_CANCELLED,
        types_pb.JOB_STATE_TIMEOUT,
    }
    assert updates[-1].state in terminal

    # status endpoint should reflect terminal state after stream completion
    status = stub.GetJobStatus(job_pb.GetJobStatusRequest(job_id=job_id)).status
    assert status.job_id == job_id
    assert status.state == updates[-1].state

    # results endpoint must return counts map and metadata map
    results = stub.GetJobResults(job_pb.GetJobResultsRequest(job_id=job_id))
    assert results.job_id == job_id
    assert results.state == types_pb.JOB_STATE_DONE
    assert len(results.counts) > 0
    assert all(isinstance(bitstring, str) and bitstring for bitstring in results.counts)
    assert all(isinstance(count, int) and count >= 0 for count in results.counts.values())
    assert len(results.metadata) > 0
    