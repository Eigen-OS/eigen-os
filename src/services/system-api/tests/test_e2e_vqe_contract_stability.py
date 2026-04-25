from __future__ import annotations

import json

import grpc

from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def _submit_vqe_job(stub: job_pb_grpc.JobServiceStub, *, max_iters: int = 6) -> str:
    req = job_pb.SubmitJobRequest(
        name="e2e-vqe-contract-stability",
        target="sim:local",
        metadata={
            "seed": "12345",
            "max_iters": str(max_iters),
            "trace_id": "trace-vqe-e2e-001",
        },
        eigen_lang=types_pb.EigenLangSource(
            source=b"""# VQE cycle program fixture\ndef main():\n    return \"vqe\"\n""",
            entrypoint="main",
        ),
    )
    resp = stub.SubmitJob(req)
    return resp.job_id


def test_e2e_vqe_contract_stability(grpc_addr: str):
    """E2E VQE flow: deterministic objective trend + contract artifacts."""

    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    job_id = _submit_vqe_job(stub, max_iters=6)

    stream = stub.StreamJobUpdates(job_pb.StreamJobUpdatesRequest(job_id=job_id))
    updates = [item.update for item in stream]

    assert len(updates) >= 5
    assert updates[-1].state == types_pb.JOB_STATE_DONE

    seqs = [int(u.event_seq) for u in updates]
    assert seqs == sorted(seqs)
    assert len(seqs) == len(set(seqs))

    iter_messages = [u.message for u in updates if "vqe_iteration" in u.message]
    assert len(iter_messages) >= 2
    assert all("trace_id=trace-vqe-e2e-001" in msg for msg in iter_messages)
    assert all("iteration=" in msg for msg in iter_messages)

    results = stub.GetJobResults(job_pb.GetJobResultsRequest(job_id=job_id))
    assert results.job_id == job_id
    assert results.state == types_pb.JOB_STATE_DONE

    # Validate objective trend from metadata for deterministic CI behavior.
    objective_history = json.loads(results.metadata["objective_history"])
    assert len(objective_history) == 6
    assert objective_history[-1] < objective_history[0]

    # Contract checks for QFS artifact pointers.
    assert results.metadata["qfs_compiled_aqo"].endswith("/compiled/circuit.aqo.json")
    assert results.metadata["qfs_results_parquet"].endswith("/results.parquet")
    assert results.metadata["qfs_metrics"].endswith("/results/metrics.json")
    assert "qfs_results_stream_prefix" in results.metadata
    