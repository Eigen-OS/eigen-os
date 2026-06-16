from __future__ import annotations

from datetime import datetime, timezone

import pytest
from google.protobuf.timestamp_pb2 import Timestamp

from eigen.api.v1 import knowledge_base_service_pb2 as kb_pb  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402

from neuro_symbolic_service.knowledge_base_versioned import KnowledgeBaseService  # noqa: E402


def _ts(value: str) -> Timestamp:
    ts = Timestamp()
    ts.FromDatetime(datetime.fromisoformat(value).replace(tzinfo=timezone.utc))
    return ts


def _envelope() -> kb_pb.ApiContractEnvelope:
    return kb_pb.ApiContractEnvelope(
        contract_version="1.0.0",
        request=types_pb.ApiRequestEnvelope(
            contract_version="1.0.0",
            request_id="kb-request-1",
            tenant_id="tenant-a",
            project_id="project-a",
            client_version="cli-1.0.0",
            traceparent="00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
        ),
    )


def _record(record_id: str, *, created_at: str, trace_id: str, user_id: str, note: str = "stable") -> kb_pb.KnowledgeRecord:
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
            "note": note,
        },
    )


def test_append_only_revision_history_and_deduplication() -> None:
    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)
    envelope = _envelope()

    first = service._upsert_record(  # noqa: SLF001 - exercise storage semantics directly.
        record=_record("kb-1", created_at="2026-06-11T10:00:00+00:00", trace_id="trace-a", user_id="alice"),
        envelope={"tenant_id": "tenant-a", "project_id": "project-a"},
        allow_overwrite=False,
        anonymize_attributes=True,
        source="rpc",
        replay_bundle_ref="kb://replay/kb-1",
        context=None,
    )
    assert first["created"] is True

    replay = service._upsert_record(  # noqa: SLF001 - exercise storage semantics directly.
        record=_record("kb-1", created_at="2026-06-11T10:00:00+00:00", trace_id="trace-a", user_id="alice"),
        envelope={"tenant_id": "tenant-a", "project_id": "project-a"},
        allow_overwrite=False,
        anonymize_attributes=True,
        source="rpc",
        replay_bundle_ref="kb://replay/kb-1",
        context=None,
    )
    assert replay["created"] is False

    snapshot = service.describe_record_history("kb-1")
    assert snapshot["revision_count"] == 1
    assert snapshot["history"][0]["revision_kind"] == "create"
    assert snapshot["history"][0]["ingest_kind"] == "create"
    assert snapshot["last_ingest_kind"] == "idempotent_replay"

    record_view = service._clone_record(service._records["kb-1"].record)  # noqa: SLF001
    attrs = dict(record_view.attributes)
    assert attrs["kb_revision_count"] == "1"
    assert attrs["kb_revision_state"] == "active"
    assert attrs["kb_active_version_label"] == "v00000001"
    assert attrs["kb_last_ingest_kind"] == "idempotent_replay"
    assert attrs["kb_revision_history_ref"] == "kb://records/kb-1/revisions"
    assert attrs["request_hash"].startswith("sha256:")
    assert attrs["replay_bundle_ref"] == "kb://replay/kb-1"
    assert attrs["user_id"].startswith("anon:")
    assert attrs["project_id"].startswith("anon:")
    assert attrs["client_ip"].startswith("anon:")

    with pytest.raises(ValueError):
        service._upsert_record(  # noqa: SLF001 - exercise storage semantics directly.
            record=_record("kb-1", created_at="2026-06-11T10:00:00+00:00", trace_id="trace-a", user_id="alice", note="changed"),
            envelope={"tenant_id": "tenant-a", "project_id": "project-a"},
            allow_overwrite=False,
            anonymize_attributes=True,
            source="rpc",
            replay_bundle_ref="kb://replay/kb-1",
            context=None,
        )

    overwrite = service._upsert_record(  # noqa: SLF001 - exercise storage semantics directly.
        record=_record("kb-1", created_at="2026-06-11T10:00:00+00:00", trace_id="trace-a", user_id="alice", note="changed"),
        envelope={"tenant_id": "tenant-a", "project_id": "project-a"},
        allow_overwrite=True,
        anonymize_attributes=True,
        source="rpc",
        replay_bundle_ref="kb://replay/kb-1",
        context=None,
    )
    assert overwrite["created"] is False

    snapshot = service.describe_record_history("kb-1")
    assert snapshot["revision_count"] == 2
    assert snapshot["history"][-1]["revision_kind"] == "new_revision"
    assert snapshot["history"][-1]["ingest_kind"] == "overwrite_authorized"
    assert snapshot["history"][-1]["active"] is True
    assert snapshot["history"][0]["active"] is False
    assert snapshot["last_ingest_kind"] == "overwrite_authorized"

    record_view = service._clone_record(service._records["kb-1"].record)  # noqa: SLF001
    attrs = dict(record_view.attributes)
    assert attrs["kb_revision_count"] == "2"
    assert attrs["kb_revision_kind"] == "new_revision"
    assert attrs["kb_last_ingest_kind"] == "overwrite_authorized"
    assert attrs["note"] == "changed"

    replay_after_overwrite = service._upsert_record(  # noqa: SLF001 - exercise storage semantics directly.
        record=_record("kb-1", created_at="2026-06-11T10:00:00+00:00", trace_id="trace-a", user_id="alice", note="changed"),
        envelope={"tenant_id": "tenant-a", "project_id": "project-a"},
        allow_overwrite=False,
        anonymize_attributes=True,
        source="rpc",
        replay_bundle_ref="kb://replay/kb-1",
        context=None,
    )
    assert replay_after_overwrite["created"] is False
    snapshot = service.describe_record_history("kb-1")
    assert snapshot["revision_count"] == 2
    assert snapshot["last_ingest_kind"] == "idempotent_replay"
