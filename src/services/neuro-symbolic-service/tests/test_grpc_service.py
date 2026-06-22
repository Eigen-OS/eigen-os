from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

import grpc
import pytest

from eigen.internal.v1 import neuro_symbolic_service_pb2 as nsc_pb
from eigen.internal.v1 import neuro_symbolic_service_pb2_grpc as nsc_pb_grpc
from neuro_symbolic_service.grpc_impl import _redact_feature_vector
from neuro_symbolic_service.observability import render_metrics_text


def _request(payload: dict[str, object], *, request_id: str = "req-1", tenant_id: str = "tenant-a", project_id: str = "project-a", feature_schema_version: str = "features.v1", policy_snapshot_version: str = "1.0.0", seed: int = 7, model_hint: str = "compile-plan") -> nsc_pb.ScoreCompilationPlanRequest:
    feature_vector = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    feature_digest = hashlib.sha256(_redact_feature_vector(feature_vector).feature_vector).hexdigest()
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


def _registry_signature(
    *,
    model_version: str,
    artifact_sha256: str,
    policy_snapshot_version: str,
    service_identity: str,
    tenant_id: str,
    project_id: str,
    artifact_path: str,
    signing_key: str,
) -> str:
    payload = json.dumps(
        {
            "artifact_path": artifact_path,
            "artifact_sha256": artifact_sha256,
            "model_version": model_version,
            "policy_snapshot_version": policy_snapshot_version,
            "project_id": project_id,
            "service_identity": service_identity,
            "tenant_id": tenant_id,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hmac.new(signing_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _write_signed_registry(
    tmp_path: Path,
    *,
    active_model_version: str,
    policy_snapshot_version: str = "1.0.0",
    service_identity: str = "neuro-symbolic-service",
    tenant_id: str = "tenant-a",
    project_id: str = "project-a",
    signing_key: str = "model-signing-key",
    artifact_bytes: bytes = b"neuro-dpda-model",
    second_model_bytes: bytes = b"neuro-dpda-model-v1",
    second_model_version: str = "dpda-model-v1",
    include_second_model: bool = True,
    bad_signature: bool = False,
    missing_artifact: bool = False,
) -> tuple[Path, Path]:
    artifact_path = tmp_path / f"{active_model_version}.bin"
    artifact_path.write_bytes(artifact_bytes)
    artifact_digest = hashlib.sha256(artifact_bytes).hexdigest()

    models: list[dict[str, object]] = []
    active_entry = {
        "model_version": active_model_version,
        "artifact_path": artifact_path.name,
        "artifact_sha256": artifact_digest,
        "signature_key_id": "internal-neuro-dpda-key",
        "service_identity": service_identity,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "policy_snapshot_version": policy_snapshot_version,
        "active": True,
    }
    active_entry["signature"] = _registry_signature(
        model_version=active_model_version,
        artifact_sha256=artifact_digest,
        policy_snapshot_version=policy_snapshot_version,
        service_identity=service_identity,
        tenant_id=tenant_id,
        project_id=project_id,
        artifact_path=artifact_path.name,
        signing_key=signing_key,
    )
    if bad_signature:
        active_entry["signature"] = "0" * 64
    models.append(active_entry)

    if include_second_model:
        second_path = tmp_path / f"{second_model_version}.bin"
        second_path.write_bytes(second_model_bytes)
        second_digest = hashlib.sha256(second_model_bytes).hexdigest()
        second_entry = {
            "model_version": second_model_version,
            "artifact_path": second_path.name,
            "artifact_sha256": second_digest,
            "signature_key_id": "internal-neuro-dpda-key",
            "service_identity": service_identity,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "policy_snapshot_version": policy_snapshot_version,
            "active": False,
        }
        second_entry["signature"] = _registry_signature(
            model_version=second_model_version,
            artifact_sha256=second_digest,
            policy_snapshot_version=policy_snapshot_version,
            service_identity=service_identity,
            tenant_id=tenant_id,
            project_id=project_id,
            artifact_path=second_path.name,
            signing_key=signing_key,
        )
        models.append(second_entry)

    if missing_artifact:
        artifact_path.unlink()

    registry = {
        "registry_version": "1.0.0",
        "service_identity": service_identity,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "policy_snapshot_version": policy_snapshot_version,
        "active_model_version": active_model_version,
        "models": models,
    }
    registry_path = tmp_path / "model-registry.json"
    registry_path.write_text(json.dumps(registry, sort_keys=True, indent=2), encoding="utf-8")
    return registry_path, artifact_path


class _FakeContext:
    def __init__(self, metadata: list[tuple[str, str]]) -> None:
        self._metadata = tuple(metadata)

    def invocation_metadata(self):
        return self._metadata

    def abort(self, *_args, **_kwargs):  # pragma: no cover - only called on failing paths
        raise AssertionError("abort should not be reached in success-path tests")


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


def test_model_registry_loads_signed_artifact_and_scores_with_loaded_model(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    registry_path, artifact_path = _write_signed_registry(
        tmp_path,
        active_model_version="dpda-model-v2",
        signing_key="registry-secret-key",
    )
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("NEURO_SYMBOLIC_MODEL_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("NEURO_SYMBOLIC_MODEL_REGISTRY_SIGNING_KEY", "registry-secret-key")
    monkeypatch.setenv("NEURO_SYMBOLIC_MODEL_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setenv("NEURO_SYMBOLIC_SERVICE_IDENTITY", "neuro-symbolic-service")
    monkeypatch.setenv("NEURO_SYMBOLIC_INTERNAL_TOKEN", "dev-internal-token")
    monkeypatch.setenv("NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")
    monkeypatch.setenv("NEURO_SYMBOLIC_AUDIT_SINK_PATH", str(audit_path))

    from neuro_symbolic_service.grpc_impl import NeuroSymbolicService

    service = NeuroSymbolicService()
    assert service.model_registry_snapshot().verified is True
    assert service.model_registry_snapshot().active_model_version == "dpda-model-v2"
    assert service._model_version == "dpda-model-v2"

    response = service.ScoreCompilationPlan(_request({"kind": "plan", "priority": 3}), _FakeContext(_metadata()))
    assert response.model_version == "dpda-model-v2"
    assert response.policy_snapshot_version == "1.0.0"
    assert response.deterministic_compatible is True

    audit_lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(audit_lines) >= 2
    activation = json.loads(audit_lines[0])
    scoring = json.loads(audit_lines[-1])
    assert activation["audit_kind"] == "model_registry_activation"
    assert activation["model_version"] == "dpda-model-v2"
    assert activation["caller_identity"] == "neuro-symbolic-service"
    assert activation["tenant"] == "tenant-a"
    assert activation["policy_snapshot_version"] == "1.0.0"
    assert scoring["audit_kind"] == "model_scoring"
    assert scoring["model_version"] == "dpda-model-v2"
    assert scoring["tenant"] == "tenant-a"
    assert scoring["policy_snapshot_version"] == "1.0.0"


@pytest.mark.parametrize(
    ("mutator", "expected_reason"),
    [
        (lambda cfg: cfg.__setitem__("bad_signature", True), "signature verification failed"),
        (lambda cfg: cfg.__setitem__("missing_artifact", True), "artifact is missing"),
        (lambda cfg: cfg.__setitem__("policy_snapshot_version", ""), "policy snapshot version is required"),
    ],
)
def test_model_registry_fallback_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutator,
    expected_reason: str,
) -> None:
    cfg: dict[str, object] = {"active_model_version": "dpda-model-v2"}
    mutator(cfg)
    registry_path, _ = _write_signed_registry(
        tmp_path,
        active_model_version=cfg["active_model_version"],  # type: ignore[arg-type]
        policy_snapshot_version=cfg.get("policy_snapshot_version", "1.0.0"),  # type: ignore[arg-type]
        signing_key="registry-secret-key",
        bad_signature=bool(cfg.get("bad_signature", False)),
        missing_artifact=bool(cfg.get("missing_artifact", False)),
    )
    if cfg.get("policy_snapshot_version") == "":
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        payload["policy_snapshot_version"] = ""
        registry_path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")

    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("NEURO_SYMBOLIC_MODEL_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("NEURO_SYMBOLIC_MODEL_REGISTRY_SIGNING_KEY", "registry-secret-key")
    monkeypatch.setenv("NEURO_SYMBOLIC_MODEL_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setenv("NEURO_SYMBOLIC_SERVICE_IDENTITY", "neuro-symbolic-service")
    monkeypatch.setenv("NEURO_SYMBOLIC_INTERNAL_TOKEN", "dev-internal-token")
    monkeypatch.setenv("NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")
    monkeypatch.setenv("NEURO_SYMBOLIC_AUDIT_SINK_PATH", str(audit_path))

    from neuro_symbolic_service.grpc_impl import NeuroSymbolicService

    service = NeuroSymbolicService()
    snapshot = service.model_registry_snapshot()
    assert snapshot.verified is False
    assert snapshot.active_model_version == "dpda-model-v1"
    assert service._model_version == "dpda-model-v1"
    assert expected_reason in snapshot.activation_reason

    audit_lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert audit_lines
    activation = json.loads(audit_lines[-1])
    assert activation["audit_kind"] == "model_registry_activation"
    assert activation["model_version"] == "dpda-model-v1"
    assert activation["activation_state"] == "baseline_fallback"
    assert expected_reason in activation["reason"]


def test_model_registry_rollback_is_auditable_and_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    registry_path, _ = _write_signed_registry(
        tmp_path,
        active_model_version="dpda-model-v2",
        signing_key="registry-secret-key",
    )
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("NEURO_SYMBOLIC_MODEL_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("NEURO_SYMBOLIC_MODEL_REGISTRY_SIGNING_KEY", "registry-secret-key")
    monkeypatch.setenv("NEURO_SYMBOLIC_MODEL_ARTIFACT_ROOT", str(tmp_path))
    monkeypatch.setenv("NEURO_SYMBOLIC_SERVICE_IDENTITY", "neuro-symbolic-service")
    monkeypatch.setenv("NEURO_SYMBOLIC_INTERNAL_TOKEN", "dev-internal-token")
    monkeypatch.setenv("NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")
    monkeypatch.setenv("NEURO_SYMBOLIC_AUDIT_SINK_PATH", str(audit_path))

    from neuro_symbolic_service.grpc_impl import NeuroSymbolicService

    service = NeuroSymbolicService()
    assert service._model_version == "dpda-model-v2"
    assert service.rollback_model_version("dpda-model-v1") is True
    assert service._model_version == "dpda-model-v1"
    assert service.rollback_model_version("dpda-model-v9") is False
    assert service._model_version == "dpda-model-v1"

    audit_lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    kinds = [json.loads(line)["audit_kind"] for line in audit_lines]
    assert "model_registry_activation" in kinds
    assert "model_registry_rollback" in kinds
    assert any(json.loads(line).get("reason", "") for line in audit_lines)
