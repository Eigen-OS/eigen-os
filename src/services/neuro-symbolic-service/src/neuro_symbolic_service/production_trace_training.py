"""Privacy-safe production trace training helpers for Neuro-DPDA."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any


_CONTRACT_VERSION = "1.0.0"
_TRACE_BUNDLE_SCHEMA = "neuro-symbolic.production-trace-training.bundle.v1"
_TRACE_RECORD_SCHEMA = "neuro-symbolic.production-trace-training.record.v1"
_TRAINING_DATASET_MANIFEST_SCHEMA = "neuro-symbolic.training-dataset.manifest.v1"

_REDACTED_VALUE = "[REDACTED]"
_MASKED_EMAIL_VALUE = "[REDACTED_EMAIL]"
_MASKED_PHONE_VALUE = "[REDACTED_PHONE]"
_MASKED_IDENTIFIER_VALUE = "[REDACTED_ID]"

_REDACT_DELETE_KEYS = {
    "authorization",
    "auth_header",
    "bearer",
    "cookie",
    "credentials",
    "credential",
    "password",
    "passwd",
    "pwd",
    "secret",
    "session_cookie",
    "session_token",
    "token",
    "api_key",
    "access_token",
    "refresh_token",
    "id_token",
    "raw_authorization",
    "raw_auth_header",
    "body",
    "payload",
    "raw_payload",
    "raw_request_body",
    "request_body",
    "stack_trace",
    "trace_dump",
}
_REDACT_MASK_EMAIL_KEYS = {"email", "email_address", "contact_email", "e_mail"}
_REDACT_MASK_PHONE_KEYS = {"phone", "phone_number", "mobile", "msisdn", "contact_phone"}
_REDACT_MASK_IDENTIFIER_KEYS = {
    "id",
    "identifier",
    "internal_id",
    "internal_identifier",
    "subject_id",
    "user_id",
    "tenant_id",
    "project_id",
    "request_id",
    "trace_id",
    "session_id",
    "correlation_id",
    "device_id",
    "account_id",
}

_EMAIL_RE = re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
_PHONE_RE = re.compile(r"(?i)(?<!\d)(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?){1,3}\d{2,4}(?!\d)")
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}\b")
_UUID_RE = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
_SECRET_PATH_RE = re.compile(
    r"(?i)(?P<path>(?:[A-Za-z]:\\|/)(?:[^\s\"'<>]*/)*(?:secrets?|secret|private|credentials?|tokens?|keys?)(?:/[^\s\"'<>]*)?)"
)


class ProductionTraceTrainingError(ValueError):
    """Raised when a production trace bundle cannot be promoted into the training corpus."""


@dataclass(frozen=True)
class TrainingSelectionSummary:
    trace_ids: tuple[str, ...]
    replay_ids: tuple[str, ...]
    selection_id: str
    selected_by: str
    selection_reason: str


@dataclass(frozen=True)
class TrainingApprovalSummary:
    approval_id: str
    approved_by: str
    approved_at: str
    ticket_ref: str
    decision: str
    policy_snapshot_version: str
    tenant_id: str
    project_id: str
    replay_ids: tuple[str, ...]


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _hex_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _redact_scalar_text(text: str, path: str, redactions: set[str]) -> str:
    original = text
    text = _BEARER_RE.sub(_REDACTED_VALUE, text)
    text = _SECRET_PATH_RE.sub(_REDACTED_VALUE, text)
    text = _EMAIL_RE.sub(_MASKED_EMAIL_VALUE, text)
    text = _PHONE_RE.sub(_MASKED_PHONE_VALUE, text)
    text = _UUID_RE.sub(_MASKED_IDENTIFIER_VALUE, text)
    if text != original:
        redactions.add(path)
    return text


def _redact_json_value(value: Any, path: str, redactions: set[str]):
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, nested in value.items():
            key_lower = str(key).strip().lower()
            nested_path = f"{path}.{key}" if path else str(key)
            if key_lower in _REDACT_DELETE_KEYS:
                redacted[key] = _REDACTED_VALUE
                redactions.add(nested_path)
                continue
            if key_lower in _REDACT_MASK_EMAIL_KEYS:
                redacted[key] = _MASKED_EMAIL_VALUE
                redactions.add(nested_path)
                continue
            if key_lower in _REDACT_MASK_PHONE_KEYS:
                redacted[key] = _MASKED_PHONE_VALUE
                redactions.add(nested_path)
                continue
            if key_lower in _REDACT_MASK_IDENTIFIER_KEYS or key_lower.endswith("_id"):
                if isinstance(nested, (dict, list)):
                    redacted[key] = _redact_json_value(nested, nested_path, redactions)
                else:
                    redacted[key] = _MASKED_IDENTIFIER_VALUE
                    redactions.add(nested_path)
                continue
            redacted[key] = _redact_json_value(nested, nested_path, redactions)
        return redacted
    if isinstance(value, list):
        return [_redact_json_value(item, f"{path}[{idx}]", redactions) for idx, item in enumerate(value)]
    if isinstance(value, str):
        return _redact_scalar_text(value, path, redactions)
    return value


def _is_redacted_payload(payload: Any) -> bool:
    redactions: set[str] = set()
    return _redact_json_value(payload, "$", redactions) == payload


def _require_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProductionTraceTrainingError(f"{field_name} must be an object")
    return value


def _require_string(value: Any, *, field_name: str) -> str:
    if value is None:
        raise ProductionTraceTrainingError(f"{field_name} is required")
    text = str(value).strip()
    if not text or text.lower() == "none":
        raise ProductionTraceTrainingError(f"{field_name} is required")
    return text


def _require_digest(value: Any, *, field_name: str) -> str:
    digest = str(value).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ProductionTraceTrainingError(f"{field_name} must be a SHA-256 hex digest")
    return digest


def _normalize_replay_ids(value: Any, *, field_name: str) -> tuple[str, ...]:
    if value in (None, ""):
        raise ProductionTraceTrainingError(f"{field_name} is required")
    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = (value,)
    normalized: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in normalized:
            normalized.append(text)
    if not normalized:
        raise ProductionTraceTrainingError(f"{field_name} is required")
    return tuple(normalized)


def _normalize_trace_selection(bundle: dict[str, Any], *, caller_identity: str, tenant_id: str, project_id: str, policy_snapshot_version: str) -> TrainingSelectionSummary:
    selection = _require_mapping(bundle.get("selection"), field_name="selection")
    selection_id = _require_string(selection.get("selection_id"), field_name="selection.selection_id")
    selected_by = _require_string(selection.get("selected_by"), field_name="selection.selected_by")
    selection_reason = _require_string(selection.get("selection_reason"), field_name="selection.selection_reason")
    trace_ids = _normalize_replay_ids(selection.get("trace_ids") or selection.get("selected_trace_ids"), field_name="selection.trace_ids")
    replay_ids = _normalize_replay_ids(selection.get("replay_ids"), field_name="selection.replay_ids")
    selection_policy = _require_string(selection.get("policy_snapshot_version", policy_snapshot_version), field_name="selection.policy_snapshot_version")
    selection_tenant = _require_string(selection.get("tenant_id", tenant_id), field_name="selection.tenant_id")
    selection_project = _require_string(selection.get("project_id", project_id), field_name="selection.project_id")
    if selection_tenant != tenant_id or selection_project != project_id:
        raise ProductionTraceTrainingError("selection must remain tenant-scoped")
    if selection_policy != policy_snapshot_version:
        raise ProductionTraceTrainingError("selection policy snapshot version must match the bundle")
    if selected_by != caller_identity:
        raise ProductionTraceTrainingError("selection.selected_by must match the internal caller identity")
    return TrainingSelectionSummary(
        trace_ids=trace_ids,
        replay_ids=replay_ids,
        selection_id=selection_id,
        selected_by=selected_by,
        selection_reason=selection_reason,
    )


def _normalize_trace_approval(bundle: dict[str, Any], *, tenant_id: str, project_id: str, policy_snapshot_version: str, selection: TrainingSelectionSummary) -> TrainingApprovalSummary:
    approval = _require_mapping(bundle.get("approval"), field_name="approval")
    approval_id = _require_string(approval.get("approval_id"), field_name="approval.approval_id")
    approved_by = _require_string(approval.get("approved_by"), field_name="approval.approved_by")
    approved_at = _require_string(approval.get("approved_at"), field_name="approval.approved_at")
    decision = _require_string(approval.get("decision", "approved"), field_name="approval.decision")
    if decision.lower() != "approved":
        raise ProductionTraceTrainingError("approval.decision must be approved")
    approval_ticket_ref = _require_string(approval.get("ticket_ref"), field_name="approval.ticket_ref")
    approval_policy = _require_string(approval.get("policy_snapshot_version", policy_snapshot_version), field_name="approval.policy_snapshot_version")
    approval_tenant = _require_string(approval.get("tenant_id", tenant_id), field_name="approval.tenant_id")
    approval_project = _require_string(approval.get("project_id", project_id), field_name="approval.project_id")
    replay_ids = _normalize_replay_ids(approval.get("replay_ids") or selection.replay_ids, field_name="approval.replay_ids")
    if approval_tenant != tenant_id or approval_project != project_id:
        raise ProductionTraceTrainingError("approval must remain tenant-scoped")
    if approval_policy != policy_snapshot_version:
        raise ProductionTraceTrainingError("approval policy snapshot version must match the bundle")
    if not set(selection.replay_ids).issubset(set(replay_ids)):
        raise ProductionTraceTrainingError("approval replay_ids must cover all selected replay identifiers")
    return TrainingApprovalSummary(
        approval_id=approval_id,
        approved_by=approved_by,
        approved_at=approved_at,
        ticket_ref=approval_ticket_ref,
        decision=decision.lower(),
        policy_snapshot_version=approval_policy,
        tenant_id=approval_tenant,
        project_id=approval_project,
        replay_ids=replay_ids,
    )


def _normalize_provenance(provenance: Any, *, field_name: str) -> dict[str, str]:
    mapping = _require_mapping(provenance, field_name=field_name)
    source_ref = _require_string(mapping.get("source_ref"), field_name=f"{field_name}.source_ref")
    captured_at = _require_string(mapping.get("captured_at"), field_name=f"{field_name}.captured_at")
    signed_by = _require_string(mapping.get("signed_by"), field_name=f"{field_name}.signed_by")
    signature_algorithm = _require_string(mapping.get("signature_algorithm"), field_name=f"{field_name}.signature_algorithm")
    signature = _require_string(mapping.get("signature"), field_name=f"{field_name}.signature")
    source_digest_sha256 = _require_digest(mapping.get("source_digest_sha256"), field_name=f"{field_name}.source_digest_sha256")
    computed_digest = hashlib.sha256(_stable_json({k: v for k, v in mapping.items() if k != "source_digest_sha256"}).encode("utf-8")).hexdigest()
    if computed_digest != source_digest_sha256:
        raise ProductionTraceTrainingError(f"{field_name}.source_digest_sha256 mismatch")
    return {
        "source_ref": source_ref,
        "captured_at": captured_at,
        "signed_by": signed_by,
        "signature_algorithm": signature_algorithm,
        "signature": signature,
        "source_digest_sha256": source_digest_sha256,
    }


def _normalize_redaction(redaction: Any, *, field_name: str) -> dict[str, Any]:
    mapping = _require_mapping(redaction, field_name=field_name)
    if not bool(mapping.get("applied", False)) or not bool(mapping.get("validated", False)):
        raise ProductionTraceTrainingError(f"{field_name} must be applied and validated")
    rules = [str(rule).strip() for rule in (mapping.get("rules") or []) if str(rule).strip()]
    if not rules:
        raise ProductionTraceTrainingError(f"{field_name}.rules are required")
    redaction_digest_sha256 = _require_digest(mapping.get("redaction_digest_sha256"), field_name=f"{field_name}.redaction_digest_sha256")
    computed_digest = hashlib.sha256(_stable_json({k: v for k, v in mapping.items() if k != "redaction_digest_sha256"}).encode("utf-8")).hexdigest()
    if computed_digest != redaction_digest_sha256:
        raise ProductionTraceTrainingError(f"{field_name}.redaction_digest_sha256 mismatch")
    return {
        "applied": True,
        "validated": True,
        "rules": rules,
        "redaction_digest_sha256": redaction_digest_sha256,
    }


def _normalize_record_provenance(provenance: Any, *, field_name: str) -> dict[str, str]:
    mapping = _require_mapping(provenance, field_name=field_name)
    source_ref = _require_string(mapping.get("source_ref"), field_name=f"{field_name}.source_ref")
    captured_at = _require_string(mapping.get("captured_at"), field_name=f"{field_name}.captured_at")
    requested_by = _require_string(mapping.get("requested_by"), field_name=f"{field_name}.requested_by")
    source_digest_sha256 = _require_digest(mapping.get("source_digest_sha256"), field_name=f"{field_name}.source_digest_sha256")
    computed_digest = hashlib.sha256(_stable_json({k: v for k, v in mapping.items() if k != "source_digest_sha256"}).encode("utf-8")).hexdigest()
    if computed_digest != source_digest_sha256:
        raise ProductionTraceTrainingError(f"{field_name}.source_digest_sha256 mismatch")
    return {
        "source_ref": source_ref,
        "captured_at": captured_at,
        "requested_by": requested_by,
        "source_digest_sha256": source_digest_sha256,
    }


def _normalize_trace_record(record: Any, *, idx: int, tenant_id: str, project_id: str, policy_snapshot_version: str, record_schema_version: str) -> dict[str, Any]:
    mapping = _require_mapping(record, field_name=f"records[{idx}]")
    record_id = _require_string(mapping.get("record_id"), field_name=f"records[{idx}].record_id")
    schema_version = _require_string(mapping.get("schema_version"), field_name=f"records[{idx}].schema_version")
    if schema_version != record_schema_version:
        raise ProductionTraceTrainingError(f"records[{idx}].schema_version must match the bundle record_schema_version")
    trace_id = _require_string(mapping.get("trace_id", record_id), field_name=f"records[{idx}].trace_id")
    replay_id = _require_string(mapping.get("replay_id"), field_name=f"records[{idx}].replay_id")
    record_tenant = _require_string(mapping.get("tenant_id", tenant_id), field_name=f"records[{idx}].tenant_id")
    record_project = _require_string(mapping.get("project_id", project_id), field_name=f"records[{idx}].project_id")
    record_policy = _require_string(mapping.get("policy_snapshot_version", policy_snapshot_version), field_name=f"records[{idx}].policy_snapshot_version")
    if record_tenant != tenant_id or record_project != project_id:
        raise ProductionTraceTrainingError(f"records[{idx}] must remain tenant-scoped")
    if record_policy != policy_snapshot_version:
        raise ProductionTraceTrainingError(f"records[{idx}].policy_snapshot_version must match the bundle")
    payload = mapping.get("payload")
    if not isinstance(payload, (dict, list, str, int, float, bool)):
        raise ProductionTraceTrainingError(f"records[{idx}].payload must be JSON-serializable")
    if not _is_redacted_payload(payload):
        raise ProductionTraceTrainingError(f"records[{idx}] must be redacted before ingestion")
    content_digest_sha256 = _require_digest(mapping.get("content_digest_sha256"), field_name=f"records[{idx}].content_digest_sha256")
    computed_content_digest = hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()
    if computed_content_digest != content_digest_sha256:
        raise ProductionTraceTrainingError(f"records[{idx}].content_digest_sha256 mismatch")
    provenance = _normalize_record_provenance(mapping.get("provenance"), field_name=f"records[{idx}].provenance")
    redaction = _normalize_redaction(mapping.get("redaction"), field_name=f"records[{idx}].redaction")
    replay_ref = f"nsc://replay/{trace_id}/{replay_id}"
    trace_ref = f"nsc://trace/{trace_id}"
    return {
        "record_id": record_id,
        "schema_version": schema_version,
        "trace_id": trace_id,
        "replay_id": replay_id,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "policy_snapshot_version": policy_snapshot_version,
        "source_kind": "production_execution_trace",
        "content_digest_sha256": content_digest_sha256,
        "payload": payload,
        "provenance": provenance,
        "redaction": redaction,
        "replay_ref": replay_ref,
        "trace_ref": trace_ref,
    }


def prepare_training_dataset_manifest(bundle: dict[str, Any], *, caller_identity: str) -> dict[str, Any]:
    schema_version = _require_string(bundle.get("schema_version"), field_name="schema_version")
    if schema_version != _TRACE_BUNDLE_SCHEMA:
        raise ProductionTraceTrainingError("unsupported production trace bundle schema")
    contract_version = _require_string(bundle.get("contract_version", _CONTRACT_VERSION), field_name="contract_version")
    dataset_id = _require_string(bundle.get("dataset_id"), field_name="dataset_id")
    dataset_version = _require_string(bundle.get("dataset_version"), field_name="dataset_version")
    record_schema_version = _require_string(bundle.get("record_schema_version", _TRACE_RECORD_SCHEMA), field_name="record_schema_version")
    tenant_id = _require_string(bundle.get("tenant_id"), field_name="tenant_id")
    project_id = _require_string(bundle.get("project_id"), field_name="project_id")
    policy_snapshot_version = _require_string(bundle.get("policy_snapshot_version"), field_name="policy_snapshot_version")

    ownership = _require_mapping(bundle.get("ownership"), field_name="ownership")
    service_identity = _require_string(ownership.get("service_identity"), field_name="ownership.service_identity")
    requested_by = _require_string(ownership.get("requested_by", caller_identity), field_name="ownership.requested_by")
    service_role = _require_string(ownership.get("service_role", "internal-ingest"), field_name="ownership.service_role")
    if service_identity != caller_identity or requested_by != caller_identity:
        raise ProductionTraceTrainingError("ownership must resolve to the internal caller identity")

    selection = _normalize_trace_selection(
        bundle,
        caller_identity=caller_identity,
        tenant_id=tenant_id,
        project_id=project_id,
        policy_snapshot_version=policy_snapshot_version,
    )
    approval = _normalize_trace_approval(
        bundle,
        tenant_id=tenant_id,
        project_id=project_id,
        policy_snapshot_version=policy_snapshot_version,
        selection=selection,
    )
    provenance = _normalize_provenance(bundle.get("provenance"), field_name="provenance")
    redaction = _normalize_redaction(bundle.get("redaction"), field_name="redaction")

    records = bundle.get("records")
    if not isinstance(records, list) or not records:
        raise ProductionTraceTrainingError("records must be a non-empty list")

    normalized_records = [
        _normalize_trace_record(
            record,
            idx=idx,
            tenant_id=tenant_id,
            project_id=project_id,
            policy_snapshot_version=policy_snapshot_version,
            record_schema_version=record_schema_version,
        )
        for idx, record in enumerate(records)
    ]

    record_digests = [record["content_digest_sha256"] for record in normalized_records]
    trace_ids = [record["trace_id"] for record in normalized_records]
    replay_ids = [record["replay_id"] for record in normalized_records]
    if tuple(trace_ids) != selection.trace_ids:
        raise ProductionTraceTrainingError("selection.trace_ids must match the selected records")
    if not set(replay_ids).issubset(set(selection.replay_ids)):
        raise ProductionTraceTrainingError("selection.replay_ids must cover the selected records")

    normalized_manifest = {
        "schema_version": _TRAINING_DATASET_MANIFEST_SCHEMA,
        "contract_version": _CONTRACT_VERSION,
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "record_schema_version": record_schema_version,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "policy_snapshot_version": policy_snapshot_version,
        "source_kind": "production_execution_traces",
        "ownership": {
            "service_identity": service_identity,
            "requested_by": requested_by,
            "service_role": service_role,
        },
        "selection": {
            "selection_id": selection.selection_id,
            "selected_by": selection.selected_by,
            "selection_reason": selection.selection_reason,
            "trace_ids": list(selection.trace_ids),
            "replay_ids": list(selection.replay_ids),
            "tenant_id": tenant_id,
            "project_id": project_id,
            "policy_snapshot_version": policy_snapshot_version,
        },
        "approval": {
            "approval_id": approval.approval_id,
            "approved_by": approval.approved_by,
            "approved_at": approval.approved_at,
            "decision": approval.decision,
            "ticket_ref": approval.ticket_ref,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "policy_snapshot_version": policy_snapshot_version,
            "replay_ids": list(approval.replay_ids),
        },
        "provenance": provenance,
        "redaction": redaction,
        "records": normalized_records,
    }

    normalized_manifest["manifest_digest_sha256"] = _hex_digest(_stable_json(normalized_manifest).encode("utf-8"))
    dataset_digest_source = {
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "policy_snapshot_version": policy_snapshot_version,
        "ownership": normalized_manifest["ownership"],
        "selection": normalized_manifest["selection"],
        "approval": normalized_manifest["approval"],
        "provenance": provenance,
        "redaction": redaction,
        "record_digests": record_digests,
        "replay_ids": replay_ids,
    }
    return normalized_manifest


_HISTORICAL_COMPILATION_BUNDLE_SCHEMA = "neuro-symbolic.historical-compilation-training.bundle.v1"
_HISTORICAL_COMPILATION_RECORD_SCHEMA = "neuro-symbolic.historical-compilation-training.record.v1"


def _normalize_string_list(value: Any, *, field_name: str, allow_empty: bool = False) -> tuple[str, ...]:
    if value in (None, ""):
        if allow_empty:
            return tuple()
        raise ProductionTraceTrainingError(f"{field_name} is required")
    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = (value,)
    normalized: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in normalized:
            normalized.append(text)
    if not normalized and not allow_empty:
        raise ProductionTraceTrainingError(f"{field_name} is required")
    return tuple(sorted(normalized))


def _normalize_numeric_tree(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize_numeric_tree(nested) for key, nested in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        return [_normalize_numeric_tree(item) for item in value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), 6)
    return value


def _normalize_historical_compilation_selection(
    bundle: dict[str, Any],
    *,
    caller_identity: str,
    tenant_id: str,
    project_id: str,
    policy_snapshot_version: str,
) -> TrainingSelectionSummary:
    selection = _require_mapping(bundle.get("selection"), field_name="selection")
    selection_id = _require_string(selection.get("selection_id"), field_name="selection.selection_id")
    selected_by = _require_string(selection.get("selected_by"), field_name="selection.selected_by")
    selection_reason = _require_string(selection.get("selection_reason"), field_name="selection.selection_reason")
    trace_ids = _normalize_string_list(selection.get("trace_ids") or selection.get("selected_trace_ids"), field_name="selection.trace_ids")
    job_ids = _normalize_string_list(selection.get("job_ids"), field_name="selection.job_ids")
    replay_ids = _normalize_string_list(selection.get("replay_ids"), field_name="selection.replay_ids")
    selection_policy = _require_string(selection.get("policy_snapshot_version", policy_snapshot_version), field_name="selection.policy_snapshot_version")
    selection_tenant = _require_string(selection.get("tenant_id", tenant_id), field_name="selection.tenant_id")
    selection_project = _require_string(selection.get("project_id", project_id), field_name="selection.project_id")
    if selection_tenant != tenant_id or selection_project != project_id:
        raise ProductionTraceTrainingError("selection must remain tenant-scoped")
    if selection_policy != policy_snapshot_version:
        raise ProductionTraceTrainingError("selection policy snapshot version must match the bundle")
    if selected_by != caller_identity:
        raise ProductionTraceTrainingError("selection.selected_by must match the internal caller identity")
    return TrainingSelectionSummary(
        trace_ids=trace_ids,
        replay_ids=replay_ids,
        selection_id=selection_id,
        selected_by=selected_by,
        selection_reason=selection_reason,
    )


def _normalize_historical_compilation_approval(
    bundle: dict[str, Any],
    *,
    tenant_id: str,
    project_id: str,
    policy_snapshot_version: str,
    selection: TrainingSelectionSummary,
) -> TrainingApprovalSummary:
    approval = _require_mapping(bundle.get("approval"), field_name="approval")
    approval_id = _require_string(approval.get("approval_id"), field_name="approval.approval_id")
    approved_by = _require_string(approval.get("approved_by"), field_name="approval.approved_by")
    approved_at = _require_string(approval.get("approved_at"), field_name="approval.approved_at")
    decision = _require_string(approval.get("decision", "approved"), field_name="approval.decision")
    if decision.lower() != "approved":
        raise ProductionTraceTrainingError("approval.decision must be approved")
    approval_ticket_ref = _require_string(approval.get("ticket_ref"), field_name="approval.ticket_ref")
    approval_policy = _require_string(approval.get("policy_snapshot_version", policy_snapshot_version), field_name="approval.policy_snapshot_version")
    approval_tenant = _require_string(approval.get("tenant_id", tenant_id), field_name="approval.tenant_id")
    approval_project = _require_string(approval.get("project_id", project_id), field_name="approval.project_id")
    replay_ids = _normalize_string_list(approval.get("replay_ids") or selection.replay_ids, field_name="approval.replay_ids")
    if approval_tenant != tenant_id or approval_project != project_id:
        raise ProductionTraceTrainingError("approval must remain tenant-scoped")
    if approval_policy != policy_snapshot_version:
        raise ProductionTraceTrainingError("approval policy snapshot version must match the bundle")
    if not set(selection.replay_ids).issubset(set(replay_ids)):
        raise ProductionTraceTrainingError("approval replay_ids must cover all selected replay identifiers")
    return TrainingApprovalSummary(
        approval_id=approval_id,
        approved_by=approved_by,
        approved_at=approved_at,
        ticket_ref=approval_ticket_ref,
        decision=decision,
        policy_snapshot_version=approval_policy,
        tenant_id=approval_tenant,
        project_id=approval_project,
        replay_ids=replay_ids,
    )


def _normalize_historical_compilation_record(
    record: Any,
    *,
    idx: int,
    tenant_id: str,
    project_id: str,
    policy_snapshot_version: str,
    record_schema_version: str,
) -> dict[str, Any]:
    mapping = _require_mapping(record, field_name=f"records[{idx}]")
    record_id = _require_string(mapping.get("record_id"), field_name=f"records[{idx}].record_id")
    schema_version = _require_string(mapping.get("schema_version"), field_name=f"records[{idx}].schema_version")
    if schema_version != record_schema_version:
        raise ProductionTraceTrainingError(f"records[{idx}].schema_version must match the bundle record_schema_version")
    job_id = _require_string(mapping.get("job_id"), field_name=f"records[{idx}].job_id")
    trace_id = _require_string(mapping.get("trace_id"), field_name=f"records[{idx}].trace_id")
    replay_id = _require_string(mapping.get("replay_id"), field_name=f"records[{idx}].replay_id")
    request_id = _require_string(mapping.get("request_id"), field_name=f"records[{idx}].request_id")
    record_tenant = _require_string(mapping.get("tenant_id", tenant_id), field_name=f"records[{idx}].tenant_id")
    record_project = _require_string(mapping.get("project_id", project_id), field_name=f"records[{idx}].project_id")
    record_policy = _require_string(mapping.get("policy_snapshot_version", policy_snapshot_version), field_name=f"records[{idx}].policy_snapshot_version")
    if record_tenant != tenant_id or record_project != project_id:
        raise ProductionTraceTrainingError(f"records[{idx}] must remain tenant-scoped")
    if record_policy != policy_snapshot_version:
        raise ProductionTraceTrainingError(f"records[{idx}].policy_snapshot_version must match the bundle")
    payload = mapping.get("payload")
    if not isinstance(payload, (dict, list, str, int, float, bool)):
        raise ProductionTraceTrainingError(f"records[{idx}].payload must be JSON-serializable")
    if not _is_redacted_payload(payload):
        raise ProductionTraceTrainingError(f"records[{idx}] must be redacted before ingestion")
    if not isinstance(payload, dict):
        raise ProductionTraceTrainingError(f"records[{idx}].payload must be an object for historical compilation corpora")
    compiler_status = _require_string(payload.get("compiler_status"), field_name=f"records[{idx}].payload.compiler_status")
    rewrite_outcome = _require_string(payload.get("rewrite_outcome"), field_name=f"records[{idx}].payload.rewrite_outcome")
    accepted_rewrite_ids = _normalize_string_list(payload.get("accepted_rewrite_ids"), field_name=f"records[{idx}].payload.accepted_rewrite_ids", allow_empty=True)
    rejected_rewrite_ids = _normalize_string_list(payload.get("rejected_rewrite_ids"), field_name=f"records[{idx}].payload.rejected_rewrite_ids", allow_empty=True)
    timing_ms = payload.get("timing_ms")
    if timing_ms is None:
        timing_ms = payload.get("stage_timings_ms")
    if timing_ms is None:
        timing_ms = payload.get("timings_ms")
    if timing_ms is None:
        raise ProductionTraceTrainingError(f"records[{idx}].payload.timing_ms is required")
    final_aqo = payload.get("final_aqo")
    if final_aqo is None:
        final_aqo = payload.get("final_aqo_json")
    if final_aqo is None:
        raise ProductionTraceTrainingError(f"records[{idx}].payload.final_aqo is required")
    final_aqo_sha256 = _hex_digest(_stable_json(final_aqo).encode("utf-8"))
    content_payload = dict(payload)
    content_payload["accepted_rewrite_ids"] = list(accepted_rewrite_ids)
    content_payload["rejected_rewrite_ids"] = list(rejected_rewrite_ids)
    content_payload["timing_ms"] = _normalize_numeric_tree(timing_ms)
    content_payload["final_aqo"] = final_aqo
    content_payload["compiler_status"] = compiler_status
    content_payload["rewrite_outcome"] = rewrite_outcome
    content_digest_sha256 = _hex_digest(_stable_json(content_payload).encode("utf-8"))
    provenance = _normalize_record_provenance(mapping.get("provenance"), field_name=f"records[{idx}].provenance")
    redaction = _normalize_redaction(mapping.get("redaction"), field_name=f"records[{idx}].redaction")
    return {
        "record_id": record_id,
        "schema_version": schema_version,
        "job_id": job_id,
        "trace_id": trace_id,
        "replay_id": replay_id,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "policy_snapshot_version": policy_snapshot_version,
        "source_kind": "historical_compilation",
        "content_digest_sha256": content_digest_sha256,
        "payload": content_payload,
        "provenance": provenance,
        "redaction": redaction,
        "trace_ref": f"nsc://trace/{trace_id}",
        "replay_ref": f"nsc://replay/{trace_id}/{replay_id}",
    }


def prepare_historical_compilation_training_manifest(bundle: dict[str, Any], *, caller_identity: str) -> dict[str, Any]:
    schema_version = _require_string(bundle.get("schema_version"), field_name="schema_version")
    if schema_version != _HISTORICAL_COMPILATION_BUNDLE_SCHEMA:
        raise ProductionTraceTrainingError("unsupported historical compilation bundle schema")
    contract_version = _require_string(bundle.get("contract_version", _CONTRACT_VERSION), field_name="contract_version")
    dataset_id = _require_string(bundle.get("dataset_id"), field_name="dataset_id")
    dataset_version = _require_string(bundle.get("dataset_version"), field_name="dataset_version")
    record_schema_version = _require_string(bundle.get("record_schema_version", _HISTORICAL_COMPILATION_RECORD_SCHEMA), field_name="record_schema_version")
    tenant_id = _require_string(bundle.get("tenant_id"), field_name="tenant_id")
    project_id = _require_string(bundle.get("project_id"), field_name="project_id")
    policy_snapshot_version = _require_string(bundle.get("policy_snapshot_version"), field_name="policy_snapshot_version")

    ownership = _require_mapping(bundle.get("ownership"), field_name="ownership")
    service_identity = _require_string(ownership.get("service_identity"), field_name="ownership.service_identity")
    requested_by = _require_string(ownership.get("requested_by", caller_identity), field_name="ownership.requested_by")
    service_role = _require_string(ownership.get("service_role", "internal-ingest"), field_name="ownership.service_role")
    if service_identity != caller_identity or requested_by != caller_identity:
        raise ProductionTraceTrainingError("ownership must resolve to the internal caller identity")

    selection = _normalize_historical_compilation_selection(
        bundle,
        caller_identity=caller_identity,
        tenant_id=tenant_id,
        project_id=project_id,
        policy_snapshot_version=policy_snapshot_version,
    )
    approval = _normalize_historical_compilation_approval(
        bundle,
        tenant_id=tenant_id,
        project_id=project_id,
        policy_snapshot_version=policy_snapshot_version,
        selection=selection,
    )
    provenance = _normalize_provenance(bundle.get("provenance"), field_name="provenance")
    redaction = _normalize_redaction(bundle.get("redaction"), field_name="redaction")

    records = bundle.get("records")
    if not isinstance(records, list) or not records:
        raise ProductionTraceTrainingError("records must be a non-empty list")

    normalized_records = [
        _normalize_historical_compilation_record(
            record,
            idx=idx,
            tenant_id=tenant_id,
            project_id=project_id,
            policy_snapshot_version=policy_snapshot_version,
            record_schema_version=record_schema_version,
        )
        for idx, record in enumerate(records)
    ]
    normalized_records.sort(key=lambda item: (item["trace_id"], item["job_id"], item["record_id"], item["replay_id"]))

    record_digests = [record["content_digest_sha256"] for record in normalized_records]
    trace_ids = [record["trace_id"] for record in normalized_records]
    job_ids = [record["job_id"] for record in normalized_records]
    replay_ids = [record["replay_id"] for record in normalized_records]
    if tuple(trace_ids) != selection.trace_ids:
        raise ProductionTraceTrainingError("selection.trace_ids must match the selected records")
    if tuple(job_ids) != tuple(_normalize_string_list(bundle.get("selection", {}).get("job_ids"), field_name="selection.job_ids")):
        raise ProductionTraceTrainingError("selection.job_ids must match the selected records")
    if tuple(replay_ids) != selection.replay_ids:
        raise ProductionTraceTrainingError("selection.replay_ids must match the selected records")

    normalized_manifest = {
        "schema_version": _TRAINING_DATASET_MANIFEST_SCHEMA,
        "contract_version": contract_version,
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "record_schema_version": record_schema_version,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "policy_snapshot_version": policy_snapshot_version,
        "source_kind": "historical_compilations",
        "ownership": {
            "service_identity": service_identity,
            "requested_by": requested_by,
            "service_role": service_role,
        },
        "selection": {
            "selection_id": selection.selection_id,
            "selected_by": selection.selected_by,
            "selection_reason": selection.selection_reason,
            "job_ids": list(job_ids),
            "trace_ids": list(trace_ids),
            "replay_ids": list(replay_ids),
            "tenant_id": tenant_id,
            "project_id": project_id,
            "policy_snapshot_version": policy_snapshot_version,
        },
        "approval": {
            "approval_id": approval.approval_id,
            "approved_by": approval.approved_by,
            "approved_at": approval.approved_at,
            "decision": approval.decision,
            "ticket_ref": approval.ticket_ref,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "policy_snapshot_version": policy_snapshot_version,
            "replay_ids": list(approval.replay_ids),
        },
        "provenance": provenance,
        "redaction": redaction,
        "records": normalized_records,
    }

    normalized_manifest["manifest_digest_sha256"] = _hex_digest(_stable_json(normalized_manifest).encode("utf-8"))
    dataset_digest_source = {
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "policy_snapshot_version": policy_snapshot_version,
        "ownership": normalized_manifest["ownership"],
        "selection": normalized_manifest["selection"],
        "approval": normalized_manifest["approval"],
        "provenance": provenance,
        "redaction": redaction,
        "record_digests": record_digests,
        "job_ids": job_ids,
        "trace_ids": trace_ids,
        "replay_ids": replay_ids,
    }
    return normalized_manifest
