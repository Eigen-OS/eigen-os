"""gRPC implementation for the internal Neuro-DPDA service."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import logging
import os
import re
from typing import Iterable

import grpc

from eigen.internal.v1 import neuro_symbolic_service_pb2 as nsc_pb
from eigen.internal.v1 import neuro_symbolic_service_pb2_grpc as nsc_pb_grpc

from .observability import record_decision, record_denial, record_request

_LOG = logging.getLogger("neuro_symbolic_service")

_CONTRACT_VERSION = "1.0.0"
_POLICY_SNAPSHOT_DEFAULT = "1.0.0"
_TOKEN_DEFAULT = "dev-internal-token"
_MODEL_VERSION_DEFAULT = "dpda-model-v1"
_ALLOWED_CALLERS_DEFAULT = "eigen-kernel,eigen-compiler"
_MAX_FEATURE_VECTOR_BYTES_DEFAULT = 16_384

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


@dataclass(frozen=True)
class FeatureRedactionResult:
    feature_vector: bytes
    redacted_fields: tuple[str, ...]


@dataclass(frozen=True)
class InternalIdentity:
    caller_id: str
    model_version: str


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _hex_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _float_from_digest(digest: bytes, start: int = 0) -> float:
    raw = digest[start : start + 8]
    if len(raw) < 8:
        raw = (raw + b"\x00" * 8)[:8]
    return int.from_bytes(raw, byteorder="big", signed=False) / float(1 << 64)


def _confidence_from_score(score: float) -> float:
    score = max(0.0, min(1.0, score))
    confidence = 0.55 + (1.0 - abs(score - 0.5) * 2.0) * 0.45
    return round(max(0.55, min(0.99, confidence)), 6)


def _decision_from_score(score: float) -> nsc_pb.AdvisoryDecision:
    if score >= 0.68:
        return nsc_pb.ADVISORY_DECISION_ACCEPT
    if score >= 0.36:
        return nsc_pb.ADVISORY_DECISION_REVIEW
    return nsc_pb.ADVISORY_DECISION_REJECT


def _metadata_map(context: grpc.ServicerContext) -> dict[str, str]:
    return {k.lower(): v for k, v in (context.invocation_metadata() or [])}


def _read_env_set(name: str, default: str) -> set[str]:
    raw = os.getenv(name, default)
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _policy_snapshot_version() -> str:
    value = os.getenv("NEURO_SYMBOLIC_POLICY_SNAPSHOT_VERSION", _POLICY_SNAPSHOT_DEFAULT).strip()
    return value or _POLICY_SNAPSHOT_DEFAULT


def _feature_vector_byte_limit() -> int:
    raw = os.getenv("NEURO_SYMBOLIC_MAX_FEATURE_VECTOR_BYTES", str(_MAX_FEATURE_VECTOR_BYTES_DEFAULT)).strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return _MAX_FEATURE_VECTOR_BYTES_DEFAULT


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


def _redact_json_value(value, path: str, redactions: set[str]):
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


def _redact_feature_vector(feature_vector: bytes) -> FeatureRedactionResult:
    if not feature_vector:
        return FeatureRedactionResult(feature_vector=b"", redacted_fields=())

    redactions: set[str] = set()
    raw_text = feature_vector.decode("utf-8", errors="replace")

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        sanitized = _redact_scalar_text(raw_text, "$", redactions)
        return FeatureRedactionResult(feature_vector=sanitized.encode("utf-8"), redacted_fields=tuple(sorted(redactions)))

    redacted = _redact_json_value(parsed, "$", redactions)
    sanitized = json.dumps(redacted, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return FeatureRedactionResult(feature_vector=sanitized.encode("utf-8"), redacted_fields=tuple(sorted(redactions)))


def _require_internal_identity(context: grpc.ServicerContext, *, method_name: str) -> InternalIdentity:
    md = _metadata_map(context)
    service_id = md.get("x-eigen-service-id", "").strip().lower()
    authorization = md.get("authorization", "").strip()
    expected_token = os.getenv("NEURO_SYMBOLIC_INTERNAL_TOKEN", _TOKEN_DEFAULT).strip() or _TOKEN_DEFAULT
    if not authorization or not service_id:
        record_denial("missing_internal_identity")
        context.abort(grpc.StatusCode.UNAUTHENTICATED, f"internal identity required for {method_name}")
    if not hmac.compare_digest(authorization, f"Bearer {expected_token}"):
        record_denial("invalid_internal_identity")
        context.abort(grpc.StatusCode.UNAUTHENTICATED, f"internal identity required for {method_name}")

    allowed_callers = _read_env_set("NEURO_SYMBOLIC_ALLOWED_CALLERS", _ALLOWED_CALLERS_DEFAULT)
    if service_id not in allowed_callers:
        record_denial("caller_not_permitted")
        context.abort(grpc.StatusCode.PERMISSION_DENIED, f"caller not permitted for {method_name}")

    return InternalIdentity(
        caller_id=service_id,
        model_version=os.getenv("NEURO_SYMBOLIC_MODEL_VERSION", _MODEL_VERSION_DEFAULT).strip() or _MODEL_VERSION_DEFAULT,
    )


def _require_tenant_project_binding(context: grpc.ServicerContext, *, method_name: str, tenant_id: str, project_id: str) -> None:
    md = _metadata_map(context)
    md_tenant = md.get("x-eigen-tenant-id", "").strip()
    md_project = md.get("x-eigen-project-id", "").strip()
    if not md_tenant or not md_project:
        record_denial("missing_scope_binding")
        context.abort(grpc.StatusCode.PERMISSION_DENIED, f"tenant/project binding required for {method_name}")
    if md_tenant != tenant_id or md_project != project_id:
        record_denial("scope_mismatch")
        context.abort(grpc.StatusCode.PERMISSION_DENIED, f"tenant/project scope mismatch for {method_name}")


def _explainability_envelope(
    *,
    request_id: str,
    tenant_id: str,
    project_id: str,
    policy_snapshot_version: str,
    model_version: str,
    confidence: float,
    feature_digest_sha256: str,
    replay_digest: str,
    redacted_fields: Iterable[str],
    feature_schema_version: str,
    model_hint: str,
) -> dict[str, object]:
    return {
        "request_id": request_id,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "policy_snapshot_version": policy_snapshot_version,
        "model_version": model_version,
        "confidence": confidence,
        "feature_set": {
            "schema_version": feature_schema_version,
            "model_hint": model_hint.strip(),
            "feature_digest_sha256": feature_digest_sha256,
            "redacted_fields": sorted(set(redacted_fields)),
        },
        "retrieval_references": [
            f"nsc://policy-snapshot/{policy_snapshot_version}",
            f"nsc://model/{model_version}",
            f"nsc://request/{request_id}/{feature_digest_sha256}",
        ],
        "replay_digest": replay_digest,
        "explanation_ref": f"nsc://explanations/{request_id}/{replay_digest}",
    }


class NeuroSymbolicService(nsc_pb_grpc.NeuroSymbolicServiceServicer):
    def __init__(self, *, policy_snapshot_version: str | None = None):
        self._policy_snapshot_version = (policy_snapshot_version or _policy_snapshot_version()).strip() or _POLICY_SNAPSHOT_DEFAULT
        self._model_version = os.getenv("NEURO_SYMBOLIC_MODEL_VERSION", _MODEL_VERSION_DEFAULT).strip() or _MODEL_VERSION_DEFAULT

    def ScoreCompilationPlan(self, request, context: grpc.ServicerContext):
        identity = _require_internal_identity(context, method_name="ScoreCompilationPlan")

        if not request.HasField("envelope") or not request.envelope.contract_version.strip():
            record_denial("missing_contract_version")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "contract_version is required")
        contract_version = request.envelope.contract_version.strip()
        if contract_version != _CONTRACT_VERSION:
            record_denial("unsupported_contract_version")
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"unsupported neuro-symbolic contract_version: {contract_version}",
            )

        if not request.HasField("context"):
            record_denial("missing_context")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "context is required")
        req_ctx = request.context
        request_id = req_ctx.request_id.strip()
        tenant_id = req_ctx.tenant_id.strip()
        project_id = req_ctx.project_id.strip()
        feature_schema_version = req_ctx.feature_schema_version.strip()
        policy_snapshot_version = req_ctx.policy_snapshot_version.strip()
        subject_id = req_ctx.subject_id.strip()
        workload_id = req_ctx.workload_id.strip()
        authz_decision_id = req_ctx.authz_decision_id.strip()
        if not all([request_id, tenant_id, project_id, feature_schema_version, policy_snapshot_version, subject_id, workload_id, authz_decision_id]):
            record_denial("missing_context_fields")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "context fields are required")

        _require_tenant_project_binding(context, method_name="ScoreCompilationPlan", tenant_id=tenant_id, project_id=project_id)

        if policy_snapshot_version != self._policy_snapshot_version:
            record_denial("policy_snapshot_mismatch")
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                "context.policy_snapshot_version must match the active immutable policy snapshot",
            )

        if not request.feature_vector:
            record_denial("missing_feature_vector")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "feature_vector is required")

        feature_limit = _feature_vector_byte_limit()
        if len(request.feature_vector) > feature_limit:
            record_denial("feature_vector_too_large")
            context.abort(
                grpc.StatusCode.RESOURCE_EXHAUSTED,
                f"feature_vector exceeds policy size limit ({len(request.feature_vector)} > {feature_limit})",
            )

        if not request.feature_digest_sha256.strip() or not re.fullmatch(r"[0-9a-f]{64}", request.feature_digest_sha256.strip().lower()):
            record_denial("invalid_feature_digest")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "feature_digest_sha256 must be a SHA-256 hex digest")
        feature_digest_sha256 = request.feature_digest_sha256.strip().lower()
        if _hex_digest(request.feature_vector) != feature_digest_sha256:
            record_denial("feature_digest_mismatch")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "feature_digest_sha256 does not match feature_vector")

        redaction = _redact_feature_vector(request.feature_vector)
        canonical = _stable_json(
            {
                "contract_version": contract_version,
                "request_id": request_id,
                "tenant_id": tenant_id,
                "project_id": project_id,
                "feature_schema_version": feature_schema_version,
                "policy_snapshot_version": self._policy_snapshot_version,
                "subject_id": subject_id,
                "workload_id": workload_id,
                "authz_decision_id": authz_decision_id,
                "feature_digest_sha256": feature_digest_sha256,
                "deterministic_seed": int(request.deterministic_seed),
                "caller_id": identity.caller_id,
                "model_hint": request.model_hint.strip(),
                "feature_vector": redaction.feature_vector.decode("utf-8", errors="replace"),
            }
        ).encode("utf-8")
        replay_digest = _hex_digest(canonical)
        score = round(_float_from_digest(hashlib.sha256(canonical).digest(), 0), 6)
        confidence = _confidence_from_score(score)
        decision = _decision_from_score(score)

        record_request("ok")
        record_decision(nsc_pb.AdvisoryDecision.Name(int(decision)))

        envelope = _explainability_envelope(
            request_id=request_id,
            tenant_id=tenant_id,
            project_id=project_id,
            policy_snapshot_version=self._policy_snapshot_version,
            model_version=self._model_version,
            confidence=confidence,
            feature_digest_sha256=feature_digest_sha256,
            replay_digest=replay_digest,
            redacted_fields=redaction.redacted_fields,
            feature_schema_version=feature_schema_version,
            model_hint=request.model_hint,
        )

        _LOG.info(
            "neuro-symbolic scoring completed",
            extra={
                "rpc": "ScoreCompilationPlan",
                "request_id": request_id,
                "tenant_id": tenant_id,
                "project_id": project_id,
                "subject_id": subject_id,
                "workload_id": workload_id,
                "policy_snapshot_version": self._policy_snapshot_version,
                "model_version": self._model_version,
                "decision": nsc_pb.AdvisoryDecision.Name(int(decision)),
                "caller_id": identity.caller_id,
                "trace_id": req_ctx.trace_id,
                "traceparent": req_ctx.traceparent,
            },
        )

        return nsc_pb.ScoreCompilationPlanResponse(
            contract_version=contract_version,
            request_id=request_id,
            tenant_id=tenant_id,
            project_id=project_id,
            feature_schema_version=feature_schema_version,
            policy_snapshot_version=self._policy_snapshot_version,
            model_version=self._model_version,
            decision=decision,
            score=score,
            confidence=confidence,
            explanation_ref=str(envelope["explanation_ref"]),
            replay_digest=replay_digest,
            deterministic_compatible=True,
            subject_id=subject_id,
            workload_id=workload_id,
            authz_decision_id=authz_decision_id,
        )
