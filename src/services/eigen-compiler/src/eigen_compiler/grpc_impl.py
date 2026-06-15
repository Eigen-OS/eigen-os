"""gRPC implementation for internal CompilationService."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import hmac
import json
import logging
import os
import re
import threading
from typing import Callable

import grpc

from .compiler import CompilerValidationError, compile_eigen_lang
from .errors import abort_invalid_argument
from .validation import validate_compile_circuit, validate_compile_job


_LOG = logging.getLogger("eigen_compiler")

_METRIC_LOCK = threading.Lock()
_RPC_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_STAGE_COUNT_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_STAGE_SECONDS_TOTALS: defaultdict[tuple[tuple[str, str], ...], float] = defaultdict(float)
_VALIDATION_FAILURE_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_AQO_DIGEST_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_REPLAY_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_SEEN_AQO_DIGESTS: set[str] = set()
_OBSERVABILITY_CONTRACT_VERSION = "1.0.0"

_REDACTED_VALUE = "[REDACTED]"
_MASKED_EMAIL_VALUE = "[REDACTED_EMAIL]"
_MASKED_PHONE_VALUE = "[REDACTED_PHONE]"
_MASKED_IDENTIFIER_VALUE = "[REDACTED_ID]"

_REDACT_DELETE_KEYS = {
    "authorization",
    "auth_header",
    "auth-token",
    "bearer",
    "cookie",
    "credentials",
    "credential",
    "password",
    "passwd",
    "pwd",
    "private_secret",
    "secret",
    "session_cookie",
    "sessionid",
    "session_token",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "id_token",
    "raw_auth_header",
    "raw_authorization",
}
_REDACT_MASK_EMAIL_KEYS = {
    "email",
    "email_address",
    "contact_email",
    "e_mail",
}
_REDACT_MASK_PHONE_KEYS = {
    "phone",
    "phone_number",
    "mobile",
    "msisdn",
    "contact_phone",
}
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
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?){1,3}\d{2,4}(?!\d)")
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}\b")
_UUID_RE = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")


@dataclass(frozen=True)
class FeatureRedactionResult:
    feature_vector: bytes
    redacted_fields: tuple[str, ...]

_STAGE_LABELS = {
    "request_validation",
    "parse",
    "validate_ast",
    "annotate",
    "lower_to_ir",
    "eigen_dpda",
    "canonicalize_aqo",
    "emit",
}


def _label_tuple(**labels: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((k, str(v)) for k, v in labels.items()))


def _fmt_labels(label_items: tuple[tuple[str, str], ...]) -> str:
    if not label_items:
        return ""
    rendered = ",".join(f'{k}="{v}"' for k, v in label_items)
    return f"{{{rendered}}}"


def _bump(counter: Counter[tuple[tuple[str, str], ...]], **labels: str) -> None:
    with _METRIC_LOCK:
        counter[_label_tuple(**labels)] += 1


def _bump_stage(stage: str, elapsed_seconds: float, outcome: str) -> None:
    if stage not in _STAGE_LABELS:
        stage = "emit"
    labels = _label_tuple(stage=stage, outcome=outcome)
    with _METRIC_LOCK:
        _STAGE_COUNT_TOTALS[labels] += 1
        _STAGE_SECONDS_TOTALS[labels] += elapsed_seconds


def _record_rpc(rpc: str, outcome: str) -> None:
    _bump(_RPC_TOTALS, rpc=rpc, outcome=outcome)


def _record_validation_failure(stage: str, reason: str) -> None:
    _bump(_VALIDATION_FAILURE_TOTALS, stage=stage, reason=reason)


def _record_digest_emitted(kind: str = "aqo") -> None:
    _bump(_AQO_DIGEST_TOTALS, kind=kind)


def _record_replay(kind: str = "duplicate") -> None:
    _bump(_REPLAY_TOTALS, kind=kind)


def reset_metrics() -> None:
    with _METRIC_LOCK:
        _RPC_TOTALS.clear()
        _STAGE_COUNT_TOTALS.clear()
        _STAGE_SECONDS_TOTALS.clear()
        _VALIDATION_FAILURE_TOTALS.clear()
        _AQO_DIGEST_TOTALS.clear()
        _REPLAY_TOTALS.clear()
        _SEEN_AQO_DIGESTS.clear()


def _validation_reason(violations) -> str:
    text = " ".join(v.description for v in violations).lower()
    if "not found" in text:
        return "not_found"
    if "limit exceeded" in text:
        return "resource_exhausted"
    if "unsupported" in text:
        return "unimplemented"
    return "invalid_argument"


def _render_counter_family(name: str, counter: Counter[tuple[tuple[str, str], ...]]) -> list[str]:
    lines = [f"# TYPE {name} counter"]
    for labels, value in sorted(counter.items(), key=lambda item: item[0]):
        lines.append(f"{name}{_fmt_labels(labels)} {int(value)}")
    return lines


def render_metrics_text() -> str:
    with _METRIC_LOCK:
        lines = [
            "# TYPE eigen_observability_contract_info gauge",
            f'eigen_observability_contract_info{{version="{_OBSERVABILITY_CONTRACT_VERSION}"}} 1',
            "# TYPE eigen_compiler_contract_info gauge",
            'eigen_compiler_contract_info{version="1.0.0"} 1',
        ]
        lines.extend(_render_counter_family("eigen_compiler_rpc_total", _RPC_TOTALS))
        lines.extend(_render_counter_family("eigen_compiler_stage_duration_seconds_count", _STAGE_COUNT_TOTALS))
        lines.append("# TYPE eigen_compiler_stage_duration_seconds_sum counter")
        for labels, value in sorted(_STAGE_SECONDS_TOTALS.items(), key=lambda item: item[0]):
            lines.append(f"eigen_compiler_stage_duration_seconds_sum{_fmt_labels(labels)} {value:.9f}")
        lines.extend(_render_counter_family("eigen_compiler_validation_failures_total", _VALIDATION_FAILURE_TOTALS))
        lines.extend(_render_counter_family("eigen_compiler_aqo_digest_emitted_total", _AQO_DIGEST_TOTALS))
        lines.extend(_render_counter_family("eigen_compiler_replay_compiles_total", _REPLAY_TOTALS))
        return "\n".join(lines) + "\n"


def _rpc_metadata_map(context: grpc.ServicerContext) -> dict[str, str]:
    return {k.lower(): v for k, v in (context.invocation_metadata() or [])}


def _request_context_from_rpc(request, context: grpc.ServicerContext) -> dict[str, str]:
    rpc_md = _rpc_metadata_map(context)
    request_md = request.request_metadata if request.HasField("request_metadata") else None

    def pick(field: str, header_key: str) -> str:
        if request_md is not None:
            value = getattr(request_md, field, "")
            if value:
                return value
        return rpc_md.get(header_key, "")
    
    def stringify_deadline(value) -> str:
        if not value:
            return ""
        if hasattr(value, "seconds") and hasattr(value, "nanos"):
            microseconds = int(getattr(value, "nanos", 0)) // 1000
            return str(timedelta(seconds=int(getattr(value, "seconds", 0)), microseconds=microseconds))
        return str(value)

    deadline = stringify_deadline(pick("deadline", "x-eigen-deadline"))
    if not deadline:
        remaining = context.time_remaining()
        if remaining is not None:
            deadline = f"{remaining:.6f}s"

    return {
        "request_id": pick("request_id", "x-eigen-request-id"),
        "trace_id": pick("trace_id", "x-eigen-trace-id"),
        "traceparent": pick("traceparent", "traceparent"),
        "deadline": deadline,
        "retry_policy": pick("retry_policy", "x-eigen-retry-policy"),
        "security_context": pick("security_context", "authorization"),
        "sandbox_profile": pick("sandbox_profile", "x-eigen-sandbox-profile"),
        "tenant_id": pick("tenant_id", "x-eigen-tenant-id"),
        "project_id": pick("project_id", "x-eigen-project-id"),
    }


def _circuit_format_value(types_pb, *names: str) -> int:
    for name in names:
        if hasattr(types_pb, name):
            return int(getattr(types_pb, name))
    raise AttributeError(f"None of the enum names exist: {names}")


class CompilationService:
    """Implementation of eigen.internal.v1.CompilationService."""

    def __init__(self, comp_pb, types_pb):
        self._comp_pb = comp_pb
        self._types_pb = types_pb

    def _compile_response(
        self,
        *,
        rpc: str,
        source: bytes,
        source_ref: str | None = None,
        options: dict[str, str] | None = None,
        request_context: dict[str, str] | None = None,
    ):
        result = compile_eigen_lang(
            source,
            source_ref=source_ref,
            options=options,
            request_context=request_context,
            observer=self._stage_observer(
                rpc=rpc,
                request_context=request_context or {},
            ),
        )

        return self._comp_pb.CompileCircuitResponse(
            circuit=self._types_pb.CircuitPayload(
                format=_circuit_format_value(
                    self._types_pb,
                    "CIRCUIT_FORMAT_AQO_JSON",
                    "AQO_JSON",
                ),
                data=result.aqo_json,
            ),
            metadata=result.metadata,
        )

    def _stage_observer(
        self,
        *,
        rpc: str,
        request_context: dict[str, str],
    ) -> Callable[[str, float, str], None]:

        def _observe(stage: str, elapsed_seconds: float, outcome: str) -> None:
            _bump_stage(stage, elapsed_seconds, outcome)

            _LOG.info(
                "compiler_stage",
                extra={
                    "rpc": rpc,
                    "stage": stage,
                    "outcome": outcome,
                    "elapsed_ms": round(elapsed_seconds * 1000.0, 3),
                    "request_id": request_context.get("request_id", ""),
                    "trace_id": request_context.get("trace_id", ""),
                    "traceparent": request_context.get("traceparent", ""),
                },
            )

        return _observe

    def CompileCircuit(self, request, context: grpc.ServicerContext):
        request_context = _request_context_from_rpc(request, context)

        _log_start(
            "CompilationService.CompileCircuit",
            "",
            request_context,
            context,
        )

        violations = validate_compile_circuit(request)

        if violations:
            _record_rpc("CompileCircuit", "failure")

            _record_validation_failure(
                "request_validation",
                _validation_reason(violations),
            )

            abort_invalid_argument(
                context,
                message="validation failed",
                violations=violations,
            )

        source = request.source if request.source else b""
        source_ref = request.source_ref or None

        try:
            resp = self._compile_response(
                rpc="CompileCircuit",
                source=source,
                source_ref=source_ref,
                options=dict(request.options),
                request_context=request_context,
            )

            _record_rpc("CompileCircuit", "success")

            aqo_sha = resp.metadata.get("aqo_sha256", "")

            if aqo_sha:
                _record_digest_emitted("aqo")

                replay_detected = False

                with _METRIC_LOCK:
                    if aqo_sha in _SEEN_AQO_DIGESTS:
                        replay_detected = True
                    else:
                        _SEEN_AQO_DIGESTS.add(aqo_sha)

                if replay_detected:
                    _record_replay("duplicate")

            _log_end(
                "CompilationService.CompileCircuit",
                "",
                request_context,
                context,
                resp.metadata,
            )

            return resp

        except CompilerValidationError as exc:
            _record_rpc("CompileCircuit", "failure")

            _record_validation_failure(
                "compile",
                _validation_reason(exc.violations),
            )

            abort_invalid_argument(
                context,
                message="validation failed",
                violations=exc.violations,
            )

    def CompileJob(self, request, context: grpc.ServicerContext):
        request_context = _request_context_from_rpc(request, context)

        _log_start(
            "CompilationService.CompileJob",
            request.job_id,
            request_context,
            context,
        )

        violations = validate_compile_job(request)

        if violations:
            _record_rpc("CompileJob", "failure")

            _record_validation_failure(
                "request_validation",
                _validation_reason(violations),
            )

            abort_invalid_argument(
                context,
                message="validation failed",
                violations=violations,
            )

        source = request.source if request.source else b""
        source_ref = request.source_ref or None

        try:
            compiled = self._compile_response(
                rpc="CompileJob",
                source=source,
                source_ref=source_ref,
                options=dict(request.options),
                request_context=request_context,
            )

        except CompilerValidationError as exc:
            _record_rpc("CompileJob", "failure")

            _record_validation_failure(
                "compile",
                _validation_reason(exc.violations),
            )

            abort_invalid_argument(
                context,
                message="validation failed",
                violations=exc.violations,
            )

        resp = self._comp_pb.CompileJobResponse(
            job_id=request.job_id,
            circuit=compiled.circuit,
            metadata=compiled.metadata,
        )

        _record_rpc("CompileJob", "success")

        aqo_sha = compiled.metadata.get("aqo_sha256", "")

        if aqo_sha:
            _record_digest_emitted("aqo")

            replay_detected = False

            with _METRIC_LOCK:
                if aqo_sha in _SEEN_AQO_DIGESTS:
                    replay_detected = True
                else:
                    _SEEN_AQO_DIGESTS.add(aqo_sha)

            if replay_detected:
                _record_replay("duplicate")

        _log_end(
            "CompilationService.CompileJob",
            request.job_id,
            request_context,
            context,
            compiled.metadata,
        )

        return resp

    def OptimizeCircuit(self, request, context: grpc.ServicerContext):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "OptimizeCircuit is not implemented")

    def ValidateCircuit(self, request, context: grpc.ServicerContext):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "ValidateCircuit is not implemented")

_NEURO_CONTRACT_VERSION = "1.0.0"
_NEURO_ALLOWED_CALLERS_DEFAULT = "eigen-kernel,eigen-compiler,system-api"
_NEURO_TOKEN_ENV = "EIGEN_NEURO_SYMBOLIC_SERVICE_TOKEN"
_NEURO_CALLERS_ENV = "EIGEN_NEURO_SYMBOLIC_ALLOWED_CALLERS"
_NEURO_MODEL_VERSION_ENV = "EIGEN_NEURO_SYMBOLIC_MODEL_VERSION"
_NEURO_POLICY_SNAPSHOT_VERSION_ENV = "EIGEN_NEURO_SYMBOLIC_POLICY_SNAPSHOT_VERSION"
_NEURO_POLICY_SNAPSHOT_DEFAULT = "policy-2026-06-15"


def _redaction_path(parent: str, key: str) -> str:
    if not parent or parent == "$":
        return f"$.{key}"
    return f"{parent}.{key}"


def _record_redaction(redactions: set[str], path: str, reason: str) -> None:
    redactions.add(f"{path}:{reason}")


def _redact_scalar_text(value: str, path: str, redactions: set[str]) -> str:
    redacted = value

    if _BEARER_RE.search(redacted):
        redacted = _BEARER_RE.sub(_REDACTED_VALUE, redacted)
        _record_redaction(redactions, path, "deleted")
    if _EMAIL_RE.search(redacted):
        redacted = _EMAIL_RE.sub(_MASKED_EMAIL_VALUE, redacted)
        _record_redaction(redactions, path, "masked_email")
    if _PHONE_RE.search(redacted):
        redacted = _PHONE_RE.sub(_MASKED_PHONE_VALUE, redacted)
        _record_redaction(redactions, path, "masked_phone")
    if _UUID_RE.search(redacted):
        redacted = _UUID_RE.sub(_MASKED_IDENTIFIER_VALUE, redacted)
        _record_redaction(redactions, path, "masked_identifier")
    return redacted


def _redact_json_value(value, path: str, redactions: set[str]):
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, nested in value.items():
            nested_path = _redaction_path(path, str(key))
            key_lower = str(key).strip().lower()

            if key_lower in _REDACT_DELETE_KEYS:
                redacted[key] = _REDACTED_VALUE
                _record_redaction(redactions, nested_path, "deleted")
                continue
            if key_lower in _REDACT_MASK_EMAIL_KEYS:
                redacted[key] = _MASKED_EMAIL_VALUE
                _record_redaction(redactions, nested_path, "masked_email")
                continue
            if key_lower in _REDACT_MASK_PHONE_KEYS:
                redacted[key] = _MASKED_PHONE_VALUE
                _record_redaction(redactions, nested_path, "masked_phone")
                continue
            if key_lower in _REDACT_MASK_IDENTIFIER_KEYS or key_lower.endswith("_id"):
                if isinstance(nested, (dict, list)):
                    redacted[key] = _redact_json_value(nested, nested_path, redactions)
                else:
                    redacted[key] = _MASKED_IDENTIFIER_VALUE
                    _record_redaction(redactions, nested_path, "masked_identifier")
                continue

            redacted[key] = _redact_json_value(nested, nested_path, redactions)
        return redacted

    if isinstance(value, list):
        return [
            _redact_json_value(item, f"{path}[{index}]", redactions)
            for index, item in enumerate(value)
        ]

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
        return FeatureRedactionResult(
            feature_vector=sanitized.encode("utf-8"),
            redacted_fields=tuple(sorted(redactions)),
        )

    redacted = _redact_json_value(parsed, "$", redactions)
    sanitized_text = json.dumps(redacted, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return FeatureRedactionResult(
        feature_vector=sanitized_text.encode("utf-8"),
        redacted_fields=tuple(sorted(redactions)),
    )


def _neuro_service_config() -> dict[str, object]:
    allowed_callers = {
        caller.strip().lower()
        for caller in os.getenv(_NEURO_CALLERS_ENV, _NEURO_ALLOWED_CALLERS_DEFAULT).split(",")
        if caller.strip()
    }
    token = os.getenv(_NEURO_TOKEN_ENV, "dev-internal-token")
    model_version = os.getenv(_NEURO_MODEL_VERSION_ENV, "dpda-model-v1")
    return {
        "allowed_callers": allowed_callers,
        "token": token,
        "model_version": model_version,
    }


def _active_policy_snapshot_version() -> str:
    snapshot_version = os.getenv(_NEURO_POLICY_SNAPSHOT_VERSION_ENV, _NEURO_POLICY_SNAPSHOT_DEFAULT).strip()
    return snapshot_version or _NEURO_POLICY_SNAPSHOT_DEFAULT


def _neuro_metadata(context: grpc.ServicerContext) -> dict[str, str]:
    return {k.lower(): v for k, v in (context.invocation_metadata() or [])}


def _require_internal_model_identity(context: grpc.ServicerContext, *, method_name: str) -> tuple[str, dict[str, object]]:
    cfg = _neuro_service_config()
    md = _neuro_metadata(context)
    service_id = md.get("x-eigen-service-id", "").strip().lower()
    authorization = md.get("authorization", "").strip()
    expected = f"Bearer {cfg['token']}"
    if not authorization or not service_id:
        context.abort(
            grpc.StatusCode.UNAUTHENTICATED,
            f"internal identity required for {method_name}",
        )
    if not hmac.compare_digest(authorization, expected):
        context.abort(
            grpc.StatusCode.UNAUTHENTICATED,
            f"internal identity required for {method_name}",
        )
    allowed_callers = cfg["allowed_callers"]
    assert isinstance(allowed_callers, set)
    if service_id not in allowed_callers:
        context.abort(
            grpc.StatusCode.PERMISSION_DENIED,
            f"caller not permitted for {method_name}",
        )
    return service_id, cfg


def _hex_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _float_from_digest(digest: bytes, start: int) -> float:
    if start < 0:
        start = 0
    raw = digest[start : start + 8]
    if len(raw) < 8:
        raw = (raw + b"\x00" * 8)[:8]
    return int.from_bytes(raw, byteorder="big", signed=False) / float(1 << 64)


def _confidence_from_score(score: float) -> float:
    score = max(0.0, min(1.0, score))
    confidence = 0.55 + (1.0 - abs(score - 0.5) * 2.0) * 0.45
    return round(max(0.55, min(0.99, confidence)), 6)


def _decision_from_score(score: float):
    if score >= 0.68:
        return "ADVISORY_DECISION_ACCEPT"
    if score >= 0.36:
        return "ADVISORY_DECISION_REVIEW"
    return "ADVISORY_DECISION_REJECT"


class NeuroSymbolicService:
    """Implementation of eigen.internal.v1.NeuroSymbolicService."""

    def __init__(self, nsc_pb, *, policy_snapshot_version: str | None = None):
        self._nsc_pb = nsc_pb
        self._policy_snapshot_version = (policy_snapshot_version or _active_policy_snapshot_version()).strip()
        if not self._policy_snapshot_version:
            self._policy_snapshot_version = _NEURO_POLICY_SNAPSHOT_DEFAULT

    def ScoreCompilationPlan(self, request, context: grpc.ServicerContext):
        caller_id, cfg = _require_internal_model_identity(context, method_name="ScoreCompilationPlan")
        envelope = request.envelope if request.HasField("envelope") else None
        if envelope is None or not envelope.contract_version.strip():
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "contract_version is required")
        contract_version = envelope.contract_version.strip()
        if contract_version != _NEURO_CONTRACT_VERSION:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"unsupported neuro-symbolic contract_version: {contract_version}",
            )

        req_context = request.context if request.HasField("context") else None
        if req_context is None:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "context is required")
        request_id = req_context.request_id.strip()
        tenant_id = req_context.tenant_id.strip()
        project_id = req_context.project_id.strip()
        feature_schema_version = req_context.feature_schema_version.strip()
        policy_snapshot_version = req_context.policy_snapshot_version.strip()
        subject_id = req_context.subject_id.strip()
        workload_id = req_context.workload_id.strip()
        authz_decision_id = req_context.authz_decision_id.strip()
        if not request_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "context.request_id is required")
        if not tenant_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "context.tenant_id is required")
        if not project_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "context.project_id is required")
        if not feature_schema_version:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "context.feature_schema_version is required")
        if not policy_snapshot_version:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "context.policy_snapshot_version is required")
        if not subject_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "context.subject_id is required")
        if not workload_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "context.workload_id is required")
        if not authz_decision_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "context.authz_decision_id is required")
        if not request.feature_vector:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "feature_vector is required")
        redaction = _redact_feature_vector(request.feature_vector)
        active_policy_snapshot_version = self._policy_snapshot_version
        if req_context.policy_snapshot_version.strip() != active_policy_snapshot_version:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                "context.policy_snapshot_version must match the active immutable policy snapshot",
            )
        feature_digest = request.feature_digest_sha256.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", feature_digest):
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "feature_digest_sha256 must be a SHA-256 hex digest")
        computed_digest = _hex_digest(request.feature_vector)
        if computed_digest != feature_digest:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "feature_digest_sha256 does not match feature_vector")
        deterministic_seed = int(request.deterministic_seed)
        canonical = b"|".join(
            [
                contract_version.encode("utf-8"),
                request_id.encode("utf-8"),
                tenant_id.encode("utf-8"),
                project_id.encode("utf-8"),
                subject_id.encode("utf-8"),
                workload_id.encode("utf-8"),
                authz_decision_id.encode("utf-8"),
                feature_schema_version.encode("utf-8"),
                active_policy_snapshot_version.encode("utf-8"),
                feature_digest.encode("utf-8"),
                str(deterministic_seed).encode("utf-8"),
                caller_id.encode("utf-8"),
                request.model_hint.strip().encode("utf-8"),
                redaction.feature_vector,
            ]
        )
        replay_digest = _hex_digest(canonical)
        digest_bytes = hashlib.sha256(canonical).digest()
        score = round(_float_from_digest(digest_bytes, 0), 6)
        confidence = _confidence_from_score(score)
        decision_name = _decision_from_score(score)
        decision = getattr(self._nsc_pb, decision_name)

        response = self._nsc_pb.ScoreCompilationPlanResponse(
            contract_version=contract_version,
            request_id=request_id,
            tenant_id=tenant_id,
            project_id=project_id,
            feature_schema_version=feature_schema_version,
            policy_snapshot_version=active_policy_snapshot_version,
            model_version=str(cfg["model_version"]),
            decision=decision,
            score=score,
            confidence=confidence,
            explanation_ref=f"nsc://explanations/{request_id}/{replay_digest}",
            replay_digest=replay_digest,
            deterministic_compatible=True,
            subject_id=subject_id,
            workload_id=workload_id,
            authz_decision_id=authz_decision_id,
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
                "authz_decision_id": authz_decision_id,
                "policy_snapshot_version": policy_snapshot_version,
                "feature_schema_version": feature_schema_version,
                "service_id": caller_id,
                "model_version": str(cfg["model_version"]),
                "policy_snapshot_version": active_policy_snapshot_version,
                "decision": decision_name,
                "feature_redaction_fields": redaction.redacted_fields,
                "feature_redaction_count": len(redaction.redacted_fields),
                "replay_digest": replay_digest,
                "trace_id": getattr(req_context, "trace_id", ""),
                "traceparent": getattr(req_context, "traceparent", ""),
            },
        )
        return response


_TRACEPARENT_RE = re.compile(r"^[0-9a-f]{2}-(?P<trace_id>[0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$")


def _trace_fields(context: grpc.ServicerContext) -> tuple[str | None, str | None]:
    md = {k.lower(): v for k, v in (context.invocation_metadata() or [])}
    traceparent = md.get("traceparent")
    trace_id = md.get("x-eigen-trace-id")
    if trace_id is None and traceparent:
        match = _TRACEPARENT_RE.match(traceparent)
        if match:
            trace_id = match.group("trace_id")
    return trace_id, traceparent


def _log_start(
    method: str,
    job_id: str,
    request_context: dict[str, str],
    context: grpc.ServicerContext,
) -> None:
    trace_id, traceparent = _trace_fields(context)
    _LOG.info(
        "rpc_start",
        extra={
            "rpc": method,
            "job_id": job_id,
            "request_id": request_context.get("request_id", ""),
            "trace_id": trace_id or request_context.get("trace_id", ""),
            "traceparent": traceparent or request_context.get("traceparent", ""),
            "stage": "rpc",
            "outcome": "start",
        },
    )


def _log_end(
    method: str,
    job_id: str,
    request_context: dict[str, str],
    context: grpc.ServicerContext,
    metadata: dict[str, str] | None = None,
) -> None:
    trace_id, _traceparent = _trace_fields(context)
    metadata = metadata or {}
    _LOG.info(
        "rpc_end",
        extra={
            "rpc": method,
            "job_id": job_id,
            "request_id": request_context.get("request_id", ""),
            "trace_id": trace_id or request_context.get("trace_id", ""),
            "traceparent": request_context.get("traceparent", ""),
            "stage": "rpc",
            "outcome": "success",
            "source_sha256": metadata.get("source_sha256", ""),
            "aqo_sha256": metadata.get("aqo_sha256", ""),
        },
    )
