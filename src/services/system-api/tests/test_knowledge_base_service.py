from __future__ import annotations

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