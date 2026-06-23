from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from google.protobuf.timestamp_pb2 import Timestamp

from eigen.api.v1 import knowledge_base_service_pb2 as kb_pb  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402

from neuro_symbolic_service.knowledge_base_versioned import KnowledgeBaseService  # noqa: E402
from neuro_symbolic_service.knowledge_base import KnowledgeBaseUnavailable  # noqa: E402
from neuro_symbolic_service.main import main as neuro_main  # noqa: E402
from neuro_symbolic_service.production_trace_training import ProductionTraceTrainingError, prepare_historical_compilation_training_manifest, prepare_training_dataset_manifest  # noqa: E402


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


import hashlib
import json
from pathlib import Path

from neuro_symbolic_service.main import main as neuro_main  # noqa: E402


def _json_digest(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _with_digest(payload: dict[str, object], digest_field: str) -> dict[str, object]:
    body = dict(payload)
    body[digest_field] = _json_digest(payload)
    return body


def _training_dataset_manifest() -> dict[str, object]:
    record_payload_1 = {
        "feature": "stable",
        "value": 7,
        "rewrite_outcome": "accepted",
    }
    record_payload_2 = {
        "feature": "stable",
        "value": 9,
        "tags": ["clean", "redacted"],
        "rewrite_outcome": "equivalent",
    }
    record_payload_3 = {
        "feature": "stable",
        "value": 11,
        "tags": ["clean", "redacted"],
        "rewrite_outcome": "rejected",
    }
    record_payload_4 = {
        "feature": "stable",
        "value": 13,
        "tags": ["clean", "redacted"],
        "rewrite_outcome": "unsafe",
    }

    record_provenance_1 = _with_digest(
        {
            "source_ref": "qfs://datasets/raw/sample-1.json",
            "captured_at": "2026-06-16T08:00:00+00:00",
            "requested_by": "neuro-symbolic-service",
        },
        "source_digest_sha256",
    )
    record_provenance_3 = _with_digest(
        {
            "source_ref": "qfs://datasets/raw/sample-3.json",
            "captured_at": "2026-06-16T08:02:00+00:00",
            "requested_by": "neuro-symbolic-service",
        },
        "source_digest_sha256",
    )
    record_provenance_4 = _with_digest(
        {
            "source_ref": "qfs://datasets/raw/sample-4.json",
            "captured_at": "2026-06-16T08:03:00+00:00",
            "requested_by": "neuro-symbolic-service",
        },
        "source_digest_sha256",
    )
    record_provenance_2 = _with_digest(
        {
            "source_ref": "qfs://datasets/raw/sample-2.json",
            "captured_at": "2026-06-16T08:01:00+00:00",
            "requested_by": "neuro-symbolic-service",
        },
        "source_digest_sha256",
    )
    record_redaction_1 = _with_digest(
        {
            "applied": True,
            "validated": True,
            "rules": ["secret", "pii"],
        },
        "redaction_digest_sha256",
    )
    record_redaction_2 = _with_digest(
        {
            "applied": True,
            "validated": True,
            "rules": ["secret", "pii"],
        },
        "redaction_digest_sha256",
    )
    record_redaction_3 = _with_digest(
        {
            "applied": True,
            "validated": True,
            "rules": ["secret", "pii"],
        },
        "redaction_digest_sha256",
    )
    record_redaction_4 = _with_digest(
        {
            "applied": True,
            "validated": True,
            "rules": ["secret", "pii"],
        },
        "redaction_digest_sha256",
    )

    records = [
        {
            "record_id": "sample-1",
            "schema_version": "training-record.v1",
            "payload": record_payload_1,
            "provenance": record_provenance_1,
            "redaction": record_redaction_1,
            "content_digest_sha256": _json_digest(record_payload_1),
        },
        {
            "record_id": "sample-2",
            "schema_version": "training-record.v1",
            "payload": record_payload_2,
            "provenance": record_provenance_2,
            "redaction": record_redaction_2,
            "content_digest_sha256": _json_digest(record_payload_2),
        },
        {
            "record_id": "sample-3",
            "schema_version": "training-record.v1",
            "payload": record_payload_3,
            "provenance": record_provenance_3,
            "redaction": record_redaction_3,
            "content_digest_sha256": _json_digest(record_payload_3),
        },
        {
            "record_id": "sample-4",
            "schema_version": "training-record.v1",
            "payload": record_payload_4,
            "provenance": record_provenance_4,
            "redaction": record_redaction_4,
            "content_digest_sha256": _json_digest(record_payload_4),
        },
    ]

    provenance = _with_digest(
        {
            "source_ref": "qfs://datasets/raw/batch-2026-06-16.json",
            "captured_at": "2026-06-16T08:00:00+00:00",
            "signed_by": "neuro-symbolic-service",
            "signature_algorithm": "HS256",
            "signature": "sig-batch-001",
        },
        "source_digest_sha256",
    )
    redaction = _with_digest(
        {
            "applied": True,
            "validated": True,
            "rules": ["secret", "pii"],
        },
        "redaction_digest_sha256",
    )

    manifest = {
        "schema_version": "neuro-symbolic.training-dataset.manifest.v1",
        "contract_version": "1.0.0",
        "dataset_id": "training-batch-2026-06-16",
        "dataset_version": "2026.06.16",
        "record_schema_version": "training-record.v1",
        "tenant_id": "tenant-a",
        "project_id": "project-a",
        "policy_snapshot_version": "1.0.0",
        "compiler_version": "compiler-1.0",
        "kb_version": "1.0.0",
        "ownership": {
            "service_identity": "neuro-symbolic-service",
            "requested_by": "neuro-symbolic-service",
            "service_role": "internal-ingest",
        },
        "provenance": provenance,
        "redaction": redaction,
        "records": records,
    }
    manifest["manifest_digest_sha256"] = _json_digest(manifest)
    return manifest


def _production_trace_training_bundle() -> dict[str, object]:
    trace_payload_1 = {
        "tenant": "tenant-a",
        "project": "project-a",
        "decision": "accepted",
        "features": {
            "compiler": "dpda",
            "label": "stable",
            "masked_email": "[REDACTED_EMAIL]",
            "masked_token": "[REDACTED]",
        },
        "notes": ["redacted", "tenant-scoped"],
    }
    trace_payload_2 = {
        "tenant": "tenant-a",
        "project": "project-a",
        "decision": "review",
        "features": {
            "compiler": "dpda",
            "label": "stable",
            "masked_email": "[REDACTED_EMAIL]",
            "masked_token": "[REDACTED]",
        },
        "notes": ["redacted", "tenant-scoped"],
    }

    record_provenance_1 = _with_digest(
        {
            "source_ref": "qfs://production-traces/raw/trace-1.json",
            "captured_at": "2026-06-16T09:00:00+00:00",
            "requested_by": "neuro-symbolic-service",
        },
        "source_digest_sha256",
    )
    record_provenance_2 = _with_digest(
        {
            "source_ref": "qfs://production-traces/raw/trace-2.json",
            "captured_at": "2026-06-16T09:01:00+00:00",
            "requested_by": "neuro-symbolic-service",
        },
        "source_digest_sha256",
    )
    record_redaction = _with_digest(
        {
            "applied": True,
            "validated": True,
            "rules": ["secret", "pii", "tenant-id"],
        },
        "redaction_digest_sha256",
    )

    records = [
        {
            "record_id": "trace-1",
            "schema_version": "neuro-symbolic.production-trace-training.record.v1",
            "job_id": "job-1",
            "trace_id": "trace-1",
            "replay_id": "replay-1",
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "policy_snapshot_version": "1.0.0",
            "payload": trace_payload_1,
            "provenance": record_provenance_1,
            "redaction": record_redaction,
            "content_digest_sha256": _json_digest(trace_payload_1),
        },
        {
            "record_id": "trace-2",
            "schema_version": "neuro-symbolic.production-trace-training.record.v1",
            "job_id": "job-2",
            "trace_id": "trace-2",
            "replay_id": "replay-2",
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "policy_snapshot_version": "1.0.0",
            "payload": trace_payload_2,
            "provenance": record_provenance_2,
            "redaction": record_redaction,
            "content_digest_sha256": _json_digest(trace_payload_2),
        },
    ]

    provenance = _with_digest(
        {
            "source_ref": "qfs://production-traces/raw/batch-2026-06-16.jsonl",
            "captured_at": "2026-06-16T09:00:00+00:00",
            "signed_by": "neuro-symbolic-service",
            "signature_algorithm": "HS256",
            "signature": "sig-trace-batch-001",
        },
        "source_digest_sha256",
    )
    redaction = _with_digest(
        {
            "applied": True,
            "validated": True,
            "rules": ["secret", "pii", "tenant-id"],
        },
        "redaction_digest_sha256",
    )
    selection = {
        "selection_id": "selection-2026-06-16",
        "selected_by": "neuro-symbolic-service",
        "selection_reason": "tenant-scoped production traces approved for replay-safe retraining",
        "job_ids": ["job-1", "job-2"],
        "trace_ids": ["trace-1", "trace-2"],
        "replay_ids": ["replay-1", "replay-2"],
        "tenant_id": "tenant-a",
        "project_id": "project-a",
        "policy_snapshot_version": "1.0.0",
    }
    selection["selection_digest_sha256"] = _json_digest(selection)
    approval = {
        "approval_id": "approval-2026-06-16",
        "approved_by": "privacy-review-board",
        "approved_at": "2026-06-16T09:05:00+00:00",
        "decision": "approved",
        "ticket_ref": "GOV-2026-0616",
        "tenant_id": "tenant-a",
        "project_id": "project-a",
        "policy_snapshot_version": "1.0.0",
        "replay_ids": ["replay-1", "replay-2"],
    }
    approval["approval_digest_sha256"] = _json_digest(approval)

    bundle = {
        "schema_version": "neuro-symbolic.production-trace-training.bundle.v1",
        "contract_version": "1.0.0",
        "dataset_id": "production-trace-batch-2026-06-16",
        "dataset_version": "2026.06.16",
        "record_schema_version": "neuro-symbolic.production-trace-training.record.v1",
        "tenant_id": "tenant-a",
        "project_id": "project-a",
        "policy_snapshot_version": "1.0.0",
        "compiler_version": "compiler-1.0",
        "source_kind": "production_execution_traces",
        "ownership": {
            "service_identity": "neuro-symbolic-service",
            "requested_by": "neuro-symbolic-service",
            "service_role": "internal-ingest",
        },
        "selection": selection,
        "approval": approval,
        "provenance": provenance,
        "redaction": redaction,
        "records": records,
    }
    bundle["manifest_digest_sha256"] = _json_digest(bundle)
    return bundle

def test_training_dataset_ingestion_round_trip_and_replayability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "SYSTEM_API_POLICY_SNAPSHOT_JSON",
        json.dumps(
            {
                "version": "1.0.0",
                "issuer": "eigen-auth",
                "audience": "eigen-api",
                "role_permissions": {"readonly": ["jobs:read"]},
                "service_permissions": {"neuro-symbolic-service": ["kb:ingest"]},
                "sandbox_profiles": ["default"],
            },
            sort_keys=True,
        ),
    )
    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)
    manifest = _training_dataset_manifest()

    summary = service.ingest_training_dataset(manifest, caller_identity="neuro-symbolic-service")
    replay = service.ingest_training_dataset(manifest, caller_identity="neuro-symbolic-service")

    assert summary["dataset_id"] == "training-batch-2026-06-16"
    assert summary["dataset_version"] == "2026.06.16"
    assert summary["compiler_version"] == "compiler-1.0"
    assert summary["kb_version"] == "1.0.0"
    assert summary["policy_snapshot_version"] == "1.0.0"
    assert summary["record_count"] == 4
    assert summary["manifest_digest_sha256"] == manifest["manifest_digest_sha256"]
    assert summary["dataset_digest_sha256"] == replay["dataset_digest_sha256"]
    assert summary["evidence_id"] == replay["evidence_id"]
    assert summary["records"][0]["payload"]["feature"] == "stable"

    training = service.start_training(
        {
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "dataset_id": "training-batch-2026-06-16",
            "dataset_version": "2026.06.16",
            "model_version": "model-v1",
            "policy_version": "learning-policy-v1",
        }
    )
    assert training["dataset_version"] == "2026.06.16"
    assert training["dataset_digest_sha256"] == summary["dataset_digest_sha256"]
    assert training["dataset_record_count"] == 2


def test_training_dataset_ingestion_fails_closed_on_missing_provenance_or_invalid_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "SYSTEM_API_POLICY_SNAPSHOT_JSON",
        json.dumps(
            {
                "version": "1.0.0",
                "issuer": "eigen-auth",
                "audience": "eigen-api",
                "role_permissions": {"readonly": ["jobs:read"]},
                "service_permissions": {"neuro-symbolic-service": ["kb:ingest"]},
                "sandbox_profiles": ["default"],
            },
            sort_keys=True,
        ),
    )
    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)
    manifest = _training_dataset_manifest()

    bad_schema = dict(manifest)
    bad_schema["schema_version"] = "broken-schema"
    with pytest.raises(ValueError):
        service.ingest_training_dataset(bad_schema, caller_identity="neuro-symbolic-service")

    missing_provenance = json.loads(json.dumps(manifest))
    missing_provenance.pop("provenance")
    with pytest.raises(ValueError):
        service.ingest_training_dataset(missing_provenance, caller_identity="neuro-symbolic-service")


def test_training_dataset_ingestion_fails_closed_on_redaction_or_ownership_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "SYSTEM_API_POLICY_SNAPSHOT_JSON",
        json.dumps(
            {
                "version": "1.0.0",
                "issuer": "eigen-auth",
                "audience": "eigen-api",
                "role_permissions": {"readonly": ["jobs:read"]},
                "service_permissions": {"neuro-symbolic-service": ["kb:ingest"]},
                "sandbox_profiles": ["default"],
            },
            sort_keys=True,
        ),
    )
    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)
    manifest = _training_dataset_manifest()

    bad_redaction = json.loads(json.dumps(manifest))
    bad_redaction["records"][0]["payload"]["email"] = "alice@example.com"
    with pytest.raises(KnowledgeBaseUnavailable):
        service.ingest_training_dataset(bad_redaction, caller_identity="neuro-symbolic-service")

    bad_owner = json.loads(json.dumps(manifest))
    bad_owner["ownership"]["service_identity"] = "other-service"
    with pytest.raises(KnowledgeBaseUnavailable):
        service.ingest_training_dataset(bad_owner, caller_identity="neuro-symbolic-service")


def test_training_dataset_cli_ingest_command(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys) -> None:
    monkeypatch.setenv(
        "SYSTEM_API_POLICY_SNAPSHOT_JSON",
        json.dumps(
            {
                "version": "1.0.0",
                "issuer": "eigen-auth",
                "audience": "eigen-api",
                "role_permissions": {"readonly": ["jobs:read"]},
                "service_permissions": {"neuro-symbolic-service": ["kb:ingest"]},
                "sandbox_profiles": ["default"],
            },
            sort_keys=True,
        ),
    )
    manifest_path = tmp_path / "dataset-manifest.json"
    manifest_path.write_text(json.dumps(_training_dataset_manifest(), indent=2), encoding="utf-8")

    exit_code = neuro_main([
        "ingest-dataset",
        "--manifest",
        str(manifest_path),
        "--caller-identity",
        "neuro-symbolic-service",
    ])
    output = capsys.readouterr().out.strip()
    summary = json.loads(output)

    assert exit_code == 0
    assert summary["dataset_id"] == "training-batch-2026-06-16"
    assert summary["dataset_version"] == "2026.06.16"
    assert summary["record_count"] == 4
    assert summary["evidence_ref"].startswith("kb://learning/")


def test_production_trace_training_requires_redaction_tenant_scope_and_approval() -> None:
    bundle = _production_trace_training_bundle()

    manifest = prepare_training_dataset_manifest(bundle, caller_identity="neuro-symbolic-service")
    assert manifest["dataset_id"] == "production-trace-batch-2026-06-16"
    assert manifest["compiler_version"] == "compiler-1.0"
    assert manifest["kb_version"] == "1.0.0"
    assert manifest["selection"]["trace_ids"] == ["trace-1", "trace-2"]
    assert manifest["approval"]["replay_ids"] == ["replay-1", "replay-2"]
    assert manifest["records"][0]["replay_ref"] == "nsc://replay/trace-1/replay-1"
    assert manifest["records"][0]["trace_ref"] == "nsc://trace/trace-1"

    unredacted_bundle = json.loads(json.dumps(bundle))
    unredacted_bundle["records"][0]["payload"]["features"]["masked_email"] = "alice@example.com"
    with pytest.raises(ProductionTraceTrainingError):
        prepare_training_dataset_manifest(unredacted_bundle, caller_identity="neuro-symbolic-service")

    foreign_scope_bundle = json.loads(json.dumps(bundle))
    foreign_scope_bundle["records"][1]["tenant_id"] = "tenant-b"
    with pytest.raises(ProductionTraceTrainingError):
        prepare_training_dataset_manifest(foreign_scope_bundle, caller_identity="neuro-symbolic-service")

    missing_approval_bundle = json.loads(json.dumps(bundle))
    missing_approval_bundle.pop("approval")
    with pytest.raises(ProductionTraceTrainingError):
        prepare_training_dataset_manifest(missing_approval_bundle, caller_identity="neuro-symbolic-service")


def test_production_trace_training_is_replayable_and_cli_ingestable(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys) -> None:
    monkeypatch.setenv(
        "SYSTEM_API_POLICY_SNAPSHOT_JSON",
        json.dumps(
            {
                "version": "1.0.0",
                "issuer": "eigen-auth",
                "audience": "eigen-api",
                "role_permissions": {"readonly": ["jobs:read"]},
                "service_permissions": {"neuro-symbolic-service": ["kb:ingest"]},
                "sandbox_profiles": ["default"],
            },
            sort_keys=True,
        ),
    )
    bundle = _production_trace_training_bundle()
    bundle_path = tmp_path / "production-trace-bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    first = prepare_training_dataset_manifest(bundle, caller_identity="neuro-symbolic-service")
    second = prepare_training_dataset_manifest(json.loads(bundle_path.read_text(encoding="utf-8")), caller_identity="neuro-symbolic-service")
    assert first["manifest_digest_sha256"] == second["manifest_digest_sha256"]

    exit_code = neuro_main([
        "ingest-production-traces",
        "--manifest",
        str(bundle_path),
        "--caller-identity",
        "neuro-symbolic-service",
    ])
    output = capsys.readouterr().out.strip()
    summary = json.loads(output)

    assert exit_code == 0
    assert summary["dataset_id"] == "production-trace-batch-2026-06-16"
    assert summary["tenant_id"] == "tenant-a"
    assert summary["compiler_version"] == "compiler-1.0"
    assert summary["kb_version"] == "1.0.0"
    assert summary["policy_snapshot_version"] == "1.0.0"
    assert summary["trace_ids"] == ["trace-1", "trace-2"]
    assert summary["replay_ids"] == ["replay-1", "replay-2"]
    assert summary["approval"]["approval_id"] == "approval-2026-06-16"
    assert summary["selection"]["selection_id"] == "selection-2026-06-16"
    assert summary["records"][0]["payload"]["features"]["masked_email"] == "[REDACTED_EMAIL]"


def _historical_compilation_training_bundle() -> dict[str, object]:
    aqo_1 = {
        "version": "1.0.0",
        "qubits": 2,
        "operations": [
            {"op": "RX", "target": 0, "theta": 1.0},
            {"op": "MEASURE", "target": 0},
        ],
    }
    aqo_2 = {
        "version": "1.0.0",
        "qubits": 2,
        "operations": [
            {"op": "RX", "target": 1, "theta": 0.5},
            {"op": "MEASURE", "target": 1},
        ],
    }
    record_provenance_1 = _with_digest(
        {
            "source_ref": "qfs://historical-compilations/raw/run-002.json",
            "captured_at": "2026-06-16T10:00:00+00:00",
            "requested_by": "neuro-symbolic-service",
        },
        "source_digest_sha256",
    )
    record_provenance_2 = _with_digest(
        {
            "source_ref": "qfs://historical-compilations/raw/run-001.json",
            "captured_at": "2026-06-16T09:59:00+00:00",
            "requested_by": "neuro-symbolic-service",
        },
        "source_digest_sha256",
    )
    record_redaction = _with_digest(
        {
            "applied": True,
            "validated": True,
            "rules": ["secret", "pii", "tenant-id"],
        },
        "redaction_digest_sha256",
    )
    records = [
        {
            "record_id": "hist-002",
            "schema_version": "neuro-symbolic.historical-compilation-training.record.v1",
            "job_id": "job-002",
            "trace_id": "trace-002",
            "replay_id": "replay-002",
            "request_id": "request-002",
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "policy_snapshot_version": "1.0.0",
            "payload": {
                "compiler_status": "DONE",
                "rewrite_outcome": "accepted",
                "accepted_rewrite_ids": ["rewrite-accept-002a", "rewrite-accept-002b"],
                "rejected_rewrite_ids": ["rewrite-reject-002a"],
                "timing_ms": {"parse": 4.5, "rewrite": 8.25, "emit": 3.0},
                "final_aqo": aqo_2,
            },
            "provenance": record_provenance_1,
            "redaction": record_redaction,
            "content_digest_sha256": _json_digest({
                "accepted_rewrite_ids": ["rewrite-accept-002a", "rewrite-accept-002b"],
                "compiler_status": "DONE",
                "final_aqo": aqo_2,
                "rejected_rewrite_ids": ["rewrite-reject-002a"],
                "rewrite_outcome": "accepted",
                "timing_ms": {"parse": 4.5, "rewrite": 8.25, "emit": 3.0},
            }),
        },
        {
            "record_id": "hist-001",
            "schema_version": "neuro-symbolic.historical-compilation-training.record.v1",
            "job_id": "job-001",
            "trace_id": "trace-001",
            "replay_id": "replay-001",
            "request_id": "request-001",
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "policy_snapshot_version": "1.0.0",
            "payload": {
                "compiler_status": "DONE",
                "rewrite_outcome": "rejected",
                "accepted_rewrite_ids": [],
                "rejected_rewrite_ids": ["rewrite-reject-001a", "rewrite-reject-001b"],
                "timing_ms": {"parse": 5.0, "rewrite": 9.5, "emit": 2.5},
                "final_aqo": aqo_1,
            },
            "provenance": record_provenance_2,
            "redaction": record_redaction,
            "content_digest_sha256": _json_digest({
                "accepted_rewrite_ids": [],
                "compiler_status": "DONE",
                "final_aqo": aqo_1,
                "rejected_rewrite_ids": ["rewrite-reject-001a", "rewrite-reject-001b"],
                "rewrite_outcome": "rejected",
                "timing_ms": {"parse": 5.0, "rewrite": 9.5, "emit": 2.5},
            }),
        },
        {
            "record_id": "hist-004",
            "schema_version": "neuro-symbolic.historical-compilation-training.record.v1",
            "job_id": "job-004",
            "trace_id": "trace-004",
            "replay_id": "replay-004",
            "request_id": "request-004",
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "policy_snapshot_version": "1.0.0",
            "compiler_version": "compiler-1.0",
            "payload": {
                "compiler_status": "DONE",
                "rewrite_outcome": "unsafe",
                "accepted_rewrite_ids": [],
                "rejected_rewrite_ids": ["rewrite-reject-004a"],
                "timing_ms": {"parse": 6.0, "rewrite": 11.0, "emit": 3.5},
                "final_aqo": aqo_2,
            },
            "provenance": record_provenance_2,
            "redaction": record_redaction,
            "content_digest_sha256": _json_digest({
                "accepted_rewrite_ids": [],
                "compiler_status": "DONE",
                "final_aqo": aqo_2,
                "rejected_rewrite_ids": ["rewrite-reject-004a"],
                "rewrite_outcome": "unsafe",
                "timing_ms": {"parse": 6.0, "rewrite": 11.0, "emit": 3.5},
            }),
        },
        {
            "record_id": "hist-003",
            "schema_version": "neuro-symbolic.historical-compilation-training.record.v1",
            "job_id": "job-003",
            "trace_id": "trace-003",
            "replay_id": "replay-003",
            "request_id": "request-003",
            "tenant_id": "tenant-a",
            "project_id": "project-a",
            "policy_snapshot_version": "1.0.0",
            "payload": {
                "compiler_status": "DONE",
                "rewrite_outcome": "equivalent",
                "accepted_rewrite_ids": ["rewrite-equivalent-003a"],
                "rejected_rewrite_ids": [],
                "timing_ms": {"parse": 4.25, "rewrite": 7.5, "emit": 2.0},
                "final_aqo": aqo_1,
            },
            "provenance": record_provenance_1,
            "redaction": record_redaction,
            "content_digest_sha256": _json_digest({
                "accepted_rewrite_ids": ["rewrite-equivalent-003a"],
                "compiler_status": "DONE",
                "final_aqo": aqo_1,
                "rejected_rewrite_ids": [],
                "rewrite_outcome": "equivalent",
                "timing_ms": {"parse": 4.25, "rewrite": 7.5, "emit": 2.0},
            }),
        },
    ]
    provenance = _with_digest(
        {
            "source_ref": "qfs://historical-compilations/raw/batch-2026-06-16.jsonl",
            "captured_at": "2026-06-16T10:00:00+00:00",
            "signed_by": "neuro-symbolic-service",
            "signature_algorithm": "HS256",
            "signature": "sig-hist-001",
        },
        "source_digest_sha256",
    )
    redaction = _with_digest(
        {
            "applied": True,
            "validated": True,
            "rules": ["secret", "pii", "tenant-id"],
        },
        "redaction_digest_sha256",
    )
    selection = {
        "selection_id": "selection-hist-2026-06-16",
        "selected_by": "neuro-symbolic-service",
        "selection_reason": "historical compiler runs selected for pass-path corpus extraction",
        "job_ids": ["job-002", "job-001", "job-004", "job-003"],
        "trace_ids": ["trace-002", "trace-001", "trace-004", "trace-003"],
        "replay_ids": ["replay-002", "replay-001", "replay-004", "replay-003"],
        "tenant_id": "tenant-a",
        "project_id": "project-a",
        "policy_snapshot_version": "1.0.0",
    }
    selection["selection_digest_sha256"] = _json_digest(selection)
    approval = {
        "approval_id": "approval-hist-2026-06-16",
        "approved_by": "compiler-governance",
        "approved_at": "2026-06-16T10:05:00+00:00",
        "decision": "approved",
        "ticket_ref": "CORPUS-2026-0616",
        "tenant_id": "tenant-a",
        "project_id": "project-a",
        "policy_snapshot_version": "1.0.0",
        "replay_ids": ["replay-002", "replay-001", "replay-004", "replay-003"],
    }
    approval["approval_digest_sha256"] = _json_digest(approval)
    bundle = {
        "schema_version": "neuro-symbolic.historical-compilation-training.bundle.v1",
        "contract_version": "1.0.0",
        "dataset_id": "historical-compilation-batch-2026-06-16",
        "dataset_version": "2026.06.16",
        "record_schema_version": "neuro-symbolic.historical-compilation-training.record.v1",
        "tenant_id": "tenant-a",
        "project_id": "project-a",
        "policy_snapshot_version": "1.0.0",
        "source_kind": "historical_compilations",
        "ownership": {
            "service_identity": "neuro-symbolic-service",
            "requested_by": "neuro-symbolic-service",
            "service_role": "internal-ingest",
        },
        "selection": selection,
        "approval": approval,
        "provenance": provenance,
        "redaction": redaction,
        "records": records,
    }
    bundle["manifest_digest_sha256"] = _json_digest(bundle)
    return bundle


def test_historical_compilation_training_dataset_is_reproducible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "SYSTEM_API_POLICY_SNAPSHOT_JSON",
        json.dumps(
            {
                "version": "1.0.0",
                "issuer": "eigen-auth",
                "audience": "eigen-api",
                "role_permissions": {"readonly": ["jobs:read"]},
                "service_permissions": {"neuro-symbolic-service": ["kb:ingest"]},
                "sandbox_profiles": ["default"],
            },
            sort_keys=True,
        ),
    )
    bundle = _historical_compilation_training_bundle()
    reordered = json.loads(json.dumps(bundle))
    reordered["records"] = list(reversed(reordered["records"]))
    reordered["selection"]["job_ids"] = list(reversed(reordered["selection"]["job_ids"]))
    reordered["selection"]["trace_ids"] = list(reversed(reordered["selection"]["trace_ids"]))
    reordered["selection"]["replay_ids"] = list(reversed(reordered["selection"]["replay_ids"]))

    first = prepare_historical_compilation_training_manifest(bundle, caller_identity="neuro-symbolic-service")
    second = prepare_historical_compilation_training_manifest(reordered, caller_identity="neuro-symbolic-service")

    assert first["schema_version"] == "neuro-symbolic.training-dataset.manifest.v1"
    assert first["source_kind"] == "historical_compilations"
    assert first["selection"]["job_ids"] == ["job-001", "job-002", "job-003", "job-004"]
    assert first["selection"]["trace_ids"] == ["trace-001", "trace-002", "trace-003", "trace-004"]
    assert first["selection"]["replay_ids"] == ["replay-001", "replay-002", "replay-003", "replay-004"]
    assert first["records"][0]["job_id"] == "job-001"
    assert first["records"][0]["trace_ref"] == "nsc://trace/trace-001"
    assert first["records"][0]["replay_ref"] == "nsc://replay/trace-001/replay-001"
    assert first["manifest_digest_sha256"] == second["manifest_digest_sha256"]


def test_historical_compilation_training_dataset_ingests_and_clis(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys) -> None:
    monkeypatch.setenv(
        "SYSTEM_API_POLICY_SNAPSHOT_JSON",
        json.dumps(
            {
                "version": "1.0.0",
                "issuer": "eigen-auth",
                "audience": "eigen-api",
                "role_permissions": {"readonly": ["jobs:read"]},
                "service_permissions": {"neuro-symbolic-service": ["kb:ingest"]},
                "sandbox_profiles": ["default"],
            },
            sort_keys=True,
        ),
    )
    bundle = _historical_compilation_training_bundle()
    bundle_path = tmp_path / "historical-compilation-bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)
    manifest = prepare_historical_compilation_training_manifest(bundle, caller_identity="neuro-symbolic-service")
    summary = service.ingest_training_dataset(manifest, caller_identity="neuro-symbolic-service")
    replay_summary = service.ingest_training_dataset(manifest, caller_identity="neuro-symbolic-service")
    assert summary["dataset_id"] == "historical-compilation-batch-2026-06-16"
    assert summary["compiler_version"] == "compiler-1.0"
    assert summary["kb_version"] == "1.0.0"
    assert summary["record_count"] == 4
    assert summary["source_kind"] == "historical_compilations"
    assert summary["selection"]["selection_id"] == "selection-hist-2026-06-16"
    assert summary["approval"]["approval_id"] == "approval-hist-2026-06-16"
    assert summary["records"][0]["payload"]["compiler_status"] == "DONE"
    assert sorted(record["payload"]["rewrite_outcome"] for record in summary["records"]) == ["accepted", "equivalent", "rejected", "unsafe"]
    assert summary["dataset_digest_sha256"] == replay_summary["dataset_digest_sha256"]
    assert summary["evidence_id"] == replay_summary["evidence_id"]

    exit_code = neuro_main([
        "ingest-historical-compilations",
        "--manifest",
        str(bundle_path),
        "--caller-identity",
        "neuro-symbolic-service",
    ])
    output = capsys.readouterr().out.strip()
    cli_summary = json.loads(output)

    assert exit_code == 0
    assert cli_summary["dataset_id"] == "historical-compilation-batch-2026-06-16"
    assert cli_summary["compiler_version"] == "compiler-1.0"
    assert cli_summary["kb_version"] == "1.0.0"
    assert cli_summary["record_count"] == 4
    assert cli_summary["source_kind"] == "historical_compilations"
    assert cli_summary["trace_ids"] == ["trace-001", "trace-002", "trace-003", "trace-004"]
    assert cli_summary["replay_ids"] == ["replay-001", "replay-002", "replay-003", "replay-004"]
