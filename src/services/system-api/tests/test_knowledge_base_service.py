from __future__ import annotations

import json
from datetime import datetime, timezone

import grpc
import pytest
from google.protobuf.timestamp_pb2 import Timestamp

from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import knowledge_base_service_pb2 as kb_pb  # noqa: E402
from eigen.api.v1 import knowledge_base_service_pb2_grpc as kb_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402

from system_api.knowledge_base import KnowledgeBaseService, KnowledgeBaseUnavailable  # noqa: E402


class _MetadataContext:
    def __init__(self, metadata: tuple[tuple[str, str], ...]) -> None:
        self._metadata = metadata

    def invocation_metadata(self):
        return self._metadata


def _ts(value: str) -> Timestamp:
    ts = Timestamp()
    ts.FromDatetime(datetime.fromisoformat(value).replace(tzinfo=timezone.utc))
    return ts


def _envelope(*, request_id: str = "kb-request-1") -> kb_pb.ApiContractEnvelope:
    return kb_pb.ApiContractEnvelope(
        contract_version="1.0.0",
        request=types_pb.ApiRequestEnvelope(
            contract_version="1.0.0",
            request_id=request_id,
            tenant_id="tenant-a",
            project_id="project-a",
            client_version="cli-1.0.0",
            traceparent="00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
        ),
    )


def _record(record_id: str, *, created_at: str, trace_id: str, user_id: str) -> kb_pb.KnowledgeRecord:
    return kb_pb.KnowledgeRecord(
        record_id=record_id,
        job_id=f"job-{record_id}",
        circuit_id=f"circuit-{record_id}",
        artifact_ref=f"qfs://artifacts/{record_id}",
        dataset_ref="dataset-v1",
        backend_profile="backend-alpha",
        optimizer_version="opt-1.0",
        qubit_count=12,
        entanglement_score=0.42,
        noise_profile_id="noise-1",
        backend_class="simulator",
        created_at=_ts(created_at),
        provenance=kb_pb.RecordProvenance(
            compiler_ref="compiler://v1",
            optimizer_ref="optimizer://v1",
            runtime_ref="runtime://v1",
            checkpoint_ref="checkpoint://v1",
        ),
        lineage=kb_pb.ModelLineage(
            model_version="m1",
            training_set_hash="train-hash",
            evaluation_bundle_hash="eval-hash",
            promotion_policy_version="policy-v1",
            promotion_outcome="PROMOTED",
        ),
        attributes={
            "trace_id": trace_id,
            "request_id": f"req-{record_id}",
            "user_id": user_id,
            "project_id": "project-a",
            "client_ip": "10.0.0.7",
            "note": "stable",
        },
    )


def _okb_benchmark_payload(
    record_id: str,
    *,
    tenant_id: str,
    project_id: str,
    trace_id: str,
    backend_profile: str = "backend-alpha",
    optimizer_version: str = "opt-1.0",
    capability_tags: list[str] | None = None,
    capabilities: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "record_id": record_id,
        "run_id": f"run-{record_id}",
        "job_id": f"job-{record_id}",
        "trace_id": trace_id,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "request_hash": f"sha256:{record_id}",
        "backend_profile": backend_profile,
        "optimizer_version": optimizer_version,
        "circuit_id": "circuit-shared",
        "artifact_ref": "qfs://artifacts/shared-reuse",
        "dataset_ref": "dataset-shared",
        "qubit_count": 12,
        "entanglement_score": 0.44,
        "noise_profile_id": "noise-shared",
        "backend_class": "simulator",
        **({"capability_tags": capability_tags} if capability_tags is not None else {}),
        **({"capabilities": capabilities} if capabilities is not None else {}),
        "provenance": {
            "compiler_ref": "compiler://shared",
            "optimizer_ref": "optimizer://shared",
            "runtime_ref": "runtime://shared",
            "checkpoint_ref": "checkpoint://shared",
        },
        "lineage": {
            "model_version": "m1",
            "training_set_hash": "train-hash",
            "evaluation_bundle_hash": "eval-hash",
            "promotion_policy_version": "policy-v1",
            "promotion_outcome": "PROMOTED",
        },
    }


def _kb_security_metadata() -> tuple[tuple[str, str], ...]:
    return (
        ("authorization", "Bearer kb-token"),
        ("x-eigen-tenant", "tenant-a"),
        ("x-eigen-roles", "readonly"),
        ("x-eigen-sub", "kb-subject"),
        ("x-eigen-service", "system-api"),
        ("x-eigen-service-role", "public-ingress"),
        ("x-eigen-sandbox-profile", "default"),
    )


def _configure_kb_security(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYSTEM_API_AUTH_MODE", "static_token")
    monkeypatch.setenv("SYSTEM_API_AUTH_TOKEN", "kb-token")
    monkeypatch.setenv("SYSTEM_API_AUTH_SUBJECT", "kb-subject")
    monkeypatch.setenv("SYSTEM_API_AUTH_ROLES", "readonly")
    monkeypatch.setenv("SYSTEM_API_AUTH_TENANT", "tenant-a")
    monkeypatch.setenv(
        "SYSTEM_API_POLICY_SNAPSHOT_JSON",
        json.dumps(
            {
                "version": "1.0.0",
                "issuer": "eigen-auth",
                "audience": "eigen-api",
                "role_permissions": {
                    "readonly": ["kb:read", "kb:write", "devices:list", "jobs:read"],
                },
                "service_permissions": {
                    "system-api": ["public-ingress"],
                },
                "sandbox_profiles": ["default"],
            },
            sort_keys=True,
        ),
    )
    monkeypatch.setenv("SYSTEM_API_SERVICE_IDENTITY", "system-api")
    monkeypatch.setenv("SYSTEM_API_SERVICE_ROLE", "public-ingress")
    monkeypatch.setenv("SYSTEM_API_SANDBOX_PROFILE", "default")


def test_upsert_query_replay_and_provenance_are_deterministic(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = kb_pb_grpc.KnowledgeBaseServiceStub(channel)
    envelope = _envelope()

    first = stub.UpsertRecord(kb_pb.UpsertRecordRequest(envelope=envelope, record=_record("kb-1", created_at="2026-06-11T10:00:00+00:00", trace_id="trace-a", user_id="alice")))
    second = stub.UpsertRecord(kb_pb.UpsertRecordRequest(envelope=envelope, record=_record("kb-2", created_at="2026-06-11T10:05:00+00:00", trace_id="trace-a", user_id="bob")))
    replay = stub.UpsertRecord(kb_pb.UpsertRecordRequest(envelope=envelope, record=_record("kb-1", created_at="2026-06-11T10:00:00+00:00", trace_id="trace-a", user_id="alice")))

    assert first.created is True
    assert second.created is True
    assert replay.created is False

    page_one = stub.QueryRecords(
        kb_pb.QueryRecordsRequest(
            envelope=envelope,
            filter=kb_pb.QueryFilter(trace_id="trace-a"),
            page_size=1,
        )
    )
    assert [item.record_id for item in page_one.records] == ["kb-1"]
    assert page_one.next_page_token

    page_two = stub.QueryRecords(
        kb_pb.QueryRecordsRequest(
            envelope=envelope,
            filter=kb_pb.QueryFilter(trace_id="trace-a"),
            page_size=1,
            page_token=page_one.next_page_token,
        )
    )
    assert [item.record_id for item in page_two.records] == ["kb-2"]

    page_two_replay = stub.QueryRecords(
        kb_pb.QueryRecordsRequest(
            envelope=envelope,
            filter=kb_pb.QueryFilter(trace_id="trace-a"),
            page_size=1,
            page_token=page_one.next_page_token,
        )
    )
    assert [item.record_id for item in page_two_replay.records] == ["kb-2"]

    fetched = stub.GetRecord(kb_pb.GetRecordRequest(envelope=envelope, record_id="kb-1")).record
    attrs = dict(fetched.attributes)
    assert fetched.provenance.compiler_ref == "compiler://v1"
    assert fetched.lineage.model_version == "m1"
    assert attrs["trace_id"] == "trace-a"
    assert attrs["request_hash"].startswith("sha256:")
    assert attrs["replay_bundle_ref"] == "kb://replay/kb-1"
    assert attrs["user_id"].startswith("anon:")
    assert attrs["project_id"].startswith("anon:")
    assert attrs["client_ip"].startswith("anon:")


def test_decision_log_lineage_validation_and_ordering(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = kb_pb_grpc.KnowledgeBaseServiceStub(channel)
    envelope = _envelope(request_id="kb-decision-1")

    first = stub.AppendDecisionLog(
        kb_pb.AppendDecisionLogRequest(
            envelope=envelope,
            decision_log=kb_pb.DecisionLog(
                decision_id="decision-a",
                trace_id="trace-b",
                model_version="m1",
                component="runtime",
                policy_branch="baseline",
                selected_action="backend-alpha",
                fallback_used=False,
                feature_snapshot={"queue_depth": "2"},
                decided_at=_ts("2026-06-11T10:00:00+00:00"),
            ),
        )
    )
    second = stub.AppendDecisionLog(
        kb_pb.AppendDecisionLogRequest(
            envelope=envelope,
            decision_log=kb_pb.DecisionLog(
                decision_id="decision-b",
                trace_id="trace-b",
                model_version="m1",
                component="runtime",
                policy_branch="fallback",
                selected_action="backend-beta",
                fallback_used=True,
                feature_snapshot={"queue_depth": "5"},
                decided_at=_ts("2026-06-11T10:01:00+00:00"),
            ),
        )
    )

    assert first.decision_id == "decision-a"
    assert second.decision_id == "decision-b"

    query = stub.QueryDecisionLogs(
        kb_pb.QueryDecisionLogsRequest(
            envelope=envelope,
            trace_id="trace-b",
            model_version="m1",
            page_size=10,
        )
    )
    assert [item.decision_id for item in query.decision_logs] == ["decision-a", "decision-b"]
    assert [item.selected_action for item in query.decision_logs] == ["backend-alpha", "backend-beta"]


def test_runtime_decision_ingest_persists_explainability_envelope(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("SYSTEM_API_AUDIT_SINK_PATH", str(audit_path))
    _configure_kb_security(monkeypatch)
    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)

    decision_id = service.ingest_runtime_decision(
        {
            "record_id": "decision-runtime-1",
            "decision_id": "decision-runtime-1",
            "trace_id": "trace-runtime",
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "caller_identity": "eigen-compiler",
            "security_context": {
                "subject": "eigen-compiler",
                "tenant": "tenant-a",
                "project_id": "project-a",
                "policy_version": "policy-2026-06-15",
                "auth_mode": "static_token",
                "service_identity": "system-api",
                "service_role": "public-ingress",
                "sandbox_profile": "default",
            },
            "model_version": "m1",
            "component": "runtime",
            "policy_branch": "baseline",
            "selected_action": "backend-alpha",
            "fallback_used": False,
            "feature_snapshot": {"queue_depth": "2"},
            "feature_set": {"schema_version": "features.v1", "signature": "sig-1"},
            "confidence": 0.8125,
            "retrieval_sources": [
                "nsc://feature-set/tenant-a/project-a/request-1/feature-digest",
                "nsc://policy-snapshot/policy-2026-06-15",
                "nsc://model/dpda-model-unit-test",
            ],
            "replay_digest": "sha256:replay-1",
            "policy_snapshot_version": "policy-2026-06-15",
            "decided_at": _ts("2026-06-11T10:05:00+00:00"),
        }
    )

    assert decision_id == "decision-runtime-1"
    stored = service._decision_logs[-1]
    snapshot = dict(stored.decision_log.feature_snapshot)
    envelope = json.loads(snapshot["explainability_envelope"])
    assert envelope["model_version"] == "m1"
    assert envelope["feature_set"]["schema_version"] == "features.v1"
    assert envelope["confidence"] == 0.8125
    assert envelope["retrieval_reference_count"] == 3
    assert envelope["retrieval_references"][1] == "nsc://policy-snapshot/policy-2026-06-15"
    assert snapshot["caller_identity"] == "eigen-compiler"
    assert snapshot["tenant_id"] == "tenant-a"
    assert snapshot["project_id"] == "project-a"
    assert snapshot["policy_snapshot_version"] == "policy-2026-06-15"
    assert snapshot["final_decision"] == "backend-alpha"
    assert json.loads(snapshot["retrieval_sources"]) == [
        "nsc://feature-set/tenant-a/project-a/request-1/feature-digest",
        "nsc://policy-snapshot/policy-2026-06-15",
        "nsc://model/dpda-model-unit-test",
    ]
    
    evidence = service._learning_evidence[-1]
    assert evidence["payload"]["explainability_envelope"]["model_version"] == "m1"
    assert evidence["payload"]["explainability_envelope"]["confidence"] == 0.8125
    assert evidence["metadata"]["explainability_envelope_json"]

    audit_lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(audit_lines) == 1
    audit = json.loads(audit_lines[0])
    assert audit["audit_kind"] == "immutable_decision"
    assert audit["operation"] == "ingest_runtime_decision"
    assert audit["caller_identity"] == "eigen-compiler"
    assert audit["tenant"] == "tenant-a"
    assert audit["policy_snapshot_version"] == "policy-2026-06-15"
    assert audit["model_version"] == "m1"
    assert audit["retrieval_sources"][-1] == "nsc://model/dpda-model-unit-test"
    assert audit["final_decision"] == "backend-alpha"
    assert audit["immutable"] is True


def test_kb_records_and_decision_logs_are_project_scoped(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = kb_pb_grpc.KnowledgeBaseServiceStub(channel)

    project_a = _envelope(request_id="kb-project-a")
    project_b = kb_pb.ApiContractEnvelope(
        contract_version="1.0.0",
        request=types_pb.ApiRequestEnvelope(
            contract_version="1.0.0",
            request_id="kb-project-b",
            tenant_id="tenant-a",
            project_id="project-b",
            client_version="cli-1.0.0",
            traceparent="00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
        ),
    )

    stub.UpsertRecord(
        kb_pb.UpsertRecordRequest(
            envelope=project_a,
            record=_record("kb-project-a-record", created_at="2026-06-11T11:00:00+00:00", trace_id="trace-scope", user_id="alice"),
        )
    )
    stub.AppendDecisionLog(
        kb_pb.AppendDecisionLogRequest(
            envelope=project_a,
            decision_log=kb_pb.DecisionLog(
                decision_id="decision-project-a",
                trace_id="trace-scope",
                model_version="m1",
                component="runtime",
                policy_branch="baseline",
                selected_action="backend-alpha",
                fallback_used=False,
                feature_snapshot={"queue_depth": "2"},
                decided_at=_ts("2026-06-11T11:01:00+00:00"),
            ),
        )
    )

    project_b_records = stub.QueryRecords(
        kb_pb.QueryRecordsRequest(
            envelope=project_b,
            filter=kb_pb.QueryFilter(trace_id="trace-scope"),
            page_size=10,
        )
    )
    project_b_decisions = stub.QueryDecisionLogs(
        kb_pb.QueryDecisionLogsRequest(
            envelope=project_b,
            trace_id="trace-scope",
            model_version="m1",
            page_size=10,
        )
    )

    assert project_b_records.records == []
    assert project_b_decisions.decision_logs == []


def test_kb_fallback_behavior_raises_when_storage_disabled() -> None:
    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb, storage_mode="disabled")
    with pytest.raises(KnowledgeBaseUnavailable):
        service.ingest_runtime_decision(
            {
                "record_id": "decision-x",
                "decision_id": "decision-x",
                "trace_id": "trace-x",
                "model_version": "m1",
                "component": "runtime",
                "policy_branch": "baseline",
                "selected_action": "backend-alpha",
                "feature_snapshot": {"queue_depth": "1"},
            }
        )

    with pytest.raises(KnowledgeBaseUnavailable):
        service.ingest_benchmark_run(
            {
                "record_id": "benchmark-x",
                "run_id": "run-x",
                "job_id": "job-x",
                "trace_id": "trace-x",
                "tenant_id": "tenant-a",
                "project_id": "project-a",
                "request_hash": "sha256:abc",
            }
        )


def test_okb_query_backend_is_deterministic_and_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_kb_security(monkeypatch)
    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)
    context = _MetadataContext(_kb_security_metadata())

    for i in range(10):
        service.ingest_benchmark_run(
            _okb_benchmark_payload(
                f"candidate-{i:02d}",
                tenant_id="tenant-a",
                project_id="project-a",
                trace_id="trace-okb",
            )
        )

    service.ingest_benchmark_run(
        _okb_benchmark_payload(
            "foreign-candidate",
            tenant_id="tenant-b",
            project_id="project-b",
            trace_id="trace-foreign",
            backend_profile="backend-foreign",
            optimizer_version="opt-foreign",
        )
    )

    query = {
        "tenant_id": "tenant-a",
        "project_id": "project-a",
        "job_id": "job-1",
        "semantic_hash": "sha256:semantic-1",
        "aqo_hash": "sha256:aqo-1",
        "backend_profile_id": "backend-alpha",
        "topology_snapshot_digest": "topology-1",
        "policy_envelope_digest": "policy-1",
        "kb_schema_version": "1.0.0",
        "compiler_version": "compiler-1.0",
        "optimizer_version": "opt-1.0",
        "seed": 7,
        "deterministic": True,
        "query_mode": "structural",
        "candidate_budget": 99,
    }

    first = service.query_optimization_candidates(query, context=context)
    second = service.query_optimization_candidates(query, context=context)

    assert first == second
    assert first["tenant_id"] == "tenant-a"
    assert first["project_id"] == "project-a"
    assert first["query_mode"] == "structural"
    assert first["candidate_budget"] == 8
    assert len(first["candidates"]) == 8
    assert first["selected_candidate_id"] == first["candidates"][0]["candidate_id"]
    assert [item["candidate_id"] for item in first["candidates"]] == [
        "okb-record-candidate-00",
        "okb-record-candidate-01",
        "okb-record-candidate-02",
        "okb-record-candidate-03",
        "okb-record-candidate-04",
        "okb-record-candidate-05",
        "okb-record-candidate-06",
        "okb-record-candidate-07",
    ]
    assert all(item["candidate_source"] == "record" for item in first["candidates"])
    assert all(item["score_breakdown"]["rank_source"] == "structural" for item in first["candidates"])
    assert all(item["score_breakdown"]["structural_score"] == 1.0 for item in first["candidates"])
    assert len({item["score_breakdown"]["vector_score"] for item in first["candidates"]}) == 1
    assert all("foreign-candidate" not in item["candidate_id"] for item in first["candidates"])
    assert all(0.0 <= item["confidence"] <= 1.0 for item in first["candidates"])
    assert all(0.0 <= item["score_total"] <= 1.0 for item in first["candidates"])
    assert first["candidates"][0]["deterministic_digest"].startswith("sha256:")
    assert first["okb_selection_digest"].startswith("sha256:")
    assert first["explanation_ref"] == "qfs://jobs/job-1/kb/explain.json"
    assert first["index_status"]["overall_status"] == "ready"
    assert first["index_status"]["indices"]["structural"]["status"] == "ready"
    assert first["index_status"]["indices"]["vector"]["status"] == "ready"

    vector = service.query_optimization_candidates({**query, "query_mode": "vector", "candidate_budget": 2}, context=context)
    assert vector["query_mode"] == "vector"
    assert vector["candidate_budget"] == 2
    assert vector["selected_candidate_id"] == vector["candidates"][0]["candidate_id"]
    assert vector["candidates"][0]["score_breakdown"]["rank_source"] == "vector"
    assert len(vector["candidates"]) == 2

    hybrid = service.query_optimization_candidates({**query, "query_mode": "hybrid", "candidate_budget": 3}, context=context)
    assert hybrid["query_mode"] == "hybrid"
    assert hybrid["candidate_budget"] == 3
    assert hybrid["selected_candidate_id"] == hybrid["candidates"][0]["candidate_id"]
    assert hybrid["candidates"][0]["score_breakdown"]["rank_source"] == "hybrid"
    assert len(hybrid["candidates"]) == 3
    

def test_okb_query_backend_is_capability_scoped_and_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_kb_security(monkeypatch)
    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)
    context = _MetadataContext(_kb_security_metadata())

    service.ingest_benchmark_run(
        _okb_benchmark_payload(
            "capability-candidate-01",
            tenant_id="tenant-a",
            project_id="project-a",
            trace_id="trace-capability",
            capability_tags=["qpu", "latency"],
        )
    )
    service.ingest_benchmark_run(
        _okb_benchmark_payload(
            "capability-candidate-02",
            tenant_id="tenant-a",
            project_id="project-a",
            trace_id="trace-capability",
            capability_tags=["simulator", "latency"],
        )
    )

    matched = service.query_optimization_candidates(
        {
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "job_id": "job-capability",
            "semantic_hash": "sha256:semantic-capability",
            "aqo_hash": "sha256:aqo-capability",
            "backend_profile_id": "backend-alpha",
            "capability_tags": ["qpu", "latency"],
            "topology_snapshot_digest": "topology-capability",
            "policy_envelope_digest": "policy-capability",
            "kb_schema_version": "1.0.0",
            "compiler_version": "compiler-1.0",
            "optimizer_version": "opt-1.0",
            "seed": 11,
            "deterministic": True,
            "query_mode": "structural",
            "candidate_budget": 8,
        },
        context=context,
    )
    mismatch = service.query_optimization_candidates(
        {
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "job_id": "job-capability-mismatch",
            "semantic_hash": "sha256:semantic-capability",
            "aqo_hash": "sha256:aqo-capability",
            "backend_profile_id": "backend-alpha",
            "capability_tags": ["gpu", "latency"],
            "topology_snapshot_digest": "topology-capability",
            "policy_envelope_digest": "policy-capability",
            "kb_schema_version": "1.0.0",
            "compiler_version": "compiler-1.0",
            "optimizer_version": "opt-1.0",
            "seed": 11,
            "deterministic": True,
            "query_mode": "structural",
            "candidate_budget": 8,
        },
        context=context,
    )

    assert [item["candidate_id"] for item in matched["candidates"]] == ["okb-record-capability-candidate-01"]
    assert matched["selected_candidate_id"] == "okb-record-capability-candidate-01"
    assert mismatch["candidates"] == []
    assert mismatch["selected_candidate_id"] == ""


def test_learning_evidence_query_is_capability_scoped_and_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_kb_security(monkeypatch)
    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)
    context = _MetadataContext(_kb_security_metadata())

    service.ingest_learning_evidence(
        {
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "evidence_kind": "learning",
            "source": "manual",
            "model_version": "m1",
            "training_set_hash": "train-hash",
            "evaluation_bundle_hash": "eval-hash",
            "promotion_policy_version": "policy-v1",
            "capability_tags": ["qpu", "latency"],
            "metadata": {"note": "matched"},
            "gate_results": {"pass": True},
            "command": "ingest",
            "decision": "accepted",
        }
    )
    service.ingest_learning_evidence(
        {
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "evidence_kind": "learning",
            "source": "manual",
            "model_version": "m1",
            "training_set_hash": "train-hash",
            "evaluation_bundle_hash": "eval-hash",
            "promotion_policy_version": "policy-v1",
            "capability_tags": ["simulator", "latency"],
            "metadata": {"note": "foreign"},
            "gate_results": {"pass": True},
            "command": "ingest",
            "decision": "accepted",
        }
    )

    matched = service.query_learning_evidence(
        {
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "model_version": "m1",
            "capability_tags": ["qpu", "latency"],
            "page_size": 10,
        },
        context=context,
    )
    mismatch = service.query_learning_evidence(
        {
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "model_version": "m1",
            "capability_tags": ["gpu", "latency"],
            "page_size": 10,
        },
        context=context,
    )

    assert matched["total_count"] == 1
    assert [item["metadata"]["note"] for item in matched["evidence"]] == ["matched"]
    assert mismatch["total_count"] == 0
    assert mismatch["evidence"] == []


def test_okb_index_recovery_backfill_and_desync_signals() -> None:
    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)

    service.ingest_benchmark_run(
        _okb_benchmark_payload(
            "recover-record-1",
            tenant_id="tenant-a",
            project_id="project-a",
            trace_id="trace-recover",
        )
    )
    service.ingest_runtime_decision(
        {
            "decision_id": "recover-decision-1",
            "trace_id": "trace-recover",
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "caller_identity": "kb-subject",
            "security_context": {
                "subject": "kb-subject",
                "tenant": "tenant-a",
                "project_id": "project-a",
                "policy_version": "1.0.0",
                "auth_mode": "static_token",
                "service_identity": "system-api",
                "service_role": "public-ingress",
                "sandbox_profile": "default",
            },
            "model_version": "m1",
            "component": "runtime",
            "policy_branch": "baseline",
            "selected_action": "backend-alpha",
            "feature_snapshot": {"queue_depth": "2"},
            "retrieval_sources": ["nsc://policy-snapshot/1.0.0"],
            "policy_snapshot_version": "1.0.0",
        }
    )

    ready = service.describe_index_health(tenant_id="tenant-a", project_id="project-a")
    assert ready["overall_status"] == "ready"
    assert ready["desynced"] is False
    assert ready["indices"]["structural"]["status"] == "ready"
    assert ready["indices"]["vector"]["status"] == "ready"

    service._reset_okb_index_runtime_state()  # noqa: SLF001 - simulate a crash / cold restart.
    unavailable = service.describe_index_health(tenant_id="tenant-a", project_id="project-a")
    assert unavailable["overall_status"] == "unavailable"

    recovered = service.recover_indexes({"tenant_id": "tenant-a", "project_id": "project-a"})
    assert recovered["overall_status"] == "ready"
    assert recovered["scopes"][0]["source_count"] == 2
    assert service.describe_index_health(tenant_id="tenant-a", project_id="project-a")["overall_status"] == "ready"

    backfill_first = service.backfill_indexes({"tenant_id": "tenant-a", "project_id": "project-a"})
    backfill_second = service.backfill_indexes({"tenant_id": "tenant-a", "project_id": "project-a"})
    assert backfill_first["overall_status"] == "ready"
    assert backfill_first["scopes"][0]["source_count"] == backfill_second["scopes"][0]["source_count"] == 2

    scope_key = "tenant-a::project-a"
    service._okb_indexes["structural"].scope_entries[scope_key].pop()  # noqa: SLF001 - simulate index corruption.
    degraded = service.describe_index_health(tenant_id="tenant-a", project_id="project-a")
    assert degraded["overall_status"] == "degraded"
    assert degraded["desynced"] is True
    assert degraded["indices"]["structural"]["desynced"] is True

    rebuilt = service.rebuild_indexes({"tenant_id": "tenant-a", "project_id": "project-a"})
    assert rebuilt["overall_status"] == "ready"
    assert service.describe_index_health(tenant_id="tenant-a", project_id="project-a")["overall_status"] == "ready"
