"""Knowledge Base public service and ingestion helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from .errors import FieldViolation, PublicErrorSpec, abort_invalid_argument, abort_public, abort_with_error_info
from .observability import (
    append_security_audit_event,
    record_kb_contract_marker,
    record_kb_fallback,
    record_kb_query,
    record_kb_replay_failure,
    sanitized_security_metadata,
    trace_id_from_traceparent,
)
from .security import auth_context, enforce_authn, enforce_authz, enforce_sandbox_policy, load_policy_snapshot, security_context

_KB_CONTRACT_VERSION = "1.0.0"
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")

_SENSITIVE_KEYS = {
    "actor_id",
    "client_ip",
    "email",
    "project_id",
    "request_hash",
    "request_id",
    "subject",
    "tenant_id",
    "user_id",
}

_DEFAULT_STORAGE_MODE = "memory"
_DEFAULT_RETENTION_SECONDS = 60 * 60 * 24 * 90
_DEFAULT_ANON_SALT = "eigen-kb-anon-salt"
_DEFAULT_ANON_EPOCH = "1"
_OKB_QUERY_MODES = {"structural", "vector"}
_OKB_MAX_CANDIDATES = 8
_LEARNING_DEFAULT_TRIGGER_MIN_RECORDS = 1000
_LEARNING_DEFAULT_TRIGGER_MIN_RUNTIME_DECISIONS = 10
_LEARNING_DEFAULT_TRIGGER_MIN_BENCHMARK_RUNS = 3
_LEARNING_DEFAULT_RETENTION_DAYS = 90
_LEARNING_ALLOWED_STATES = ("DRAFT", "TRAINED", "VALIDATED", "SHADOW", "CANARY", "PROMOTED", "RETIRED")
_LEARNING_ALLOWED_TRANSITIONS = {
    "DRAFT": ("TRAINED", "RETIRED"),
    "TRAINED": ("VALIDATED", "RETIRED"),
    "VALIDATED": ("SHADOW", "RETIRED"),
    "SHADOW": ("CANARY", "RETIRED"),
    "CANARY": ("PROMOTED", "ROLLBACK_TO_VALIDATED", "RETIRED"),
    "PROMOTED": ("ROLLBACK_TO_VALIDATED", "RETIRED"),
    "RETIRED": (),
}
_LEARNING_QUARANTINE_KEYS = {"user_id", "client_ip", "email", "subject", "raw_payload", "unredacted_payload"}
_LEARNING_QUERY_KINDS = {"optimizer", "runtime", "benchmark", "control_plane_command"}

_INDEX_STATUS_READY = "ready"
_INDEX_STATUS_REBUILDING = "rebuilding"
_INDEX_STATUS_DEGRADED = "degraded"
_INDEX_STATUS_UNAVAILABLE = "unavailable"
_OKB_INDEX_MODES = ("structural", "vector")


class KnowledgeBaseUnavailable(RuntimeError):
    """Raised when the KB backend is disabled or unavailable."""


@dataclass(slots=True)
class _StoredRecord:
    record: Any
    tenant_id: str
    project_id: str
    capability_scope: Sequence[str]
    created_at: datetime
    updated_at: datetime
    fingerprint: str
    sequence: int


@dataclass(slots=True)
class _StoredDecisionLog:
    decision_log: Any
    tenant_id: str
    project_id: str
    capability_scope: Sequence[str]
    decided_at: datetime
    fingerprint: str
    sequence: int


@dataclass(slots=True)
class _StoredLearningEvidence:
    evidence_id: str
    tenant_id: str
    project_id: str
    evidence_kind: str
    evidence_hash: str
    model_version: str
    training_set_hash: str
    evaluation_bundle_hash: str
    promotion_policy_version: str
    lifecycle_state: str
    quarantine_state: str
    source: str
    command: str
    decision: str
    gate_results: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    queryable_ref: str


@dataclass(slots=True)
class _OptimizationCandidate:
    candidate_id: str
    candidate_source: str
    optimization_type: str
    transformation_ref: str
    provenance_ref: str
    compatibility_window: str
    deterministic_digest: str
    explanation_ref: str
    selection_reason: str
    confidence: float
    structural_score: float
    vector_score: float
    score_total: float
    selected: bool
    metadata: dict[str, str]


@dataclass(slots=True)
class _IndexState:
    name: str
    status: str
    source_revision: int
    source_fingerprint: str
    scope_entries: dict[str, list[str]]
    scope_fingerprints: dict[str, str]
    scope_counts: dict[str, int]
    built_at: datetime | None
    backfilled_at: datetime | None
    recovered_at: datetime | None
    last_error: str


def _metadata(context: grpc.ServicerContext) -> dict[str, str]:
    return {
        k.lower(): (v.decode("utf-8") if isinstance(v, bytes) else str(v))
        for k, v in (context.invocation_metadata() or [])
    }


def _now_ts() -> Timestamp:
    ts = Timestamp()
    ts.FromDatetime(datetime.now(timezone.utc))
    return ts


def _ts_to_dt(ts: Timestamp | None) -> datetime:
    if ts is None:
        return datetime.now(timezone.utc)
    try:
        dt = ts.ToDatetime()
    except Exception:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _stable_json(payload: Any) -> str:
    def _normalize(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): _normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [_normalize(item) for item in value]
        if isinstance(value, Timestamp):
            return _ts_to_dt(value).isoformat()
        if isinstance(value, datetime):
            dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        return value

    return json.dumps(_normalize(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_hash(payload: Any) -> str:
    return f"sha256:{hashlib.sha256(_stable_json(payload).encode('utf-8')).hexdigest()}"


def _stable_request_id(request: Any) -> str:
    raw = request.SerializeToString(deterministic=True)
    return f"req_{hashlib.sha256(raw).hexdigest()[:24]}"


def _anon_token(*, salt: str, epoch: str, value: str) -> str:
    digest = hmac.new(salt.encode('utf-8'), f"{epoch}:{value}".encode('utf-8'), hashlib.sha256).hexdigest()[:32]
    return f"anon:{epoch}:{digest}"


def _anonymize_value(key: str, value: Any, *, salt: str, epoch: str) -> Any:
    if isinstance(value, dict):
        return {k: _anonymize_value(str(k), v, salt=salt, epoch=epoch) for k, v in value.items()}
    if isinstance(value, list):
        return [_anonymize_value(key, item, salt=salt, epoch=epoch) for item in value]
    if isinstance(value, str) and key.strip().lower() in _SENSITIVE_KEYS:
        return _anon_token(salt=salt, epoch=epoch, value=value)
    return value


def _anonymize_mapping(payload: dict[str, Any], *, salt: str, epoch: str) -> dict[str, Any]:
    return {key: _anonymize_value(key, value, salt=salt, epoch=epoch) for key, value in payload.items()}


def _explainability_envelope_from_payload(payload: dict[str, Any], *, salt: str, epoch: str) -> dict[str, Any]:
    raw_envelope = payload.get("explainability_envelope")
    if isinstance(raw_envelope, dict) and raw_envelope:
        envelope = dict(raw_envelope)
    else:
        envelope = {
            "contract_version": str(payload.get("contract_version", "")).strip() or _KB_CONTRACT_VERSION,
            "model_version": str(payload.get("model_version", "")).strip(),
            "feature_set": payload.get("feature_set") if isinstance(payload.get("feature_set"), dict) else {},
            "confidence": payload.get("confidence", 0.0),
            "retrieval_references": payload.get("retrieval_references") or [],
            "replay_digest": str(payload.get("replay_digest", "")).strip(),
            "decision_digest": str(payload.get("decision_digest", "")).strip(),
            "policy_snapshot_version": str(payload.get("policy_snapshot_version", "")).strip(),
        }

    feature_set = envelope.get("feature_set")
    if isinstance(feature_set, dict):
        normalized_feature_set = _anonymize_mapping(dict(feature_set), salt=salt, epoch=epoch)
    elif feature_set:
        normalized_feature_set = {"value": str(feature_set)}
    else:
        normalized_feature_set = {}

    retrieval_references = envelope.get("retrieval_references")
    if isinstance(retrieval_references, (list, tuple, set)):
        normalized_retrieval_references = [str(ref).strip() for ref in retrieval_references if str(ref).strip()]
    elif retrieval_references:
        normalized_retrieval_references = [str(retrieval_references).strip()]
    else:
        normalized_retrieval_references = []

    confidence = envelope.get("confidence", 0.0)
    try:
        confidence_value = round(float(confidence), 6)
    except (TypeError, ValueError):
        confidence_value = 0.0

    return {
        "contract_version": str(envelope.get("contract_version", "")).strip() or _KB_CONTRACT_VERSION,
        "model_version": str(envelope.get("model_version", "")).strip(),
        "feature_set": normalized_feature_set,
        "confidence": confidence_value,
        "retrieval_references": normalized_retrieval_references,
        "retrieval_reference_count": len(normalized_retrieval_references),
        "replay_digest": str(envelope.get("replay_digest", "")).strip(),
        "decision_digest": str(envelope.get("decision_digest") or envelope.get("replay_digest") or "").strip(),
        "policy_snapshot_version": str(envelope.get("policy_snapshot_version", "")).strip(),
    }


def _copy_timestamp(ts: Timestamp | None) -> Timestamp:
    if ts is None:
        return _now_ts()
    out = Timestamp()
    out.CopyFrom(ts)
    return out


def _contract_version_from_envelope(envelope: Any) -> str:
    contract_version = (
        getattr(envelope, "contract_version", "")
        or getattr(getattr(envelope, "request", None), "contract_version", "")
        or _KB_CONTRACT_VERSION
    ).strip()
    return contract_version if _SEMVER_RE.match(contract_version) else ""


def _parse_iso_datetime(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except Exception:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _capability_tokens_from_value(value: Any) -> set[str]:
    tokens: set[str] = set()
    if value is None:
        return tokens
    if isinstance(value, dict):
        for key, item in sorted(value.items(), key=lambda kv: str(kv[0])):
            key_text = str(key).strip().lower()
            if not key_text:
                continue
            if isinstance(item, dict):
                nested = _stable_json(item).strip().lower()
                if nested:
                    tokens.add(f"{key_text}={nested}")
                else:
                    tokens.add(key_text)
                continue
            if isinstance(item, (list, tuple, set)):
                nested_tokens = sorted({str(entry).strip().lower() for entry in item if str(entry).strip()})
                if nested_tokens:
                    nested = ",".join(nested_tokens)
                    tokens.add(f"{key_text}={nested}")
                    tokens.add(nested)
                else:
                    tokens.add(key_text)
                continue
            item_text = str(item).strip().lower()
            if item_text:
                tokens.add(f"{key_text}={item_text}")
                tokens.add(item_text)
            else:
                tokens.add(key_text)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            tokens.update(_capability_tokens_from_value(item))
    else:
        text = str(value).strip().lower()
        if text:
            for part in re.split(r"[,\s]+", text):
                part = part.strip().lower()
                if part:
                    tokens.add(part)
    return tokens


def _capability_scope_tokens(payload: dict[str, Any] | None) -> Sequence[str]:
    if not payload:
        return ()
    tokens: set[str] = set()
    for key in ("capability_scope", "capability_tags", "capabilities"):
        tokens.update(_capability_tokens_from_value(payload.get(key)))
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        for key in ("capability_scope", "capability_tags", "capabilities"):
            tokens.update(_capability_tokens_from_value(metadata.get(key)))
    for key in ("backend_profile_id", "backend_profile"):
        token = str(payload.get(key, "")).strip().lower()
        if token:
            tokens.add(token)
            tokens.add(f"backend_profile={token}")
            break
    return tuple(sorted(tokens))


def _capability_scope_matches(stored_scope: Sequence[str], requested_scope: Sequence[str]) -> bool:
    if not requested_scope:
        return True
    return tuple(stored_scope) == tuple(requested_scope)


from collections.abc import Sequence
from typing import Any


def _okb_filter_scope_tokens(
    scope: Any,
    backend_profile_id: str,
) -> Sequence[str]:
    """
    Normalize scope for OKB matching.

    Backend profile is used for scoring/routing, but it should not narrow the
    capability filter itself. Otherwise queries without explicit capability tags
    can be filtered down to zero candidates.
    """

    if not scope:
        return ()

    backend_profile_id = str(backend_profile_id).strip().lower()
    routing_tokens = (
        {backend_profile_id, f"backend_profile={backend_profile_id}"}
        if backend_profile_id
        else set()
    )

    items = (scope,) if isinstance(scope, str) else tuple(scope)

    normalized: list[str] = []
    for token in items:
        value = str(token).strip().lower()
        if not value or value in routing_tokens:
            continue
        normalized.append(value)

    return tuple(sorted(dict.fromkeys(normalized)))

class KnowledgeBaseService:
    """Deterministic in-memory KnowledgeBaseService implementation."""

    def __init__(
        self,
        kb_pb,
        types_pb,
        *,
        storage_mode: str | None = None,
        retention_seconds: int | None = None,
    ) -> None:
        self._kb_pb = kb_pb
        self._types_pb = types_pb
        self._storage_mode = (storage_mode or os.getenv("SYSTEM_API_KB_STORAGE_MODE", _DEFAULT_STORAGE_MODE)).strip().lower()
        raw_retention = retention_seconds if retention_seconds is not None else os.getenv("SYSTEM_API_KB_RETENTION_SECONDS", str(_DEFAULT_RETENTION_SECONDS))
        self._retention_seconds = max(int(raw_retention), 1)
        self._anon_salt = os.getenv("SYSTEM_API_KB_ANON_SALT", _DEFAULT_ANON_SALT)
        self._anon_epoch = os.getenv("SYSTEM_API_KB_ANON_SALT_EPOCH", _DEFAULT_ANON_EPOCH).strip() or _DEFAULT_ANON_EPOCH
        self._lock = threading.RLock()
        self._records: dict[str, _StoredRecord] = {}
        self._decision_logs: list[_StoredDecisionLog] = []
        self._learning_evidence: list[dict[str, Any]] = []
        self._learning_models: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._learning_datasets: dict[str, dict[str, Any]] = {}
        self._learning_command_index: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
        self._sequence = 0
        self._okb_indexes: dict[str, _IndexState] = {
            mode: self._new_index_state(mode) for mode in _OKB_INDEX_MODES
        }
        self._okb_restart_count = 0

    # Public RPC methods -------------------------------------------------

    def UpsertRecord(self, request, context: grpc.ServicerContext):
        self._require_write(context, operation="upsert_record")
        envelope = self._normalize_envelope(request.envelope, context)
        record = self._validate_record(request.record, context)
        with self._lock:
            self._gc_locked()
            result = self._upsert_record(
                record=record,
                envelope=envelope,
                allow_overwrite=bool(request.allow_overwrite),
                anonymize_attributes=True,
                source="rpc",
                replay_bundle_ref=self._replay_bundle_ref(record.record_id),
                context=context,
            )
        record_kb_contract_marker(envelope["contract_version"], "accepted")
        return self._kb_pb.UpsertRecordResponse(record_id=result["record_id"], created=result["created"], updated_at=result["updated_at"])

    def BatchUpsertRecords(self, request, context: grpc.ServicerContext):
        self._require_write(context, operation="batch_upsert_records")
        envelope = self._normalize_envelope(request.envelope, context)
        accepted = 0
        rejected = 0
        errors = []
        with self._lock:
            self._gc_locked()
            for record in request.records:
                if self._record_violations(record):
                    rejected += 1
                    errors.append(self._make_error("KB_INVALID_ARGUMENT", "record validation failed", "NEVER"))
                    continue
                try:
                    self._upsert_record(
                        record=record,
                        envelope=envelope,
                        allow_overwrite=bool(request.allow_overwrite),
                        anonymize_attributes=True,
                        source="rpc",
                        replay_bundle_ref=self._replay_bundle_ref(record.record_id),
                        context=context,
                    )
                except grpc.RpcError:
                    raise
                except Exception as exc:
                    rejected += 1
                    errors.append(self._make_error("KB_INTERNAL", str(exc), "SAFE_RETRY"))
                else:
                    accepted += 1
        record_kb_contract_marker(envelope["contract_version"], "accepted" if accepted else "error")
        return self._kb_pb.BatchUpsertRecordsResponse(accepted=accepted, rejected=rejected, errors=errors)

    def QueryRecords(self, request, context: grpc.ServicerContext):
        self._require_read(context, operation="query_records")
        envelope = self._normalize_envelope(request.envelope, context)
        sec_ctx, policy_version = self._retrieval_security_context(context, operation="query_records")
        page_size = self._page_size(request.page_size)
        with self._lock:
            self._gc_locked()
            filtered = [entry.record for entry in self._records.values() if self._record_visible_to_tenant(entry, envelope["tenant_id"], envelope["project_id"], context) and self._record_matches_filter(entry.record, request.filter)]
            filtered.sort(key=lambda item: (self._ts_signature(item.created_at), item.record_id))
            offset, query_sig = self._decode_cursor(request.page_token, envelope, self._filter_signature(request.filter), kind="records", context=context)
            next_offset = offset + page_size
            window = filtered[offset:next_offset]
            next_token = self._encode_cursor(envelope=envelope, filter_payload=self._filter_signature(request.filter), kind="records", offset=next_offset, query_sig=query_sig, more=next_offset < len(filtered))
        self._audit_retrieval_decision(
            context=context,
            sec_ctx=sec_ctx,
            policy_version=policy_version,
            operation="query_records",
            decision="allow" if window else "allow",
            reason="KB_QUERY_HIT" if window else "KB_QUERY_EMPTY",
            result_count=len(window),
            hit=bool(window),
            resource_name=f"{envelope['tenant_id']}/{envelope['project_id']}",
        )
        record_kb_query("records", hit=bool(window))
        return self._kb_pb.QueryRecordsResponse(records=window, next_page_token=next_token)

    def GetRecord(self, request, context: grpc.ServicerContext):
        self._require_read(context, operation="get_record")
        envelope = self._normalize_envelope(request.envelope, context)
        sec_ctx, policy_version = self._retrieval_security_context(context, operation="get_record")
        with self._lock:
            self._gc_locked()
            entry = self._records.get(request.record_id)
            if entry is None or not self._record_visible_to_tenant(entry, envelope["tenant_id"], envelope["project_id"], context):
                self._audit_retrieval_decision(
                    context=context,
                    sec_ctx=sec_ctx,
                    policy_version=policy_version,
                    operation="get_record",
                    decision="deny",
                    reason="KB_RECORD_NOT_FOUND",
                    hit=False,
                    resource_name=request.record_id,
                )
                record_kb_query("records", hit=False)
                self._abort_not_found(context, request.record_id)
                return self._kb_pb.GetRecordResponse()
            self._audit_retrieval_decision(
                context=context,
                sec_ctx=sec_ctx,
                policy_version=policy_version,
                operation="get_record",
                decision="allow",
                reason="KB_RECORD_FOUND",
                hit=True,
                resource_name=request.record_id,
            )
            record_kb_query("records", hit=True)
            return self._kb_pb.GetRecordResponse(record=self._clone_record(entry.record))

    def AppendDecisionLog(self, request, context: grpc.ServicerContext):
        self._require_write(context, operation="append_decision_log")
        envelope = self._normalize_envelope(request.envelope, context)
        self._validate_decision_log(request.decision_log, context)
        with self._lock:
            self._gc_locked()
            stored = self._store_decision_log(decision_log=request.decision_log, envelope=envelope, context=context)
        record_kb_contract_marker(envelope["contract_version"], "accepted")
        return self._kb_pb.AppendDecisionLogResponse(decision_id=stored.decision_log.decision_id, appended_at=_copy_timestamp(stored.decision_log.decided_at))

    def QueryDecisionLogs(self, request, context: grpc.ServicerContext):
        self._require_read(context, operation="query_decision_logs")
        envelope = self._normalize_envelope(request.envelope, context)
        sec_ctx, policy_version = self._retrieval_security_context(context, operation="query_decision_logs")
        page_size = self._page_size(request.page_size)
        with self._lock:
            self._gc_locked()
            filtered = [entry.decision_log for entry in self._decision_logs if self._decision_visible_to_tenant(entry, envelope["tenant_id"], envelope["project_id"], context) and self._decision_matches_filter(entry.decision_log, trace_id=request.trace_id, model_version=request.model_version)]
            filtered.sort(key=lambda item: (self._ts_signature(item.decided_at), item.decision_id))
            offset, query_sig = self._decode_cursor(request.page_token, envelope, {"trace_id": request.trace_id, "model_version": request.model_version}, kind="decision_logs", context=context)
            next_offset = offset + page_size
            window = filtered[offset:next_offset]
            next_token = self._encode_cursor(envelope=envelope, filter_payload={"trace_id": request.trace_id, "model_version": request.model_version}, kind="decision_logs", offset=next_offset, query_sig=query_sig, more=next_offset < len(filtered))
        self._audit_retrieval_decision(
            context=context,
            sec_ctx=sec_ctx,
            policy_version=policy_version,
            operation="query_decision_logs",
            decision="allow",
            reason="KB_QUERY_HIT" if window else "KB_QUERY_EMPTY",
            result_count=len(window),
            hit=bool(window),
            resource_name=f"{envelope['tenant_id']}/{envelope['project_id']}",
        )
        record_kb_query("decision_logs", hit=bool(window))
        return self._kb_pb.QueryDecisionLogsResponse(decision_logs=window, next_page_token=next_token)

    # Ingestion helpers --------------------------------------------------

    def query_optimization_candidates(self, payload: dict[str, Any], context: grpc.ServicerContext | None = None) -> dict[str, Any]:
        """Deterministic OKB query backend for scoped structural/vector/hybrid reuse selection."""
        if self._storage_mode == "disabled":
            raise KnowledgeBaseUnavailable("knowledge base storage unavailable")

        query = self._normalize_okb_query(payload)
        sec_ctx, policy_version = self._retrieval_security_context(context, operation="query_optimization_candidates")
        with self._lock:
            self._gc_locked()
            self._okb_ensure_indexes_ready_locked(query["tenant_id"], query["project_id"])
            candidates = self._okb_candidate_pool(query, query["capability_scope"])
            index_status = self._describe_index_health_locked(tenant_id=query["tenant_id"], project_id=query["project_id"])

        ordered = sorted(
            candidates,
            key=lambda item: (-item.score_total, -item.confidence, item.candidate_id),
        )[: query["candidate_budget"]]

        selected_candidate_id = ordered[0].candidate_id if ordered else ""
        selected_payload = [
            {
                "candidate_id": item.candidate_id,
                "candidate_source": item.candidate_source,
                "optimization_type": item.optimization_type,
                "transformation_ref": item.transformation_ref,
                "provenance_ref": item.provenance_ref,
                "compatibility_window": item.compatibility_window,
                "deterministic_digest": item.deterministic_digest,
                "explanation_ref": item.explanation_ref,
                "selection_reason": item.selection_reason,
                "confidence": item.confidence,
                "score_breakdown": {
                    "structural_score": item.structural_score,
                    "vector_score": item.vector_score,
                    "rank_source": item.metadata["rank_source"],
                },
                "score_total": item.score_total,
                "selected": item.candidate_id == selected_candidate_id,
                "metadata": item.metadata,
            }
            for item in ordered
        ]

        digest = _stable_hash(
            {
                "query": {
                    "tenant_id": query["tenant_id"],
                    "project_id": query["project_id"],
                    "semantic_hash": query["semantic_hash"],
                    "aqo_hash": query["aqo_hash"],
                    "backend_profile_id": query["backend_profile_id"],
                    "capability_scope": list(query["capability_scope"]),
                    "topology_snapshot_digest": query["topology_snapshot_digest"],
                    "policy_envelope_digest": query["policy_envelope_digest"],
                    "kb_schema_version": query["kb_schema_version"],
                    "compiler_version": query["compiler_version"],
                    "optimizer_version": query["optimizer_version"],
                    "seed": query["seed"],
                    "query_mode": query["query_mode"],
                    "candidate_budget": query["candidate_budget"],
                    "deterministic": query["deterministic"],
                },
                "selected_candidate_id": selected_candidate_id,
                "candidate_ids": [item["candidate_id"] for item in selected_payload],
            }
        )

        return {
            "tenant_id": query["tenant_id"],
            "project_id": query["project_id"],
            "query_mode": query["query_mode"],
            "deterministic": query["deterministic"],
            "candidate_budget": query["candidate_budget"],
            "selected_candidate_id": selected_candidate_id,
            "candidates": selected_payload,
            "explanation_ref": f"qfs://jobs/{query['job_id']}/kb/explain.json" if query["job_id"] else f"kb://explain/{digest}",
            "okb_selection_digest": digest,
            "index_status": index_status,
        }

    def ingest_runtime_decision(self, payload: dict[str, Any]) -> str:
        if self._storage_mode == "disabled":
            raise KnowledgeBaseUnavailable("knowledge base storage unavailable")
        decision_log = self._kb_pb.DecisionLog()
        decision_log.decision_id = str(payload.get("decision_id") or self._decision_id(payload))
        decision_log.trace_id = str(payload.get("trace_id", "")).strip()
        decision_log.model_version = str(payload.get("model_version", "")).strip()
        decision_log.component = str(payload.get("component", "")).strip()
        decision_log.policy_branch = str(payload.get("policy_branch", "")).strip()
        decision_log.selected_action = str(payload.get("selected_action", "")).strip()
        decision_log.fallback_used = bool(payload.get("fallback_used", False))
        explainability_envelope = _explainability_envelope_from_payload(
            payload,
            salt=self._anon_salt,
            epoch=self._anon_epoch,
        )
        snapshot = _anonymize_mapping(dict(payload.get("feature_snapshot") or {}), salt=self._anon_salt, epoch=self._anon_epoch)
        snapshot["explainability_envelope"] = _stable_json(explainability_envelope)
        snapshot["feature_set"] = _stable_json(explainability_envelope["feature_set"])
        snapshot["confidence"] = f"{explainability_envelope['confidence']:.6f}"
        snapshot["retrieval_references"] = _stable_json(explainability_envelope["retrieval_references"])
        snapshot["replay_digest"] = explainability_envelope["replay_digest"]
        snapshot["policy_snapshot_version"] = explainability_envelope["policy_snapshot_version"]
        snapshot["model_version"] = explainability_envelope["model_version"] or decision_log.model_version
        for key, value in snapshot.items():
            decision_log.feature_snapshot[key] = str(value)
        decided_at = payload.get("decided_at")
        if isinstance(decided_at, Timestamp):
            decision_log.decided_at.CopyFrom(decided_at)
        elif isinstance(decided_at, datetime):
            decision_log.decided_at.FromDatetime(decided_at.astimezone(timezone.utc))
        else:
            decision_log.decided_at.CopyFrom(_now_ts())
        envelope = self._payload_envelope(payload)
        capability_scope = _capability_scope_tokens(payload)
        with self._lock:
            self._gc_locked()
            self._store_decision_log(
                decision_log=decision_log,
                envelope=envelope,
                context=None,
                capability_scope=self._capability_scope_tokens(payload),
            )
            self._learning_store_evidence(
                source="runtime",
                evidence_kind="runtime",
                envelope=envelope,
                evidence_payload={
                    "decision_id": decision_log.decision_id,
                    "trace_id": decision_log.trace_id,
                    "model_version": decision_log.model_version,
                    "component": decision_log.component,
                    "policy_branch": decision_log.policy_branch,
                    "selected_action": decision_log.selected_action,
                    "fallback_used": decision_log.fallback_used,
                    "feature_snapshot": dict(decision_log.feature_snapshot),
                    "capability_scope": list(capability_scope),
                    "decided_at": decision_log.decided_at,
                    "training_set_hash": str(payload.get("training_set_hash", "")).strip(),
                    "evaluation_bundle_hash": str(payload.get("evaluation_bundle_hash", "")).strip(),
                    "promotion_policy_version": str(payload.get("promotion_policy_version", "")).strip(),
                    "explainability_envelope": explainability_envelope,
                },
                model_version=decision_log.model_version,
                training_set_hash=str(payload.get("training_set_hash", "")).strip(),
                evaluation_bundle_hash=str(payload.get("evaluation_bundle_hash", "")).strip(),
                promotion_policy_version=str(payload.get("promotion_policy_version", "")).strip(),
                lifecycle_state="VALIDATED",
                quarantine_state="quarantine" if self._learning_payload_contains_quarantine_fields(payload) else "none",
                gate_results={
                    "fallback_used": bool(decision_log.fallback_used),
                    "trace_id": decision_log.trace_id,
                },
                metadata={
                    "component": decision_log.component,
                    "policy_branch": decision_log.policy_branch,
                    "explainability_envelope_json": _stable_json(explainability_envelope),
                },
                command="runtime_decision",
                decision=decision_log.selected_action,
            )
        record_kb_query("runtime_decisions", hit=True)
        return decision_log.decision_id

    def ingest_benchmark_run(self, payload: dict[str, Any]) -> str:
        if self._storage_mode == "disabled":
            raise KnowledgeBaseUnavailable("knowledge base storage unavailable")
        record = self._kb_pb.KnowledgeRecord()
        record.record_id = str(payload.get("record_id") or f"run:{payload['run_id']}")
        record.job_id = str(payload.get("job_id") or payload.get("run_id") or "")
        record.circuit_id = str(payload.get("circuit_id", "")).strip()
        record.artifact_ref = str(payload.get("artifact_ref", "")).strip()
        record.dataset_ref = str(payload.get("dataset_ref", "")).strip()
        record.backend_profile = str(payload.get("backend_profile", "")).strip()
        record.optimizer_version = str(payload.get("optimizer_version", "")).strip()
        record.qubit_count = int(payload.get("qubit_count", 0) or 0)
        record.entanglement_score = float(payload.get("entanglement_score", 0.0) or 0.0)
        record.noise_profile_id = str(payload.get("noise_profile_id", "")).strip()
        record.backend_class = str(payload.get("backend_class", "")).strip()
        created_at = payload.get("created_at")
        if isinstance(created_at, Timestamp):
            record.created_at.CopyFrom(created_at)
        elif isinstance(created_at, datetime):
            record.created_at.FromDatetime(created_at.astimezone(timezone.utc))
        else:
            record.created_at.CopyFrom(_now_ts())
        provenance = payload.get("provenance") or {}
        if isinstance(provenance, dict):
            record.provenance.compiler_ref = str(provenance.get("compiler_ref", "")).strip()
            record.provenance.optimizer_ref = str(provenance.get("optimizer_ref", "")).strip()
            record.provenance.runtime_ref = str(provenance.get("runtime_ref", "")).strip()
            record.provenance.checkpoint_ref = str(provenance.get("checkpoint_ref", "")).strip()
        lineage = payload.get("lineage") or {}
        if isinstance(lineage, dict):
            record.lineage.model_version = str(lineage.get("model_version", "")).strip()
            record.lineage.training_set_hash = str(lineage.get("training_set_hash", "")).strip()
            record.lineage.evaluation_bundle_hash = str(lineage.get("evaluation_bundle_hash", "")).strip()
            record.lineage.promotion_policy_version = str(lineage.get("promotion_policy_version", "")).strip()
            record.lineage.promotion_outcome = str(lineage.get("promotion_outcome", "")).strip()
        capability_scope = _capability_scope_tokens(payload)
        attrs = _anonymize_mapping(dict(payload.get("attributes") or {}), salt=self._anon_salt, epoch=self._anon_epoch)
        attrs.update(
            {
                "record_kind": "benchmark_run",
                "request_hash": str(payload.get("request_hash", "")).strip(),
                "idempotency_key": str(payload.get("idempotency_key", "")).strip(),
                "parent_run_id": str(payload.get("parent_run_id", "")).strip(),
                "run_state": str(payload.get("state", "")).strip(),
                "capability_scope": _stable_json(list(capability_scope)),
                "tenant_id": _anon_token(salt=self._anon_salt, epoch=self._anon_epoch, value=str(payload.get("tenant_id", ""))) if payload.get("tenant_id") else "",
                "project_id": _anon_token(salt=self._anon_salt, epoch=self._anon_epoch, value=str(payload.get("project_id", ""))) if payload.get("project_id") else "",
                "trace_id": str(payload.get("trace_id", "")).strip(),
                "replay_bundle_ref": str(payload.get("replay_bundle_ref") or self._replay_bundle_ref(record.record_id)).strip(),
            }
        )
        for key, value in attrs.items():
            record.attributes[key] = str(value)
        envelope = self._payload_envelope(payload)
        with self._lock:
            self._gc_locked()
            self._upsert_record(
                record=record,
                envelope=envelope,
                allow_overwrite=True,
                anonymize_attributes=False,
                source="benchmark",
                replay_bundle_ref=attrs["replay_bundle_ref"],
                context=None,
                capability_scope=self._capability_scope_tokens(payload),
            )

            self._learning_store_evidence(
                source="benchmark",
                evidence_kind="benchmark",
                envelope=envelope,
                evidence_payload={
                    "record_id": record.record_id,
                    "job_id": record.job_id,
                    "circuit_id": record.circuit_id,
                    "artifact_ref": record.artifact_ref,
                    "dataset_ref": record.dataset_ref,
                    "backend_profile": record.backend_profile,
                    "optimizer_version": record.optimizer_version,
                    "qubit_count": record.qubit_count,
                    "entanglement_score": record.entanglement_score,
                    "noise_profile_id": record.noise_profile_id,
                    "backend_class": record.backend_class,
                    "capability_scope": list(capability_scope),
                    "provenance": {
                        "compiler_ref": record.provenance.compiler_ref,
                        "optimizer_ref": record.provenance.optimizer_ref,
                        "runtime_ref": record.provenance.runtime_ref,
                        "checkpoint_ref": record.provenance.checkpoint_ref,
                    },
                    "lineage": {
                        "model_version": record.lineage.model_version,
                        "training_set_hash": record.lineage.training_set_hash,
                        "evaluation_bundle_hash": record.lineage.evaluation_bundle_hash,
                        "promotion_policy_version": record.lineage.promotion_policy_version,
                        "promotion_outcome": record.lineage.promotion_outcome,
                    },
                    "created_at": record.created_at,
                },
                model_version=record.lineage.model_version,
                training_set_hash=record.lineage.training_set_hash,
                evaluation_bundle_hash=record.lineage.evaluation_bundle_hash,
                promotion_policy_version=record.lineage.promotion_policy_version,
                lifecycle_state="VALIDATED",
                quarantine_state="none",
                gate_results={
                    "promotion_outcome": record.lineage.promotion_outcome,
                    "optimizer_version": record.optimizer_version,
                },
                metadata={
                    "backend_profile": record.backend_profile,
                    "backend_class": record.backend_class,
                    "noise_profile_id": record.noise_profile_id,
                },
                command="benchmark_ingest",
                decision="validated",
                capability_scope=self._capability_scope_tokens(payload),
            )
        record_kb_query("benchmark_runs", hit=True)
        return record.record_id


    def ingest_learning_evidence(self, payload: dict[str, Any]) -> str:
        if self._storage_mode == "disabled":
            raise KnowledgeBaseUnavailable("knowledge base storage unavailable")
        envelope = self._payload_envelope(payload)
        with self._lock:
            self._gc_locked()
            evidence = self._learning_store_evidence(
                source=str(payload.get("source", "manual")).strip() or "manual",
                evidence_kind=str(payload.get("evidence_kind", "learning")).strip() or "learning",
                envelope=envelope,
                evidence_payload=dict(payload),
                model_version=str(payload.get("model_version", "")).strip(),
                training_set_hash=str(payload.get("training_set_hash", "")).strip(),
                evaluation_bundle_hash=str(payload.get("evaluation_bundle_hash", "")).strip(),
                promotion_policy_version=str(payload.get("promotion_policy_version", "")).strip(),
                lifecycle_state=str(payload.get("lifecycle_state", "DRAFT")).strip() or "DRAFT",
                quarantine_state="quarantine" if self._learning_payload_contains_quarantine_fields(payload) else "none",
                gate_results=dict(payload.get("gate_results") or {}),
                metadata=dict(payload.get("metadata") or {}),
                command=str(payload.get("command", "")).strip(),
                decision=str(payload.get("decision", "")).strip(),
                capability_scope=self._capability_scope_tokens(payload),
            )
        record_kb_query("learning_evidence", hit=True)
        return evidence["evidence_id"]

    def query_learning_evidence(self, payload: dict[str, Any], context: grpc.ServicerContext | None = None) -> dict[str, Any]:
        if self._storage_mode == "disabled":
            raise KnowledgeBaseUnavailable("knowledge base storage unavailable")
        envelope = self._payload_envelope(payload)
        requested_scope = _capability_scope_tokens(payload)
        sec_ctx, policy_version = self._retrieval_security_context(context, operation="query_learning_evidence")
        page_size = self._page_size(int(payload.get("page_size", 50) or 50))
        kind_filter = str(payload.get("evidence_kind", "")).strip().lower()
        model_version = str(payload.get("model_version", "")).strip()
        lifecycle_state = str(payload.get("lifecycle_state", "")).strip().upper()
        page_token = str(payload.get("page_token", "")).strip()
        try:
            offset = max(int(page_token), 0) if page_token else 0
        except ValueError:
            offset = 0
        with self._lock:
            self._gc_locked()
            requested_scope = self._capability_scope_tokens(payload)
            filtered = [
                item
                for item in self._learning_evidence
                if item["tenant_id"] == envelope["tenant_id"]
                and item["project_id"] == envelope["project_id"]
                and (not kind_filter or item["evidence_kind"] == kind_filter)
                and (not model_version or item["model_version"] == model_version)
                and (not lifecycle_state or item["lifecycle_state"] == lifecycle_state)
                and self._capability_scope_matches(tuple(item.get("capability_scope", ())), requested_scope)
            ]
            filtered.sort(key=lambda item: (item["created_at"], item["evidence_id"]))
            window = filtered[offset : offset + page_size]
            next_page_token = str(offset + page_size) if (offset + page_size) < len(filtered) else ""
        self._audit_retrieval_decision(
            context=context,
            sec_ctx=sec_ctx,
            policy_version=policy_version,
            operation="query_learning_evidence",
            decision="allow",
            reason="KB_QUERY_HIT" if window else "KB_QUERY_EMPTY",
            result_count=len(window),
            hit=bool(window),
            resource_name=f"{envelope['tenant_id']}/{envelope['project_id']}",
        )
        record_kb_query("learning_evidence", hit=bool(window))
        return {
            "evidence": [self._learning_public_view(item) for item in window],
            "next_page_token": next_page_token,
            "total_count": len(filtered),
        }

    def assemble_learning_dataset(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._storage_mode == "disabled":
            raise KnowledgeBaseUnavailable("knowledge base storage unavailable")
        envelope = self._payload_envelope(payload)
        requested_scope = _capability_scope_tokens(payload)
        policy = self._normalize_learning_policy(payload)
        target_model_version = str(payload.get("model_version", "")).strip()
        with self._lock:
            self._gc_locked()
            requested_scope = self._capability_scope_tokens(payload)
            scoped = [
                item
                for item in self._learning_evidence
                if item["tenant_id"] == envelope["tenant_id"]
                and item["project_id"] == envelope["project_id"]
                and (not target_model_version or item["model_version"] == target_model_version)
                and self._capability_scope_matches(tuple(item.get("capability_scope", ())), requested_scope)
            ]
            runtime_decisions = [item for item in scoped if item["evidence_kind"] == "runtime"]
            benchmark_runs = [item for item in scoped if item["evidence_kind"] == "benchmark"]
            learning_evidence = [item for item in scoped if item["evidence_kind"] in {"learning", "optimizer", "runtime", "benchmark"}]
            triggered = (
                len(learning_evidence) >= policy["trigger_min_records"]
                and len(runtime_decisions) >= policy["trigger_min_runtime_decisions"]
                and len(benchmark_runs) >= policy["trigger_min_benchmark_runs"]
            )
            sorted_evidence = sorted(learning_evidence, key=lambda item: (item["created_at"], item["evidence_id"]))
            dataset_id = str(
                payload.get("dataset_id")
                or f"ds_{hashlib.sha256(_stable_json({'tenant_id': envelope['tenant_id'], 'project_id': envelope['project_id'], 'policy': policy, 'model_version': target_model_version, 'evidence_ids': [item['evidence_id'] for item in sorted_evidence]}).encode('utf-8')).hexdigest()[:24]}"
            )
            summary = {
                "dataset_id": dataset_id,
                "tenant_id": envelope["tenant_id"],
                "project_id": envelope["project_id"],
                "policy_version": policy["policy_version"],
                "model_version": target_model_version,
                "triggered": triggered,
                "assembly_state": "assembled" if triggered else "held",
                "quarantine_state": "quarantine" if any(item["quarantine_state"] != "none" for item in scoped) else "none",
                "retention_days": policy["retention_days"],
                "evidence_ids": [item["evidence_id"] for item in sorted_evidence],
                "runtime_decision_ids": [item["command"] or item["decision"] or item["evidence_id"] for item in runtime_decisions],
                "benchmark_record_ids": [item["metadata"].get("record_id", item["evidence_id"]) for item in benchmark_runs],
                "model_lineage": [
                    {
                        "model_version": item["model_version"],
                        "training_set_hash": item["training_set_hash"],
                        "evaluation_bundle_hash": item["evaluation_bundle_hash"],
                        "promotion_policy_version": item["promotion_policy_version"],
                        "lifecycle_state": item["lifecycle_state"],
                        "quarantine_state": item["quarantine_state"],
                    }
                    for item in sorted_evidence
                    if item["model_version"]
                ],
                "policy": policy,
                "queryable_ref": f"kb://datasets/{dataset_id}",
            }
            summary["dataset_hash"] = _stable_hash(summary)
            summary["evidence_hashes"] = [item["evidence_hash"] for item in sorted_evidence]
            self._learning_datasets[dataset_id] = summary
        record_kb_query("learning_datasets", hit=bool(scoped))
        return summary

    def start_training(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._storage_mode == "disabled":
            raise KnowledgeBaseUnavailable("knowledge base storage unavailable")
        envelope = self._payload_envelope(payload)
        model_version = str(payload.get("model_version", "")).strip()
        dataset_id = str(payload.get("dataset_id", "")).strip()
        policy = self._normalize_learning_policy(payload)
        if not model_version or not dataset_id:
            raise ValueError("model_version and dataset_id are required")
        with self._lock:
            self._gc_locked()
            dataset = self._learning_datasets.get(dataset_id)
            if dataset is None or dataset["tenant_id"] != envelope["tenant_id"] or dataset["project_id"] != envelope["project_id"]:
                raise KnowledgeBaseUnavailable("dataset unavailable")
            result = self._learning_transition_result(
                tenant_id=envelope["tenant_id"],
                project_id=envelope["project_id"],
                model_version=model_version,
                from_state="DRAFT",
                to_state="TRAINED",
                policy=policy,
                gate_results={"dataset_hash": dataset["dataset_hash"]},
                queryable_ref=f"kb://models/{model_version}",
                evidence_ref=dataset["queryable_ref"],
            )
        record_kb_query("learning_models", hit=True)
        return result

    def run_evaluation(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._storage_mode == "disabled":
            raise KnowledgeBaseUnavailable("knowledge base storage unavailable")
        envelope = self._payload_envelope(payload)
        model_version = str(payload.get("model_version", "")).strip()
        dataset_id = str(payload.get("dataset_id", "")).strip()
        policy = self._normalize_learning_policy(payload)
        gate_results = dict(payload.get("gate_results") or {})
        if not model_version or not dataset_id:
            raise ValueError("model_version and dataset_id are required")
        with self._lock:
            self._gc_locked()
            dataset = self._learning_datasets.get(dataset_id)
            if dataset is None or dataset["tenant_id"] != envelope["tenant_id"] or dataset["project_id"] != envelope["project_id"]:
                raise KnowledgeBaseUnavailable("dataset unavailable")
            result = self._learning_transition_result(
                tenant_id=envelope["tenant_id"],
                project_id=envelope["project_id"],
                model_version=model_version,
                from_state="TRAINED",
                to_state="VALIDATED",
                policy=policy,
                gate_results=gate_results,
                queryable_ref=f"kb://models/{model_version}",
                evidence_ref=dataset["queryable_ref"],
            )
            result["shadow_validated"] = bool(payload.get("shadow_validated", False))
            result["canary_passed"] = bool(payload.get("canary_passed", False))
        record_kb_query("learning_models", hit=True)
        return result

    def promote_model(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._storage_mode == "disabled":
            raise KnowledgeBaseUnavailable("knowledge base storage unavailable")
        envelope = self._payload_envelope(payload)
        model_version = str(payload.get("model_version", "")).strip()
        policy = self._normalize_learning_policy(payload)
        gate_results = dict(payload.get("gate_results") or {})
        if not model_version:
            raise ValueError("model_version is required")
        with self._lock:
            self._gc_locked()
            model = self._learning_models.get((envelope["tenant_id"], envelope["project_id"], model_version))
            if model is None:
                raise KnowledgeBaseUnavailable("model unavailable")
            if not bool(payload.get("shadow_validated", False)) or not bool(payload.get("canary_passed", False)):
                raise PermissionError("promotion requires shadow validation and canary pass")
            result = self._learning_transition_result(
                tenant_id=envelope["tenant_id"],
                project_id=envelope["project_id"],
                model_version=model_version,
                from_state=model["lifecycle_state"],
                to_state="PROMOTED",
                policy=policy,
                gate_results=gate_results,
                queryable_ref=model["queryable_ref"],
                evidence_ref=model["evidence_ref"],
            )
        record_kb_query("learning_models", hit=True)
        return result

    def rollback_model(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._storage_mode == "disabled":
            raise KnowledgeBaseUnavailable("knowledge base storage unavailable")
        envelope = self._payload_envelope(payload)
        model_version = str(payload.get("model_version", "")).strip()
        policy = self._normalize_learning_policy(payload)
        gate_results = dict(payload.get("gate_results") or {})
        if not model_version:
            raise ValueError("model_version is required")
        with self._lock:
            self._gc_locked()
            model = self._learning_models.get((envelope["tenant_id"], envelope["project_id"], model_version))
            if model is None:
                raise KnowledgeBaseUnavailable("model unavailable")
            result = self._learning_transition_result(
                tenant_id=envelope["tenant_id"],
                project_id=envelope["project_id"],
                model_version=model_version,
                from_state=model["lifecycle_state"],
                to_state="VALIDATED",
                policy=policy,
                gate_results=gate_results,
                queryable_ref=model["queryable_ref"],
                evidence_ref=model["evidence_ref"],
                command="ROLLBACK",
            )
            result["rollback_enabled"] = True
        record_kb_query("learning_models", hit=True)
        return result

    def get_model_lifecycle(self, payload: dict[str, Any], context: grpc.ServicerContext | None = None) -> dict[str, Any]:
        if self._storage_mode == "disabled":
            raise KnowledgeBaseUnavailable("knowledge base storage unavailable")
        scope = self._payload_envelope(payload)
        model_version = str(payload.get("model_version", "")).strip()
        if not model_version:
            raise ValueError("model_version is required")
        sec_ctx, policy_version = self._retrieval_security_context(context, operation="get_model_lifecycle")
        with self._lock:
            self._gc_locked()
            model = self._learning_models.get((scope["tenant_id"], scope["project_id"], model_version))
            if model is None:
                self._audit_retrieval_decision(
                    context=context,
                    sec_ctx=sec_ctx,
                    policy_version=policy_version,
                    operation="get_model_lifecycle",
                    decision="deny",
                    reason="KB_MODEL_NOT_FOUND",
                    hit=False,
                    resource_name=model_version,
                )
                raise KnowledgeBaseUnavailable("model unavailable")
        self._audit_retrieval_decision(
            context=context,
            sec_ctx=sec_ctx,
            policy_version=policy_version,
            operation="get_model_lifecycle",
            decision="allow",
            reason="KB_MODEL_FOUND",
            hit=True,
            resource_name=model_version,
        )
        record_kb_query("learning_models", hit=bool(model))
        return self._learning_model_view(scope, model)


    def _policy_snapshot_version(self) -> str:
        snapshot = load_policy_snapshot()
        version = str(snapshot.version).strip()
        if not version:
            raise KnowledgeBaseUnavailable("policy snapshot unavailable")
        return version

    def _retrieval_security_context(
        self,
        context: grpc.ServicerContext | None,
        *,
        operation: str,
    ) -> tuple[Any | None, str]:
        if context is None:
            return None, self._policy_snapshot_version()
        sec_ctx = security_context(context, method_name=f"KnowledgeBaseService.{operation}")
        if sec_ctx.auth_mode != "allow_all":
            enforce_sandbox_policy(context, sandbox_profile=sec_ctx.sandbox_profile)
        policy_version = sec_ctx.policy_version.strip() or self._policy_snapshot_version()
        return sec_ctx, policy_version

    def _audit_retrieval_decision(
        self,
        *,
        context: grpc.ServicerContext | None,
        sec_ctx: Any | None,
        policy_version: str,
        operation: str,
        decision: str,
        reason: str,
        hit: bool,
        resource_name: str,
        result_count: int | None = None,
    ) -> None:
        md = _metadata(context) if context is not None else {}
        traceparent = str(md.get("traceparent", ""))
        trace_id = str(md.get("trace_id", "")) or trace_id_from_traceparent(traceparent)
        subject = ""
        roles: tuple[str, ...] = ()
        auth_mode = "allow_all"
        service_identity = None
        sandbox_profile = None
        replay_marker = ""
        if sec_ctx is not None:
            subject = getattr(sec_ctx, "subject", "") or ""
            roles = tuple(getattr(sec_ctx, "roles", ()) or ())
            auth_mode = getattr(sec_ctx, "auth_mode", "allow_all") or "allow_all"
            service_identity = getattr(sec_ctx, "service_identity", None)
            sandbox_profile = getattr(sec_ctx, "sandbox_profile", None)
            replay_marker = str(getattr(sec_ctx, "claims", {}).get("replay_marker", "") or "")
        append_security_audit_event(
            {
                "method": f"KnowledgeBaseService.{operation}",
                "decision": decision,
                "reason": reason,
                "trace_id": trace_id,
                "traceparent": traceparent,
                "resource_type": "eigen.api.v1.KnowledgeBase",
                "resource_name": resource_name,
                "hit": hit,
                **({"result_count": result_count} if result_count is not None else {}),
                **sanitized_security_metadata(
                    subject=subject,
                    roles=roles,
                    auth_mode=auth_mode,
                    policy_version=policy_version,
                    service_identity=service_identity,
                    sandbox_profile=sandbox_profile,
                    replay_marker=replay_marker,
                ),
            }
        )


    def _normalize_okb_query(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = str(payload.get("tenant_id", "")).strip()
        project_id = str(payload.get("project_id", "")).strip()
        if not tenant_id or not project_id:
            raise ValueError("tenant_id and project_id are required")

        query_mode = str(payload.get("query_mode", "structural")).strip().lower() or "structural"
        if query_mode not in {"structural", "vector", "hybrid"}:
            raise ValueError("query_mode must be structural, vector, or hybrid")

        candidate_budget = max(1, min(int(payload.get("candidate_budget", 1) or 1), _OKB_MAX_CANDIDATES))
        seed = int(payload.get("seed", 0) or 0)

        return {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "job_id": str(payload.get("job_id", "")).strip(),
            "semantic_hash": str(payload.get("semantic_hash", "")).strip(),
            "aqo_hash": str(payload.get("aqo_hash", "")).strip(),
            "backend_profile_id": str(payload.get("backend_profile_id", "")).strip(),
            "capability_scope": _capability_scope_tokens(payload),
            "topology_snapshot_digest": str(payload.get("topology_snapshot_digest", "")).strip(),
            "policy_envelope_digest": str(payload.get("policy_envelope_digest", "")).strip(),
            "kb_schema_version": str(payload.get("kb_schema_version", _KB_CONTRACT_VERSION)).strip() or _KB_CONTRACT_VERSION,
            "compiler_version": str(payload.get("compiler_version", "")).strip(),
            "optimizer_version": str(payload.get("optimizer_version", "")).strip(),
            "seed": seed,
            "deterministic": bool(payload.get("deterministic", True)),
            "query_mode": query_mode,
            "candidate_budget": candidate_budget,
        }

    def _okb_candidate_pool(self, query: dict[str, Any], requested_scope: Sequence[str]) -> list[_OptimizationCandidate]:
        pool: list[_OptimizationCandidate] = []

        scope_key = self._okb_scope_key(query["tenant_id"], query["project_id"])
        backend_profile_id = str(query.get("backend_profile_id", "")).strip()
        requested_scope = _okb_filter_scope_tokens(query.get("capability_scope", ()), backend_profile_id)
        source_ids = self._okb_index_sources_for_mode_locked(query["query_mode"], scope_key)
        if not source_ids:
            source_ids = [
                *[f"record:{entry.record.record_id}" for entry in self._records.values() if entry.tenant_id == query["tenant_id"] and entry.project_id == query["project_id"]],
                *[f"decision:{entry.decision_log.decision_id}" for entry in self._decision_logs if entry.tenant_id == query["tenant_id"] and entry.project_id == query["project_id"]],
            ]

        for source_id in source_ids:
            candidate = self._okb_candidate_from_source_id(source_id, query, requested_scope)
            if candidate is not None:
                pool.append(candidate)

        return [
            candidate
            for candidate in pool
            if candidate.score_total > 0.0
            and self._capability_scope_matches(
                _okb_filter_scope_tokens(candidate.metadata.get("capability_scope", ()), backend_profile_id),
                requested_scope,
            )
        ]

    def _candidate_from_record(self, entry: _StoredRecord, query: dict[str, Any]) -> _OptimizationCandidate:
        candidate_id = f"okb-record-{entry.record.record_id}"
        compatibility_window = f"{entry.record.optimizer_version or query['optimizer_version']}::{entry.record.backend_profile or query['backend_profile_id']}"
        basis = {
            "kind": "record",
            "record_id": entry.record.record_id,
            "backend_profile": entry.record.backend_profile,
            "optimizer_version": entry.record.optimizer_version,
            "trace_id": entry.record.attributes.get("trace_id", ""),
            "lineage_model_version": getattr(getattr(entry.record, "lineage", None), "model_version", ""),
            "artifact_ref": entry.record.artifact_ref,
            "provenance_ref": entry.record.provenance.compiler_ref,
            "capability_scope": entry.capability_scope,
            "query": query,
        }
        return self._build_candidate(
            candidate_id=candidate_id,
            candidate_source="record",
            optimization_type="structural-reuse" if query["query_mode"] != "vector" else "vector-reuse",
            transformation_ref=entry.record.artifact_ref or entry.record.record_id,
            provenance_ref=entry.record.provenance.compiler_ref or entry.record.record_id,
            compatibility_window=compatibility_window,
            basis=basis,
            query=query,
            selection_reason="structural_match" if query["query_mode"] == "structural" else "vector_similarity",
            explanation_ref=f"kb://records/{entry.record.record_id}/explain",
        )

    def _candidate_from_decision_log(self, entry: _StoredDecisionLog, query: dict[str, Any]) -> _OptimizationCandidate:
        candidate_id = f"okb-decision-{entry.decision_log.decision_id}"
        compatibility_window = f"{entry.decision_log.model_version or query['optimizer_version']}::{query['backend_profile_id'] or 'any'}"
        basis = {
            "kind": "decision_log",
            "decision_id": entry.decision_log.decision_id,
            "trace_id": entry.decision_log.trace_id,
            "model_version": entry.decision_log.model_version,
            "component": entry.decision_log.component,
            "policy_branch": entry.decision_log.policy_branch,
            "selected_action": entry.decision_log.selected_action,
            "capability_scope": entry.capability_scope,
            "query": query,
        }
        return self._build_candidate(
            candidate_id=candidate_id,
            candidate_source="decision_log",
            optimization_type="decision-lineage-reuse",
            transformation_ref=entry.decision_log.selected_action or entry.decision_log.decision_id,
            provenance_ref=entry.decision_log.trace_id or entry.decision_log.decision_id,
            compatibility_window=compatibility_window,
            basis=basis,
            query=query,
            selection_reason="lineage_match" if query["query_mode"] == "structural" else "vector_similarity",
            explanation_ref=f"kb://decision-logs/{entry.decision_log.decision_id}/explain",
        )

    def _build_candidate(
        self,
        *,
        candidate_id: str,
        candidate_source: str,
        optimization_type: str,
        transformation_ref: str,
        provenance_ref: str,
        compatibility_window: str,
        basis: dict[str, Any],
        query: dict[str, Any],
        selection_reason: str,
        explanation_ref: str,
    ) -> _OptimizationCandidate:
        signature = _stable_hash(
            {
                "candidate_source": candidate_source,
                "optimization_type": optimization_type,
                "basis": basis,
                "query": {
                    "tenant_id": query["tenant_id"],
                    "project_id": query["project_id"],
                    "semantic_hash": query["semantic_hash"],
                    "aqo_hash": query["aqo_hash"],
                    "backend_profile_id": query["backend_profile_id"],
                    "capability_scope": list(query["capability_scope"]),
                    "topology_snapshot_digest": query["topology_snapshot_digest"],
                    "policy_envelope_digest": query["policy_envelope_digest"],
                    "seed": query["seed"],
                    "query_mode": query["query_mode"],
                    "deterministic": query["deterministic"],
                },
            }
        )
        score_basis = {
            key: value
            for key, value in basis.items()
            if key not in {"record_id", "decision_id"}
        }
        score_signature = _stable_hash(
            {
                "candidate_source": candidate_source,
                "optimization_type": optimization_type,
                "basis": score_basis,
                "query": {
                    "tenant_id": query["tenant_id"],
                    "project_id": query["project_id"],
                    "semantic_hash": query["semantic_hash"],
                    "aqo_hash": query["aqo_hash"],
                    "backend_profile_id": query["backend_profile_id"],
                    "capability_scope": list(query["capability_scope"]),
                    "topology_snapshot_digest": query["topology_snapshot_digest"],
                    "policy_envelope_digest": query["policy_envelope_digest"],
                    "seed": query["seed"],
                    "query_mode": query["query_mode"],
                    "deterministic": query["deterministic"],
                },
            }
        )

        structural_score = self._structural_score(basis, query, compatibility_window)
        vector_score = self._vector_score(score_signature)
        if query["query_mode"] == "vector":
            score_total = vector_score
            rank_source = "vector"
        elif query["query_mode"] == "hybrid":
            score_total = round((structural_score * 0.6) + (vector_score * 0.4), 6)
            rank_source = "hybrid"
        else:
            score_total = structural_score
            rank_source = "structural"

        confidence = round((structural_score + vector_score) / 2.0, 6)
        metadata = {
            "query_mode": query["query_mode"],
            "ranking_mode": rank_source,
            "rank_source": rank_source,
            "kb_schema_version": query["kb_schema_version"],
            "compiler_version": query["compiler_version"],
            "optimizer_version": query["optimizer_version"],
            "tenant_id": query["tenant_id"],
            "project_id": query["project_id"],
            "capability_scope": tuple(query.get("capability_scope", ())),
        }
        return _OptimizationCandidate(
            candidate_id=candidate_id,
            candidate_source=candidate_source,
            optimization_type=optimization_type,
            transformation_ref=transformation_ref,
            provenance_ref=provenance_ref,
            compatibility_window=compatibility_window,
            deterministic_digest=signature,
            explanation_ref=explanation_ref,
            selection_reason=selection_reason,
            confidence=confidence,
            structural_score=structural_score,
            vector_score=vector_score,
            score_total=score_total,
            selected=False,
            metadata=metadata,
        )

    def _structural_score(self, basis: dict[str, Any], query: dict[str, Any], compatibility_window: str) -> float:
        candidate_backend = str(
            basis.get("backend_profile")
            or basis.get("selected_action")
            or ""
        ).strip()
        candidate_optimizer = str(
            basis.get("optimizer_version")
            or basis.get("model_version")
            or ""
        ).strip()
        backend_match = 1.0 if candidate_backend and candidate_backend == query["backend_profile_id"] else 0.0
        optimizer_match = 1.0 if candidate_optimizer and candidate_optimizer == query["optimizer_version"] else 0.0
        compatibility_match = 1.0 if compatibility_window == f"{query['optimizer_version']}::{query['backend_profile_id']}" else 0.0
        return round((backend_match * 0.45) + (optimizer_match * 0.35) + (compatibility_match * 0.20), 6)

    def _vector_score(self, signature: str) -> float:
        raw = int(signature.removeprefix("sha256:")[:16], 16)
        base = raw / float(0xFFFFFFFFFFFFFFFF)
        return round(0.25 + (base * 0.75), 6)

    def _confidence_from_signature(self, signature: str, query_mode: str) -> float:
        raw = int(signature.removeprefix("sha256:")[16:32], 16)
        base = raw / float(0xFFFFFFFFFFFFFFFF)
        if query_mode == "structural":
            return round(0.60 + (base * 0.35), 6)
        return round(0.50 + (base * 0.40), 6)


    def describe_index_health(self, *, tenant_id: str | None = None, project_id: str | None = None) -> dict[str, Any]:
        """Return a deterministic health snapshot for the derived OKB indexes."""

        with self._lock:
            return self._describe_index_health_locked(tenant_id=tenant_id, project_id=project_id)

    def rebuild_indexes(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Rebuild all or one scope of the derived indexes from the primary store."""

        payload = dict(payload or {})
        tenant_id = str(payload.get("tenant_id", "")).strip() or None
        project_id = str(payload.get("project_id", "")).strip() or None
        with self._lock:
            self._gc_locked()
            return self._rebuild_indexes_locked(tenant_id=tenant_id, project_id=project_id, reason="rebuild")

    def recover_indexes(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Recover indexes after a crash or restart from the primary store of truth."""

        payload = dict(payload or {})
        tenant_id = str(payload.get("tenant_id", "")).strip() or None
        project_id = str(payload.get("project_id", "")).strip() or None
        with self._lock:
            self._gc_locked()
            return self._rebuild_indexes_locked(tenant_id=tenant_id, project_id=project_id, reason="recovery")

    def backfill_indexes(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Backfill historical primary-store records into the derived indexes."""

        payload = dict(payload or {})
        tenant_id = str(payload.get("tenant_id", "")).strip() or None
        project_id = str(payload.get("project_id", "")).strip() or None
        with self._lock:
            self._gc_locked()
            return self._rebuild_indexes_locked(tenant_id=tenant_id, project_id=project_id, reason="backfill")

    def _reset_okb_index_runtime_state(self) -> None:
        """Simulate a cold restart without mutating the primary store."""
        self._okb_indexes = {mode: self._new_index_state(mode) for mode in _OKB_INDEX_MODES}
        self._okb_restart_count += 1

    def _new_index_state(self, name: str) -> _IndexState:
        return _IndexState(
            name=name,
            status=_INDEX_STATUS_UNAVAILABLE,
            source_revision=0,
            source_fingerprint="",
            scope_entries={},
            scope_fingerprints={},
            scope_counts={},
            built_at=None,
            backfilled_at=None,
            recovered_at=None,
            last_error="",
        )

    def _okb_scope_key(self, tenant_id: str, project_id: str) -> str:
        return f"{tenant_id}::{project_id}"

    def _okb_scope_tuple(self, scope_key: str) -> tuple[str, str]:
        tenant_id, project_id = scope_key.split("::", 1)
        return tenant_id, project_id

    def _okb_scope_snapshot_locked(self, tenant_id: str, project_id: str) -> list[dict[str, Any]]:
        snapshot: list[dict[str, Any]] = []

        for entry in self._records.values():
            if entry.tenant_id != tenant_id or entry.project_id != project_id:
                continue
            snapshot.append(
                {
                    "source_id": f"record:{entry.record.record_id}",
                    "source_kind": "record",
                    "primary_id": entry.record.record_id,
                    "sequence": entry.sequence,
                    "timestamp": self._ts_signature(entry.created_at),
                    "fingerprint": entry.fingerprint,
                    "order_hint": 0,
                }
            )

        for entry in self._decision_logs:
            if entry.tenant_id != tenant_id or entry.project_id != project_id:
                continue
            snapshot.append(
                {
                    "source_id": f"decision:{entry.decision_log.decision_id}",
                    "source_kind": "decision_log",
                    "primary_id": entry.decision_log.decision_id,
                    "sequence": entry.sequence,
                    "timestamp": self._ts_signature(entry.decided_at),
                    "fingerprint": entry.fingerprint,
                    "order_hint": 1,
                }
            )

        snapshot.sort(key=lambda item: (item["order_hint"], item["timestamp"], item["primary_id"], item["sequence"]))
        return snapshot

    def _okb_scope_fingerprint_locked(self, tenant_id: str, project_id: str) -> str:
        snapshot = self._okb_scope_snapshot_locked(tenant_id, project_id)
        return _stable_hash(
            {
                "tenant_id": tenant_id,
                "project_id": project_id,
                "sources": [
                    {
                        "source_id": item["source_id"],
                        "source_kind": item["source_kind"],
                        "primary_id": item["primary_id"],
                        "sequence": item["sequence"],
                        "timestamp": item["timestamp"],
                        "fingerprint": item["fingerprint"],
                    }
                    for item in snapshot
                ],
            }
        )

    def _okb_order_scope_snapshot(self, snapshot: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
        if mode == "vector":
            return sorted(snapshot, key=lambda item: (item["fingerprint"], item["source_id"]))
        if mode == "hybrid":
            return sorted(snapshot, key=lambda item: (item["order_hint"], item["fingerprint"], item["source_id"]))
        return list(snapshot)

    def _okb_expected_scope_entries_locked(self, tenant_id: str, project_id: str, mode: str) -> list[str]:
        snapshot = self._okb_scope_snapshot_locked(tenant_id, project_id)
        return [item["source_id"] for item in self._okb_order_scope_snapshot(snapshot, mode)]

    def _okb_index_catalog_fingerprint_locked(self, shard: _IndexState) -> str:
        return _stable_hash(
            {
                "name": shard.name,
                "scope_fingerprints": [
                    {
                        "scope": scope,
                        "fingerprint": shard.scope_fingerprints.get(scope, ""),
                        "entry_count": shard.scope_counts.get(scope, 0),
                        "source_ids": shard.scope_entries.get(scope, []),
                    }
                    for scope in sorted(shard.scope_entries)
                ],
            }
        )

    def _okb_target_scopes_locked(self, tenant_id: str | None, project_id: str | None) -> list[tuple[str, str]]:
        scopes = {
            self._okb_scope_key(entry.tenant_id, entry.project_id)
            for entry in self._records.values()
        }
        scopes.update(
            self._okb_scope_key(entry.tenant_id, entry.project_id)
            for entry in self._decision_logs
        )
        if tenant_id is not None and project_id is not None:
            requested = self._okb_scope_key(tenant_id, project_id)
            return [self._okb_scope_tuple(requested)]
        return [self._okb_scope_tuple(scope) for scope in sorted(scopes)]

    def _okb_sync_index_scope_locked(self, tenant_id: str, project_id: str, *, reason: str) -> dict[str, Any]:
        scope_key = self._okb_scope_key(tenant_id, project_id)
        snapshot = self._okb_scope_snapshot_locked(tenant_id, project_id)
        scope_fingerprint = self._okb_scope_fingerprint_locked(tenant_id, project_id)
        now = datetime.now(timezone.utc)
        result = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "scope_key": scope_key,
            "source_count": len(snapshot),
            "source_fingerprint": scope_fingerprint,
            "reason": reason,
            "indices": {},
        }

        for mode in _OKB_INDEX_MODES:
            shard = self._okb_indexes[mode]
            try:
                shard.status = _INDEX_STATUS_REBUILDING
                ordered = self._okb_order_scope_snapshot(snapshot, mode)
                shard.scope_entries[scope_key] = [item["source_id"] for item in ordered]
                shard.scope_fingerprints[scope_key] = scope_fingerprint
                shard.scope_counts[scope_key] = len(ordered)
                shard.source_revision = self._sequence
                shard.source_fingerprint = self._okb_index_catalog_fingerprint_locked(shard)
                shard.last_error = ""
                if reason == "recovery":
                    shard.recovered_at = now
                elif reason == "backfill":
                    shard.backfilled_at = now
                else:
                    shard.built_at = now
                shard.status = _INDEX_STATUS_READY
                result["indices"][mode] = {
                    "status": shard.status,
                    "entry_count": shard.scope_counts[scope_key],
                    "source_fingerprint": shard.scope_fingerprints[scope_key],
                }
            except Exception as exc:  # pragma: no cover - deterministic helpers should not fail
                shard.status = _INDEX_STATUS_DEGRADED
                shard.last_error = str(exc)
                result["indices"][mode] = {
                    "status": shard.status,
                    "error": shard.last_error,
                }

        result["overall_status"] = self._okb_overall_status_locked(tenant_id=tenant_id, project_id=project_id)
        return result

    def _rebuild_indexes_locked(self, *, tenant_id: str | None, project_id: str | None, reason: str) -> dict[str, Any]:
        scopes = self._okb_target_scopes_locked(tenant_id, project_id)
        if not scopes:
            for shard in self._okb_indexes.values():
                shard.status = _INDEX_STATUS_READY
                shard.source_revision = self._sequence
                shard.source_fingerprint = self._okb_index_catalog_fingerprint_locked(shard)
            return {
                "overall_status": _INDEX_STATUS_READY,
                "scopes": [],
                "source_revision": self._sequence,
            }

        summaries = []
        for scope_tenant, scope_project in scopes:
            summaries.append(self._okb_sync_index_scope_locked(scope_tenant, scope_project, reason=reason))
        return {
            "overall_status": self._okb_overall_status_locked(tenant_id=tenant_id, project_id=project_id),
            "scopes": summaries,
            "source_revision": self._sequence,
        }

    def _okb_overall_status_locked(self, *, tenant_id: str | None, project_id: str | None) -> str:
        if self._storage_mode == "disabled":
            return _INDEX_STATUS_UNAVAILABLE

        relevant = [self._okb_indexes[mode] for mode in _OKB_INDEX_MODES]
        if any(shard.status == _INDEX_STATUS_DEGRADED for shard in relevant):
            return _INDEX_STATUS_DEGRADED
        if any(shard.status == _INDEX_STATUS_REBUILDING for shard in relevant):
            return _INDEX_STATUS_REBUILDING
        if any(shard.status == _INDEX_STATUS_UNAVAILABLE for shard in relevant):
            return _INDEX_STATUS_UNAVAILABLE

        if tenant_id is not None and project_id is not None:
            scope_key = self._okb_scope_key(tenant_id, project_id)
            for mode, shard in self._okb_indexes.items():
                expected_entries = self._okb_expected_scope_entries_locked(tenant_id, project_id, mode)
                if scope_key not in shard.scope_entries:
                    return _INDEX_STATUS_UNAVAILABLE
                if shard.scope_entries.get(scope_key, []) != expected_entries:
                    return _INDEX_STATUS_DEGRADED
            return _INDEX_STATUS_READY

        for scope_key in sorted(set().union(*(shard.scope_entries.keys() for shard in relevant))):
            tenant, project = self._okb_scope_tuple(scope_key)
            for mode, shard in self._okb_indexes.items():
                expected_entries = self._okb_expected_scope_entries_locked(tenant, project, mode)
                if shard.scope_entries.get(scope_key, []) != expected_entries:
                    return _INDEX_STATUS_DEGRADED
        return _INDEX_STATUS_READY

    def _describe_index_health_locked(self, *, tenant_id: str | None = None, project_id: str | None = None) -> dict[str, Any]:
        overall_status = self._okb_overall_status_locked(tenant_id=tenant_id, project_id=project_id)
        if tenant_id is not None and project_id is not None:
            scope_key = self._okb_scope_key(tenant_id, project_id)
            expected_by_mode = {
                mode: self._okb_expected_scope_entries_locked(tenant_id, project_id, mode)
                for mode in _OKB_INDEX_MODES
            }
            scope_present = any(scope_key in shard.scope_entries for shard in self._okb_indexes.values())
            shard_health = {
                mode: {
                    "status": shard.status,
                    "entry_count": len(shard.scope_entries.get(scope_key, [])),
                    "source_fingerprint": shard.scope_fingerprints.get(scope_key, ""),
                    "desynced": shard.scope_entries.get(scope_key, []) != expected_by_mode[mode],
                    "last_error": shard.last_error,
                    "last_built_at": self._ts_signature(shard.built_at) if shard.built_at else "",
                    "last_backfilled_at": self._ts_signature(shard.backfilled_at) if shard.backfilled_at else "",
                    "last_recovered_at": self._ts_signature(shard.recovered_at) if shard.recovered_at else "",
                }
                for mode, shard in self._okb_indexes.items()
            }
            desynced = any(item["desynced"] for item in shard_health.values())
            return {
                "overall_status": overall_status,
                "tenant_id": tenant_id,
                "project_id": project_id,
                "scope_key": scope_key,
                "scope_present": scope_present,
                "desynced": desynced,
                "source_revision": self._sequence,
                "indices": shard_health,
            }

        shard_health = {
            mode: {
                "status": shard.status,
                "scope_count": len(shard.scope_entries),
                "source_fingerprint": shard.source_fingerprint,
                "last_error": shard.last_error,
                "last_built_at": self._ts_signature(shard.built_at) if shard.built_at else "",
                "last_backfilled_at": self._ts_signature(shard.backfilled_at) if shard.backfilled_at else "",
                "last_recovered_at": self._ts_signature(shard.recovered_at) if shard.recovered_at else "",
            }
            for mode, shard in self._okb_indexes.items()
        }
        return {
            "overall_status": overall_status,
            "source_revision": self._sequence,
            "desynced": overall_status == _INDEX_STATUS_DEGRADED,
            "indices": shard_health,
        }

    def _okb_ensure_indexes_ready_locked(self, tenant_id: str, project_id: str) -> dict[str, Any]:
        health = self._describe_index_health_locked(tenant_id=tenant_id, project_id=project_id)
        if health["overall_status"] == _INDEX_STATUS_READY and not health["desynced"]:
            return health
        self._rebuild_indexes_locked(tenant_id=tenant_id, project_id=project_id, reason="recovery")
        return self._describe_index_health_locked(tenant_id=tenant_id, project_id=project_id)

    def _okb_index_sources_for_mode_locked(self, query_mode: str, scope_key: str) -> list[str]:
        structural = list(self._okb_indexes["structural"].scope_entries.get(scope_key, []))
        vector = list(self._okb_indexes["vector"].scope_entries.get(scope_key, []))
        if query_mode == "vector":
            return vector or structural
        if query_mode == "hybrid":
            merged: list[str] = []
            for source_id in structural + vector:
                if source_id not in merged:
                    merged.append(source_id)
            return merged
        return structural or vector

    def _okb_candidate_from_source_id(self, source_id: str, query: dict[str, Any], requested_scope: Sequence[str]) -> _OptimizationCandidate | None:
        backend_profile_id = str(query.get("backend_profile_id", "")).strip()
        if source_id.startswith("record:"):
            record_id = source_id.removeprefix("record:")
            entry = self._records.get(record_id)
            if entry and self._record_visible_to_tenant(entry, query["tenant_id"], query["project_id"], context=None) and _capability_scope_matches(
                _okb_filter_scope_tokens(entry.capability_scope, backend_profile_id),
                requested_scope,
            ):
                return self._candidate_from_record(entry, query)
            return None
        if source_id.startswith("decision:"):
            decision_id = source_id.removeprefix("decision:")
            for entry in self._decision_logs:
                if entry.decision_log.decision_id == decision_id and self._decision_visible_to_tenant(entry, query["tenant_id"], query["project_id"], context=None) and _capability_scope_matches(
                    _okb_filter_scope_tokens(entry.capability_scope, backend_profile_id),
                    requested_scope,
                ):
                    return self._candidate_from_decision_log(entry, query)
            return None
        return None 

    def _require_write(self, context: grpc.ServicerContext, *, operation: str) -> None:
        enforce_authn(context, method_name=f"KnowledgeBaseService.{operation}")
        enforce_authz(context, required_permission="kb:write")
        if self._storage_mode == "disabled":
            self._abort_storage_unavailable(context, operation)

    def _require_read(self, context: grpc.ServicerContext, *, operation: str) -> None:
        enforce_authn(context, method_name=f"KnowledgeBaseService.{operation}")
        enforce_authz(context, required_permission="kb:read")
        if self._storage_mode == "disabled":
            self._abort_storage_unavailable(context, operation)

    def _normalize_envelope(self, envelope: Any, context: grpc.ServicerContext) -> dict[str, Any]:
        if envelope is None or getattr(envelope, "request", None) is None:
            abort_invalid_argument(context, "validation failed", [FieldViolation(field="envelope", description="envelope and envelope.request are required")])
        contract_version = _contract_version_from_envelope(envelope)
        if not contract_version:
            abort_invalid_argument(context, "validation failed", [FieldViolation(field="envelope.contract_version", description="contract_version must be semver")])
        if contract_version != _KB_CONTRACT_VERSION:
            abort_with_error_info(context, grpc_code=grpc.StatusCode.FAILED_PRECONDITION, message=f"unsupported public contract_version: {contract_version}", reason="EIGEN_PUBLIC_CONTRACT_VERSION_UNSUPPORTED", domain="eigen.api.v1", metadata={"contract_version": contract_version, "supported_contract_version": _KB_CONTRACT_VERSION})
        request = envelope.request
        subject, roles, auth_tenant = auth_context(context)
        md = _metadata(context)
        tenant_id = (request.tenant_id or auth_tenant or "tenant-default").strip() or "tenant-default"
        project_id = (request.project_id or md.get("x-project-id") or md.get("x-eigen-project") or "project-default").strip() or "project-default"
        request_id = (request.request_id or md.get("x-request-id") or _stable_request_id(request)).strip()
        traceparent = (request.traceparent or md.get("traceparent", "")).strip()
        trace_id = trace_id_from_traceparent(traceparent) or md.get("trace_id", "")
        return {
            "contract_version": contract_version,
            "request_id": request_id,
            "traceparent": traceparent,
            "trace_id": trace_id,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "client_version": (request.client_version or md.get("x-client-version", "")).strip(),
            "subject": subject,
            "roles": roles,
        }

    def _abort_storage_unavailable(self, context: grpc.ServicerContext, operation: str) -> None:
        record_kb_fallback("storage_unavailable")
        abort_public(context, PublicErrorSpec(grpc_code=grpc.StatusCode.UNAVAILABLE, message="knowledge base storage unavailable", reason="KB_INDEX_UNAVAILABLE", retryable=True, metadata={"operation": operation, "storage_mode": self._storage_mode}, retry_delay_seconds=1, detail="Knowledge base storage is disabled or unavailable; retry the operation after recovery."))

    def _make_error(self, reason_name: str, message: str, retry_semantics: str):
        return self._kb_pb.KnowledgeBaseError(
            reason_code=getattr(self._kb_pb, f"KNOWLEDGE_BASE_REASON_CODE_{reason_name.split('_', 1)[-1]}", self._kb_pb.KNOWLEDGE_BASE_REASON_CODE_INTERNAL),
            message=message,
            retry_semantics=retry_semantics,
            details_ref="",
        )

    def _validate_record(self, record: Any, context: grpc.ServicerContext):
        if not str(getattr(record, "record_id", "")).strip():
            abort_invalid_argument(context, "validation failed", [FieldViolation(field="record.record_id", description="record_id is required")])
        clone = self._clone_record(record)
        return clone

    def _record_violations(self, record: Any) -> list[FieldViolation]:
        return [FieldViolation(field="record.record_id", description="record_id is required")] if not str(getattr(record, "record_id", "")).strip() else []

    def _validate_decision_log(self, decision_log: Any, context: grpc.ServicerContext):
        violations: list[FieldViolation] = []
        if not str(getattr(decision_log, "decision_id", "")).strip():
            violations.append(FieldViolation(field="decision_log.decision_id", description="decision_id is required"))
        if not str(getattr(decision_log, "trace_id", "")).strip():
            violations.append(FieldViolation(field="decision_log.trace_id", description="trace_id is required"))
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

    def _clone_record(self, record: Any):
        clone = self._kb_pb.KnowledgeRecord()
        clone.CopyFrom(record)
        return clone

    def _clone_decision_log(self, decision_log: Any):
        clone = self._kb_pb.DecisionLog()
        clone.CopyFrom(decision_log)
        return clone

    def _record_fingerprint(self, record: Any, *, replay_bundle_ref: str) -> str:
        payload = {
            "record_id": getattr(record, "record_id", ""),
            "job_id": getattr(record, "job_id", ""),
            "circuit_id": getattr(record, "circuit_id", ""),
            "artifact_ref": getattr(record, "artifact_ref", ""),
            "dataset_ref": getattr(record, "dataset_ref", ""),
            "backend_profile": getattr(record, "backend_profile", ""),
            "optimizer_version": getattr(record, "optimizer_version", ""),
            "qubit_count": int(getattr(record, "qubit_count", 0) or 0),
            "entanglement_score": float(getattr(record, "entanglement_score", 0.0) or 0.0),
            "noise_profile_id": getattr(record, "noise_profile_id", ""),
            "backend_class": getattr(record, "backend_class", ""),
            "provenance": {
                "compiler_ref": getattr(getattr(record, "provenance", None), "compiler_ref", ""),
                "optimizer_ref": getattr(getattr(record, "provenance", None), "optimizer_ref", ""),
                "runtime_ref": getattr(getattr(record, "provenance", None), "runtime_ref", ""),
                "checkpoint_ref": getattr(getattr(record, "provenance", None), "checkpoint_ref", ""),
            },
            "lineage": {
                "model_version": getattr(getattr(record, "lineage", None), "model_version", ""),
                "training_set_hash": getattr(getattr(record, "lineage", None), "training_set_hash", ""),
                "evaluation_bundle_hash": getattr(getattr(record, "lineage", None), "evaluation_bundle_hash", ""),
                "promotion_policy_version": getattr(getattr(record, "lineage", None), "promotion_policy_version", ""),
                "promotion_outcome": getattr(getattr(record, "lineage", None), "promotion_outcome", ""),
            },
            "attributes": {k: str(v) for k, v in sorted(dict(getattr(record, "attributes", {})).items())},
            "replay_bundle_ref": replay_bundle_ref,
            "created_at": self._ts_signature(getattr(record, "created_at", None)),
        }
        return _stable_hash(payload)

    def _decision_fingerprint(self, decision_log: Any) -> str:
        payload = {
            "decision_id": getattr(decision_log, "decision_id", ""),
            "trace_id": getattr(decision_log, "trace_id", ""),
            "model_version": getattr(decision_log, "model_version", ""),
            "component": getattr(decision_log, "component", ""),
            "policy_branch": getattr(decision_log, "policy_branch", ""),
            "selected_action": getattr(decision_log, "selected_action", ""),
            "fallback_used": bool(getattr(decision_log, "fallback_used", False)),
            "feature_snapshot": {k: str(v) for k, v in sorted(dict(getattr(decision_log, "feature_snapshot", {})).items())},
            "decided_at": self._ts_signature(getattr(decision_log, "decided_at", None)),
        }
        return _stable_hash(payload)

    def _ts_signature(self, ts: Timestamp | datetime | None) -> str:
        if ts is None:
            return ""
        if isinstance(ts, datetime):
            dt = ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        return _ts_to_dt(ts).isoformat()

    def _record_visible_to_tenant(self, entry: _StoredRecord, tenant_id: str, project_id: str, context: grpc.ServicerContext) -> bool:
        return entry.tenant_id == tenant_id and entry.project_id == project_id

    def _decision_visible_to_tenant(self, entry: _StoredDecisionLog, tenant_id: str, project_id: str, context: grpc.ServicerContext) -> bool:
        return entry.tenant_id == tenant_id and entry.project_id == project_id
    
    def _capability_scope_tokens(self, payload: dict[str, Any] | None) -> Sequence[str]:
        if not payload:
            return ()
        raw_scope = payload.get("capability_scope")
        if raw_scope in (None, ""):
            raw_scope = payload.get("capability_tags")
        if raw_scope in (None, ""):
            raw_scope = payload.get("capabilities")
        tokens: list[str] = []
        if isinstance(raw_scope, dict):
            iterable = raw_scope.keys()
        elif isinstance(raw_scope, str):
            iterable = [raw_scope]
        elif isinstance(raw_scope, (list, tuple, set)):
            iterable = raw_scope
        else:
            iterable = ()
        for item in iterable:
            token = str(item).strip().lower()
            if token and token not in tokens:
                tokens.append(token)
        return tuple(tokens)

    def _capability_scope_matches(self, stored_scope: Sequence[str], requested_scope: Sequence[str]) -> bool:
        if not requested_scope:
            return True
        if not stored_scope:
            return False
        return set(stored_scope).issubset(set(requested_scope))

    def _record_matches_filter(self, record: Any, query_filter: Any) -> bool:
        if query_filter is None:
            return True
        trace_id = str(getattr(query_filter, "trace_id", "")).strip()
        if trace_id and record.attributes.get("trace_id", "") != trace_id:
            return False
        model_version = str(getattr(query_filter, "model_version", "")).strip()
        if model_version and record.lineage.model_version != model_version:
            return False
        noise_profile_id = str(getattr(query_filter, "noise_profile_id", "")).strip()
        if noise_profile_id and record.noise_profile_id != noise_profile_id:
            return False
        backend_class = str(getattr(query_filter, "backend_class", "")).strip()
        if backend_class and record.backend_class != backend_class:
            return False
        optimizer_version = str(getattr(query_filter, "optimizer_version", "")).strip()
        if optimizer_version and record.optimizer_version != optimizer_version:
            return False
        min_qubit_count = int(getattr(query_filter, "min_qubit_count", 0) or 0)
        if min_qubit_count and record.qubit_count < min_qubit_count:
            return False
        max_qubit_count = int(getattr(query_filter, "max_qubit_count", 0) or 0)
        if max_qubit_count and record.qubit_count > max_qubit_count:
            return False
        min_entanglement_score = float(getattr(query_filter, "min_entanglement_score", 0.0) or 0.0)
        if min_entanglement_score and record.entanglement_score < min_entanglement_score:
            return False
        max_entanglement_score = float(getattr(query_filter, "max_entanglement_score", 0.0) or 0.0)
        if max_entanglement_score and record.entanglement_score > max_entanglement_score:
            return False
        if getattr(query_filter, "HasField", None):
            try:
                if query_filter.HasField("created_after") and _ts_to_dt(query_filter.created_after) >= _ts_to_dt(record.created_at):
                    return False
                if query_filter.HasField("created_before") and _ts_to_dt(query_filter.created_before) <= _ts_to_dt(record.created_at):
                    return False
            except Exception:
                return False
        return True

    def _decision_matches_filter(self, decision_log: Any, *, trace_id: str, model_version: str) -> bool:
        if trace_id and decision_log.trace_id != trace_id:
            return False
        if model_version and decision_log.model_version != model_version:
            return False
        return True

    def _page_size(self, requested: int) -> int:
        return 50 if not isinstance(requested, int) or requested <= 0 else min(requested, 100)

    def _encode_cursor(self, *, envelope: dict[str, Any], filter_payload: Any, kind: str, offset: int, query_sig: str | None, more: bool) -> str:
        if not more:
            return ""
        signature = query_sig or self._query_signature(envelope, filter_payload, kind)
        raw = f"v1:{kind}:{signature}:{offset}".encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    def _decode_cursor(self, token: str, envelope: dict[str, Any], filter_payload: Any, *, kind: str, context: grpc.ServicerContext) -> tuple[int, str]:
        signature = self._query_signature(envelope, filter_payload, kind)
        if not token:
            return 0, signature
        padded = token + "=" * (-len(token) % 4)
        try:
            raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
            version, cursor_kind, cursor_sig, offset = raw.split(":", 3)
            if version != "v1" or cursor_kind != kind or cursor_sig != signature:
                raise ValueError("cursor mismatch")
            return max(int(offset), 0), signature
        except Exception:
            record_kb_replay_failure()
            abort_with_error_info(context, grpc_code=grpc.StatusCode.INVALID_ARGUMENT, message="invalid page_token", reason="KB_INVALID_ARGUMENT", domain="eigen.api.v1", metadata={"page_token": token})
        return 0, signature

    def _query_signature(self, envelope: dict[str, Any], filter_payload: Any, kind: str) -> str:
        payload = {"kind": kind, "tenant_id": envelope["tenant_id"], "project_id": envelope["project_id"], "filter": filter_payload}
        return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()

    def _filter_signature(self, query_filter: Any) -> Any:
        if query_filter is None:
            return {}
        return {
            "trace_id": getattr(query_filter, "trace_id", ""),
            "model_version": getattr(query_filter, "model_version", ""),
            "min_qubit_count": int(getattr(query_filter, "min_qubit_count", 0) or 0),
            "max_qubit_count": int(getattr(query_filter, "max_qubit_count", 0) or 0),
            "min_entanglement_score": float(getattr(query_filter, "min_entanglement_score", 0.0) or 0.0),
            "max_entanglement_score": float(getattr(query_filter, "max_entanglement_score", 0.0) or 0.0),
            "noise_profile_id": getattr(query_filter, "noise_profile_id", ""),
            "backend_class": getattr(query_filter, "backend_class", ""),
            "optimizer_version": getattr(query_filter, "optimizer_version", ""),
            "created_after": self._ts_signature(getattr(query_filter, "created_after", None)),
            "created_before": self._ts_signature(getattr(query_filter, "created_before", None)),
        }

    def _replay_bundle_ref(self, record_id: str) -> str:
        return f"kb://replay/{record_id}"

    # Reconstructed Missing Internals -------------------------------------

    def _upsert_record(
        self,
        record: Any,
        envelope: dict[str, Any],
        allow_overwrite: bool,
        anonymize_attributes: bool,
        source: str,
        replay_bundle_ref: str,
        context: grpc.ServicerContext | None,
        capability_scope: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        record_id = record.record_id
        now = datetime.now(timezone.utc)
        existing = self._records.get(record_id)
        created_at = _ts_to_dt(record.created_at) if getattr(record, "created_at", None) else now
        if existing:
            created_at = existing.created_at

        record.created_at.FromDatetime(created_at)
        
        attrs = dict(record.attributes)
        if anonymize_attributes:
            attrs = _anonymize_mapping(attrs, salt=self._anon_salt, epoch=self._anon_epoch)

        normalized_scope = tuple(capability_scope or _capability_scope_tokens({"backend_profile": getattr(record, "backend_profile", ""), "capability_scope": attrs.get("capability_scope"), "capabilities": attrs.get("capabilities"), "capability_tags": attrs.get("capability_tags")}))
        attrs["capability_scope"] = _stable_json(list(normalized_scope)) if normalized_scope else ""
        
        fingerprint = self._record_fingerprint(record, replay_bundle_ref=replay_bundle_ref)
        attrs["request_hash"] = fingerprint
        attrs["replay_bundle_ref"] = replay_bundle_ref
        record.attributes.clear()
        record.attributes.update({k: str(v) for k, v in attrs.items()})

        if existing and not allow_overwrite:
            if existing.fingerprint == fingerprint:
                ts = Timestamp()
                ts.FromDatetime(existing.updated_at)
                return {
                    "record_id": record_id,
                    "created": False,
                    "updated_at": ts,
                }
            if context:
                abort_with_error_info(
                    context,
                    grpc_code=grpc.StatusCode.ALREADY_EXISTS,
                    message=f"Record {record_id} already exists",
                    reason="KB_RECORD_ALREADY_EXISTS",
                    domain="eigen.api.v1",
                )
                return {}
            else:
                raise ValueError(f"Record {record_id} already exists and overwrite is disabled.")

        self._sequence += 1

        stored = _StoredRecord(
            record=self._clone_record(record),
            tenant_id=envelope["tenant_id"],
            project_id=envelope["project_id"],
            capability_scope=tuple(capability_scope or self._capability_scope_tokens(dict(attrs))),
            created_at=created_at,
            updated_at=now,
            fingerprint=fingerprint,
            sequence=self._sequence,
        )
        self._records[record_id] = stored
        self._okb_sync_index_scope_locked(envelope["tenant_id"], envelope["project_id"], reason=source)

        ts = Timestamp()
        ts.FromDatetime(now)
        return {"record_id": record_id, "created": not bool(existing), "updated_at": ts}

    def _store_decision_log(self, decision_log: Any, envelope: dict[str, Any], context: grpc.ServicerContext | None, capability_scope: Sequence[str] | None = None) -> _StoredDecisionLog:
        self._sequence += 1
        decided_at = _ts_to_dt(decision_log.decided_at) if getattr(decision_log, "decided_at", None) else datetime.now(timezone.utc)
        decision_log.decided_at.FromDatetime(decided_at)
        
        normalized_scope = tuple(capability_scope or ())
        fingerprint = self._decision_fingerprint(decision_log)
        stored = _StoredDecisionLog(
            decision_log=self._clone_decision_log(decision_log),
            tenant_id=envelope["tenant_id"],
            project_id=envelope["project_id"],
            capability_scope=tuple(capability_scope or ()),
            decided_at=decided_at,
            fingerprint=fingerprint,
            sequence=self._sequence,
        )
        self._decision_logs.append(stored)
        self._okb_sync_index_scope_locked(envelope["tenant_id"], envelope["project_id"], reason="decision_log")
        return stored

    
    def _abort_not_found(self, context: grpc.ServicerContext, record_id: str) -> None:
        abort_with_error_info(
            context,
            grpc_code=grpc.StatusCode.NOT_FOUND,
            message=f"Knowledge record {record_id} not found",
            reason="KB_RECORD_NOT_FOUND",
            domain="eigen.api.v1",
        )

    def _decision_id(self, payload: dict[str, Any]) -> str:
        return f"dec_{hashlib.sha256(_stable_json(payload).encode('utf-8')).hexdigest()[:24]}"

    def _payload_envelope(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "contract_version": str(payload.get("contract_version", _KB_CONTRACT_VERSION)),
            "tenant_id": str(payload.get("tenant_id", "tenant-default")),
            "project_id": str(payload.get("project_id", "project-default")),
            "request_id": str(payload.get("request_id", "")),
            "trace_id": str(payload.get("trace_id", "")),
        }
    
    def _normalize_learning_policy(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "policy_version": str(payload.get("policy_version", "learning-policy-v1")).strip() or "learning-policy-v1",
            "trigger_min_records": max(int(payload.get("trigger_min_records", _LEARNING_DEFAULT_TRIGGER_MIN_RECORDS) or _LEARNING_DEFAULT_TRIGGER_MIN_RECORDS), 1),
            "trigger_min_runtime_decisions": max(int(payload.get("trigger_min_runtime_decisions", _LEARNING_DEFAULT_TRIGGER_MIN_RUNTIME_DECISIONS) or _LEARNING_DEFAULT_TRIGGER_MIN_RUNTIME_DECISIONS), 1),
            "trigger_min_benchmark_runs": max(int(payload.get("trigger_min_benchmark_runs", _LEARNING_DEFAULT_TRIGGER_MIN_BENCHMARK_RUNS) or _LEARNING_DEFAULT_TRIGGER_MIN_BENCHMARK_RUNS), 1),
            "retention_days": max(int(payload.get("retention_days", _LEARNING_DEFAULT_RETENTION_DAYS) or _LEARNING_DEFAULT_RETENTION_DAYS), 1),
            "quarantine_on_invalid": bool(payload.get("quarantine_on_invalid", True)),
        }


    def _gc_locked(self) -> None:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self._retention_seconds)

        before_record_count = len(self._records)
        before_decision_count = len(self._decision_logs)

        self._records = {
            key: value
            for key, value in self._records.items()
            if value.created_at >= cutoff
        }
        self._decision_logs = [
            item for item in self._decision_logs if item.decided_at >= cutoff
        ]
        self._learning_evidence = [
            item
            for item in self._learning_evidence
            if _parse_iso_datetime(item["created_at"]) >= cutoff
        ]
        self._learning_models = {
            key: value
            for key, value in self._learning_models.items()
            if _parse_iso_datetime(value["updated_at"]) >= cutoff
        }

        if len(self._records) != before_record_count or len(self._decision_logs) != before_decision_count:
            self._rebuild_indexes_locked(tenant_id=None, project_id=None, reason="gc")

    def _learning_store_evidence(
        self,
        *,
        source: str,
        evidence_kind: str,
        envelope: dict[str, Any],
        evidence_payload: dict[str, Any],
        model_version: str,
        training_set_hash: str,
        evaluation_bundle_hash: str,
        promotion_policy_version: str,
        lifecycle_state: str,
        quarantine_state: str,
        gate_results: dict[str, Any],
        metadata: dict[str, Any],
        command: str,
        decision: str,
        capability_scope: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        normalized_kind = evidence_kind.strip().lower() or "learning"
        capability_scope = tuple(_capability_scope_tokens(evidence_payload))
        evidence = {
            "tenant_id": envelope["tenant_id"],
            "project_id": envelope["project_id"],
            "capability_scope": capability_scope,
            "source": source,
            "evidence_kind": normalized_kind,
            "model_version": model_version,
            "training_set_hash": training_set_hash,
            "evaluation_bundle_hash": evaluation_bundle_hash,
            "promotion_policy_version": promotion_policy_version,
            "lifecycle_state": lifecycle_state.upper() if lifecycle_state else "DRAFT",
            "quarantine_state": quarantine_state,
            "gate_results": dict(gate_results or {}),
            "metadata": _anonymize_mapping(dict(metadata or {}), salt=self._anon_salt, epoch=self._anon_epoch),
            "command": command,
            "decision": decision,
            "payload": _anonymize_mapping(dict(evidence_payload or {}), salt=self._anon_salt, epoch=self._anon_epoch),
            "capability_scope": capability_scope,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        evidence["evidence_hash"] = _stable_hash(evidence)
        evidence["evidence_id"] = str(
            evidence_payload.get("evidence_id")
            or f"evid_{hashlib.sha256(_stable_json(evidence).encode('utf-8')).hexdigest()[:24]}"
        )
        evidence["queryable_ref"] = f"kb://learning/{evidence['evidence_id']}"
        self._learning_evidence.append(
            {
                "evidence_id": evidence["evidence_id"],
                "tenant_id": evidence["tenant_id"],
                "project_id": evidence["project_id"],
                "capability_scope": evidence["capability_scope"],
                "evidence_kind": evidence["evidence_kind"],
                "evidence_hash": evidence["evidence_hash"],
                "model_version": evidence["model_version"],
                "training_set_hash": evidence["training_set_hash"],
                "evaluation_bundle_hash": evidence["evaluation_bundle_hash"],
                "promotion_policy_version": evidence["promotion_policy_version"],
                "lifecycle_state": evidence["lifecycle_state"],
                "quarantine_state": evidence["quarantine_state"],
                "source": evidence["source"],
                "command": evidence["command"],
                "decision": evidence["decision"],
                "gate_results": evidence["gate_results"],
                "metadata": evidence["metadata"],
                "payload": evidence["payload"],
                "capability_scope": evidence["capability_scope"],
                "created_at": evidence["created_at"],
                "queryable_ref": evidence["queryable_ref"],
            }
        )
        if evidence["model_version"]:
            self._learning_models[(envelope["tenant_id"], envelope["project_id"], evidence["model_version"])] = {
                "tenant_id": envelope["tenant_id"],
                "project_id": envelope["project_id"],
                "model_version": evidence["model_version"],
                "training_set_hash": evidence["training_set_hash"],
                "evaluation_bundle_hash": evidence["evaluation_bundle_hash"],
                "promotion_policy_version": evidence["promotion_policy_version"],
                "lifecycle_state": evidence["lifecycle_state"],
                "gate_results": dict(gate_results or {}),
                "updated_at": evidence["created_at"],
                "queryable_ref": f"kb://models/{evidence['model_version']}",
                "evidence_ref": evidence["queryable_ref"],
                "quarantine_state": evidence["quarantine_state"],
            }
        return evidence

    def _learning_collect_lineage(self, *, envelope: dict[str, Any], model_version: str) -> list[dict[str, Any]]:
        lineage: list[dict[str, Any]] = []
        for item in self._learning_evidence:
            if item["tenant_id"] != envelope["tenant_id"] or item["project_id"] != envelope["project_id"]:
                continue
            if model_version and item["model_version"] != model_version:
                continue
            lineage.append(self._learning_public_view(item))
        lineage.sort(key=lambda item: (item["model_version"], item["evidence_id"]))
        return lineage

    def _learning_transition_result(
        self,
        *,
        tenant_id: str,
        project_id: str,
        model_version: str,
        from_state: str,
        to_state: str,
        policy: dict[str, Any],
        gate_results: dict[str, Any],
        queryable_ref: str,
        evidence_ref: str,
        command: str = "",
    ) -> dict[str, Any]:
        current = from_state.upper() if from_state else "DRAFT"
        target = to_state.upper() if to_state else "DRAFT"
        if target not in _LEARNING_ALLOWED_STATES:
            target = "DRAFT"
        if current not in _LEARNING_ALLOWED_STATES:
            current = "DRAFT"
        if target != current and target not in _LEARNING_ALLOWED_TRANSITIONS.get(current, ()):
            raise PermissionError(f"transition {current} -> {target} is not allowed")
        result = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "model_version": model_version,
            "previous_state": current,
            "current_state": target,
            "allowed_transitions": list(_LEARNING_ALLOWED_TRANSITIONS.get(target, ())),
            "policy_version": policy["policy_version"],
            "retention_days": policy["retention_days"],
            "gate_results": dict(gate_results or {}),
            "queryable_ref": queryable_ref,
            "evidence_ref": evidence_ref,
            "command": command or target,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._learning_models[(tenant_id, project_id, model_version)] = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "model_version": model_version,
            "training_set_hash": self._learning_models.get((tenant_id, project_id, model_version), {}).get("training_set_hash", ""),
            "evaluation_bundle_hash": self._learning_models.get((tenant_id, project_id, model_version), {}).get("evaluation_bundle_hash", ""),
            "promotion_policy_version": policy["policy_version"],
            "lifecycle_state": target,
            "gate_results": dict(gate_results or {}),
            "updated_at": result["updated_at"],
            "queryable_ref": queryable_ref,
            "evidence_ref": evidence_ref,
            "quarantine_state": "none",
        }
        return result

    def _learning_model_view(self, scope: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
        return {
            "tenant_id": scope["tenant_id"],
            "project_id": scope["project_id"],
            "model_version": model["model_version"],
            "current_state": model["lifecycle_state"],
            "allowed_transitions": list(_LEARNING_ALLOWED_TRANSITIONS.get(model["lifecycle_state"], ())),
            "training_set_hash": model["training_set_hash"],
            "evaluation_bundle_hash": model["evaluation_bundle_hash"],
            "promotion_policy_version": model["promotion_policy_version"],
            "gate_results": dict(model.get("gate_results") or {}),
            "queryable_ref": model["queryable_ref"],
            "evidence_ref": model["evidence_ref"],
            "quarantine_state": model["quarantine_state"],
            "lineage": self._learning_collect_lineage(envelope=scope, model_version=model["model_version"]),
            "updated_at": model["updated_at"],
        }

    def _learning_public_view(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "evidence_id": item["evidence_id"],
            "tenant_id": item["tenant_id"],
            "project_id": item["project_id"],
            "evidence_kind": item["evidence_kind"],
            "evidence_hash": item["evidence_hash"],
            "model_version": item["model_version"],
            "training_set_hash": item["training_set_hash"],
            "evaluation_bundle_hash": item["evaluation_bundle_hash"],
            "promotion_policy_version": item["promotion_policy_version"],
            "lifecycle_state": item["lifecycle_state"],
            "quarantine_state": item["quarantine_state"],
            "queryable_ref": item["queryable_ref"],
            "metadata": dict(item["metadata"]),
            "created_at": item["created_at"],
        }

    def _learning_payload_contains_quarantine_fields(self, payload: dict[str, Any]) -> bool:
        for key, value in payload.items():
            if str(key).strip().lower() in _LEARNING_QUARANTINE_KEYS and value not in ("", None, {}, []):
                return True
            if isinstance(value, dict) and self._learning_payload_contains_quarantine_fields(value):
                return True
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and self._learning_payload_contains_quarantine_fields(item):
                        return True
        return False
    