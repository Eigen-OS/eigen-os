from __future__ import annotations

import json
from pathlib import Path

import grpc
import pytest

from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402

GOLDEN_RESULTS_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "runtime" / "smoke_submit_status_results.golden.json"
)


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

    # Depending on scheduler speed, results can be unavailable or already terminal.
    try:
        early_results = stub.GetJobResults(job_pb.GetJobResultsRequest(job_id=job_id))
    except grpc.RpcError as err:
        assert err.code() == grpc.StatusCode.FAILED_PRECONDITION
    else:
        assert early_results.job_id == job_id
        assert early_results.state in {
            types_pb.JOB_STATE_DONE,
            types_pb.JOB_STATE_ERROR,
            types_pb.JOB_STATE_CANCELLED,
            types_pb.JOB_STATE_TIMEOUT,
        }


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
    assert status.topology.contract_version == "1.1.0"
    assert status.topology.lineage_version == "1.1.0"
    assert status.topology.cluster_id == "cluster-local"
    assert status.topology.partition_id == "partition-0"
    assert status.topology.attempt >= 1

    # results endpoint must return counts map and metadata map
    results = stub.GetJobResults(job_pb.GetJobResultsRequest(job_id=job_id))
    assert results.job_id == job_id
    assert results.state == types_pb.JOB_STATE_DONE
    assert len(results.counts) > 0
    assert all(isinstance(bitstring, str) and bitstring for bitstring in results.counts)
    assert all(isinstance(count, int) and count >= 0 for count in results.counts.values())
    assert len(results.metadata) > 0
    fixture = json.loads(GOLDEN_RESULTS_FIXTURE.read_text(encoding="utf-8"))
    assert results.state == fixture["state"]
    assert dict(results.counts) == fixture["counts"]
    for key, template in fixture["metadata_templates"].items():
        assert results.metadata.get(key) == template.format(job_id=job_id)

    rationale = stub.GetDispatchRationale(job_pb.GetDispatchRationaleRequest(job_id=job_id)).rationale
    assert rationale.version == "2.3.0"
    assert rationale.policy_version
    assert "WEIGHTED_FAIRNESS" in rationale.reason_codes
    assert "DEVICE_SCORE" in rationale.reason_codes
    assert rationale.selected_backend == "sim:local"
    assert rationale.attributes["policy_branch"]
    assert rationale.attributes["fallback_reason"]
    assert rationale.attributes["artifact_version"] == "1.2.0"
    decision_lineage = rationale.attributes.get("decision_lineage")
    if decision_lineage:
        lineage = json.loads(decision_lineage)
        assert isinstance(lineage, list)
        assert lineage

    dispatch_latency_ms = rationale.attributes.get("dispatch_latency_ms")
    if dispatch_latency_ms not in {None, ""}:
        assert int(dispatch_latency_ms) >= 0
    assert rationale.timeline_ref == f"qfs://jobs/{job_id}/timeline.json"
    assert rationale.logs_ref == f"qfs://jobs/{job_id}/logs/dispatch.log"
    