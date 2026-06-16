from __future__ import annotations

import hashlib
import json

import grpc
import pytest

from eigen.internal.v1 import neuro_symbolic_service_pb2 as nsc_pb
from eigen.internal.v1 import neuro_symbolic_service_pb2_grpc as nsc_pb_grpc
from neuro_symbolic_service.observability import render_metrics_text


def _request(payload: dict[str, object], *, request_id: str = "req-1", tenant_id: str = "tenant-a", project_id: str = "project-a", feature_schema_version: str = "features.v1", policy_snapshot_version: str = "1.0.0", seed: int = 7, model_hint: str = "compile-plan") -> nsc_pb.ScoreCompilationPlanRequest:
    feature_vector = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    feature_digest = hashlib.sha256(feature_vector).hexdigest()
    return nsc_pb.ScoreCompilationPlanRequest(
        envelope=nsc_pb.NeuroSymbolicContractEnvelope(contract_version="1.0.0"),
        context=nsc_pb.NeuroSymbolicRequestContext(
            request_id=request_id,
            tenant_id=tenant_id,
            project_id=project_id,
            feature_schema_version=feature_schema_version,
            policy_snapshot_version=policy_snapshot_version,
            trace_id="0123456789abcdef0123456789abcdef",
            traceparent="00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
            subject_id="subject-1",
            workload_id="workload-1",
            authz_decision_id="authz-1",
        ),
        feature_vector=feature_vector,
        feature_digest_sha256=feature_digest,
        deterministic_seed=seed,
        model_hint=model_hint,
    )


def _metadata(*, caller: str = "eigen-kernel", tenant_id: str = "tenant-a", project_id: str = "project-a") -> list[tuple[str, str]]:
    return [
        ("authorization", "Bearer dev-internal-token"),
        ("x-eigen-service-id", caller),
        ("x-eigen-tenant-id", tenant_id),
        ("x-eigen-project-id", project_id),
    ]


def test_score_compilation_plan_is_internal_only(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        stub.ScoreCompilationPlan(_request({"kind": "plan"}))

    assert err.value.code() == grpc.StatusCode.UNAUTHENTICATED


def test_score_compilation_plan_returns_deterministic_advisory_metadata(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    request = _request({"kind": "plan", "priority": 3, "email": "alice@example.com"})
    first = stub.ScoreCompilationPlan(request, metadata=_metadata())
    second = stub.ScoreCompilationPlan(request, metadata=_metadata())

    assert first.contract_version == "1.0.0"
    assert first.request_id == "req-1"
    assert first.tenant_id == "tenant-a"
    assert first.project_id == "project-a"
    assert first.policy_snapshot_version == "1.0.0"
    assert first.deterministic_compatible is True
    assert first.replay_digest == second.replay_digest
    assert first.score == second.score
    assert first.confidence == second.confidence
    assert first.decision == second.decision
    assert first.explanation_ref == second.explanation_ref
    assert first.subject_id == "subject-1"
    assert first.workload_id == "workload-1"
    assert first.authz_decision_id == "authz-1"


def test_score_compilation_plan_fail_closed_on_scope_mismatch(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        stub.ScoreCompilationPlan(_request({"kind": "plan"}), metadata=_metadata(tenant_id="tenant-b"))

    assert err.value.code() == grpc.StatusCode.PERMISSION_DENIED


def test_metrics_and_healthz_smoke() -> None:
    metrics = render_metrics_text()
    assert 'eigen_observability_contract_info{version="1.0.0"} 1' in metrics
    assert 'eigen_neuro_requests_total' in metrics


def test_score_compilation_plan_fail_closed_on_policy_snapshot_mismatch(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        stub.ScoreCompilationPlan(_request({"kind": "plan"}, policy_snapshot_version="2.0.0"), metadata=_metadata())

    assert err.value.code() == grpc.StatusCode.FAILED_PRECONDITION
