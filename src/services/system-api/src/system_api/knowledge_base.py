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
from typing import Any

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from .errors import FieldViolation, PublicErrorSpec, abort_invalid_argument, abort_public, abort_with_error_info
from .observability import (
    record_kb_contract_marker,
    record_kb_fallback,
    record_kb_query,
    record_kb_replay_failure,
    trace_id_from_traceparent,
)
from .security import auth_context, enforce_authn, enforce_authz

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


class KnowledgeBaseUnavailable(RuntimeError):
    """Raised when the KB backend is disabled or unavailable."""


@dataclass(slots=True)
class _StoredRecord:
    record: Any
    tenant_id: str
    project_id: str
    created_at: datetime
    updated_at: datetime
    fingerprint: str
    sequence: int


@dataclass(slots=True)
class _StoredDecisionLog:
    decision_log: Any
    tenant_id: str
    project_id: str
    decided_at: datetime
    fingerprint: str
    sequence: int


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
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


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
        self._sequence = 0

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
        page_size = self._page_size(request.page_size)
        with self._lock:
            self._gc_locked()
            filtered = [entry.record for entry in self._records.values() if self._record_visible_to_tenant(entry, envelope["tenant_id"], context) and self._record_matches_filter(entry.record, request.filter)]
            filtered.sort(key=lambda item: (self._ts_signature(item.created_at), item.record_id))
            offset, query_sig = self._decode_cursor(request.page_token, envelope, self._filter_signature(request.filter), kind="records", context=context)
            next_offset = offset + page_size
            window = filtered[offset:next_offset]
            next_token = self._encode_cursor(envelope=envelope, filter_payload=self._filter_signature(request.filter), kind="records", offset=next_offset, query_sig=query_sig, more=next_offset < len(filtered))
        record_kb_query("records", hit=bool(window))
        return self._kb_pb.QueryRecordsResponse(records=window, next_page_token=next_token)

    def GetRecord(self, request, context: grpc.ServicerContext):
        self._require_read(context, operation="get_record")
        envelope = self._normalize_envelope(request.envelope, context)
        with self._lock:
            self._gc_locked()
            entry = self._records.get(request.record_id)
            if entry is None or not self._record_visible_to_tenant(entry, envelope["tenant_id"], context):
                record_kb_query("records", hit=False)
                self._abort_not_found(context, request.record_id)
                return self._kb_pb.GetRecordResponse()
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
        page_size = self._page_size(request.page_size)
        with self._lock:
            self._gc_locked()
            filtered = [entry.decision_log for entry in self._decision_logs if self._decision_visible_to_tenant(entry, envelope["tenant_id"], context) and self._decision_matches_filter(entry.decision_log, trace_id=request.trace_id, model_version=request.model_version)]
            filtered.sort(key=lambda item: (self._ts_signature(item.decided_at), item.decision_id))
            offset, query_sig = self._decode_cursor(request.page_token, envelope, {"trace_id": request.trace_id, "model_version": request.model_version}, kind="decision_logs", context=context)
            next_offset = offset + page_size
            window = filtered[offset:next_offset]
            next_token = self._encode_cursor(envelope=envelope, filter_payload={"trace_id": request.trace_id, "model_version": request.model_version}, kind="decision_logs", offset=next_offset, query_sig=query_sig, more=next_offset < len(filtered))
        record_kb_query("decision_logs", hit=bool(window))
        return self._kb_pb.QueryDecisionLogsResponse(decision_logs=window, next_page_token=next_token)

    # Ingestion helpers --------------------------------------------------

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
        snapshot = _anonymize_mapping(dict(payload.get("feature_snapshot") or {}), salt=self._anon_salt, epoch=self._anon_epoch)
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
        with self._lock:
            self._gc_locked()
            self._store_decision_log(decision_log=decision_log, envelope=envelope, context=None)
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
        attrs = _anonymize_mapping(dict(payload.get("attributes") or {}), salt=self._anon_salt, epoch=self._anon_epoch)
        attrs.update(
            {
                "record_kind": "benchmark_run",
                "request_hash": str(payload.get("request_hash", "")).strip(),
                "idempotency_key": str(payload.get("idempotency_key", "")).strip(),
                "parent_run_id": str(payload.get("parent_run_id", "")).strip(),
                "run_state": str(payload.get("state", "")).strip(),
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
            self._upsert_record(record=record, envelope=envelope, allow_overwrite=True, source="benchmark", replay_bundle_ref=attrs["replay_bundle_ref"], context=None)
        record_kb_query("benchmark_runs", hit=True)
        return record.record_id

    # Internal helpers --------------------------------------------------

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
        return {}

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

    def _ts_signature(self, ts: Timestamp | None) -> str:
        return _ts_to_dt(ts).isoformat() if ts is not None else ""

    def _record_visible_to_tenant(self, entry: _StoredRecord, tenant_id: str, context: grpc.ServicerContext) -> bool:
        _, roles, _ = auth_context(context)
        return True if ("*" in roles or "admin" in roles) else entry.tenant_id == tenant_id

    def _decision_visible_to_tenant(self, entry: _StoredDecisionLog, tenant_id: str, context: grpc.ServicerContext) -> bool:
        _, roles, _ = auth_context(context)
        return True if ("*" in roles or "admin" in roles) else entry.tenant_id == tenant_id

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
                pass
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
        source: str,
        replay_bundle_ref: str,
        context: grpc.ServicerContext | None,
    ) -> dict[str, Any]:
        record_id = record.record_id
        now = datetime.now(timezone.utc)
        existing = self._records.get(record_id)

        if existing and not allow_overwrite:
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
        created_at = _ts_to_dt(record.created_at) if getattr(record, "created_at", None) else now
        if existing:
            created_at = existing.created_at

        record.created_at.FromDatetime(created_at)
        fingerprint = self._record_fingerprint(record, replay_bundle_ref=replay_bundle_ref)

        stored = _StoredRecord(
            record=self._clone_record(record),
            tenant_id=envelope["tenant_id"],
            project_id=envelope["project_id"],
            created_at=created_at,
            updated_at=now,
            fingerprint=fingerprint,
            sequence=self._sequence,
        )
        self._records[record_id] = stored

        ts = Timestamp()
        ts.FromDatetime(now)
        return {"record_id": record_id, "created": not bool(existing), "updated_at": ts}

    def _store_decision_log(self, decision_log: Any, envelope: dict[str, Any], context: grpc.ServicerContext | None) -> _StoredDecisionLog:
        self._sequence += 1
        decided_at = _ts_to_dt(decision_log.decided_at) if getattr(decision_log, "decided_at", None) else datetime.now(timezone.utc)
        decision_log.decided_at.FromDatetime(decided_at)
        
        fingerprint = self._decision_fingerprint(decision_log)
        stored = _StoredDecisionLog(
            decision_log=self._clone_decision_log(decision_log),
            tenant_id=envelope["tenant_id"],
            project_id=envelope["project_id"],
            decided_at=decided_at,
            fingerprint=fingerprint,
            sequence=self._sequence,
        )
        self._decision_logs.append(stored)
        return stored

    def _gc_locked(self) -> None:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self._retention_seconds)
        
        # Evict expired records
        expired_records = [k for k, v in self._records.items() if v.created_at < cutoff]
        for k in expired_records:
            del self._records[k]
            
        # Evict expired decision logs
        self._decision_logs = [log for log in self._decision_logs if log.decided_at >= cutoff]

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
    