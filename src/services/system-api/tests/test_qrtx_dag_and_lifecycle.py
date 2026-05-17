from __future__ import annotations

import grpc

from system_api.lifecycle import apply_signal
from system_api.proto_gen import ensure_generated
from system_api.scheduling import resolve_dag

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def test_dag_resolver_is_deterministic_for_valid_graph() -> None:
    res = resolve_dag(["c", "a", "b"], {"c": ["a", "b"], "b": ["a"]})
    assert res.ok is True
    assert res.reason_code == "DAG_RESOLVE_OK"
    assert res.order == ("a", "b", "c")


def test_dag_resolver_reason_codes_for_malformed_graph() -> None:
    cycle = resolve_dag(["a", "b"], {"a": ["b"], "b": ["a"]})
    assert cycle.ok is False
    assert cycle.reason_code == "DAG_CYCLE_DETECTED"

    unknown = resolve_dag(["a"], {"a": ["missing"]})
    assert unknown.ok is False
    assert unknown.reason_code == "DAG_UNKNOWN_NODE"


def test_lifecycle_cancel_idempotency_and_out_of_order_retry() -> None:
    accepted = apply_signal(current_stage="RUNNING", signal="cancel", already_requested=False)
    assert accepted.accepted is True
    assert accepted.reason_code == "LIFECYCLE_CANCEL_ACCEPTED"

    duplicate = apply_signal(current_stage="RUNNING", signal="cancel", already_requested=True)
    assert duplicate.accepted is False
    assert duplicate.reason_code == "LIFECYCLE_CANCEL_DUPLICATE"

    out_of_order = apply_signal(current_stage="QUEUED", signal="retry")
    assert out_of_order.accepted is False
    assert out_of_order.reason_code == "LIFECYCLE_RETRY_OUT_OF_ORDER"


def test_cancel_is_replay_safe_for_repeated_control_signal(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)
    submit = stub.SubmitJob(
        job_pb.SubmitJobRequest(
            name="cancel-idem",
            target="emu:real-hifi",
            metadata={"simulate_runtime_sec": "4"},
            eigen_lang=types_pb.EigenLangSource(source=b"fn main() {}\n", entrypoint="main"),
        )
    )
    first = stub.CancelJob(job_pb.CancelJobRequest(job_id=submit.job_id))
    second = stub.CancelJob(job_pb.CancelJobRequest(job_id=submit.job_id))

    assert first.accepted is True
    assert second.accepted is False
    