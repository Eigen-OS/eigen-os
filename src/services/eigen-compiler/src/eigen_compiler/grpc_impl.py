"""gRPC implementation for internal CompilationService."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import logging
import importlib.util
import os
from pathlib import Path
import re
import sys
import threading
import types
from time import perf_counter
from typing import Callable

import grpc

from google.protobuf.timestamp_pb2 import Timestamp


def _find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "proto").is_dir() and (candidate / "src" / "services").is_dir():
            return candidate
    raise RuntimeError("Could not locate repo root (expected proto/ and src/services/)")


_REPO_ROOT = _find_repo_root(Path(__file__).resolve())
_NEURO_API_ROOT = _REPO_ROOT / "src" / "services" / "neuro-symbolic-service" / "src" / "eigen" / "api" / "v1"


def _ensure_package(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is not None:
        return module  # type: ignore[return-value]
    module = types.ModuleType(name)
    module.__path__ = []  # type: ignore[attr-defined]
    sys.modules[name] = module
    parent_name, _, child_name = name.rpartition(".")
    if parent_name:
        parent = _ensure_package(parent_name)
        setattr(parent, child_name, module)
    return module


def _load_module(module_name: str, file_path: Path) -> types.ModuleType:
    module = sys.modules.get(module_name)
    if module is not None:
        return module  # type: ignore[return-value]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    parent_name, _, child_name = module_name.rpartition(".")
    if parent_name:
        parent = _ensure_package(parent_name)
        setattr(parent, child_name, module)
    return module  # type: ignore[return-value]


_ensure_package("eigen.api")
_ensure_package("eigen.api.v1")
api_types_pb2 = _load_module("eigen.api.v1.types_pb2", _NEURO_API_ROOT / "types_pb2.py")
kb_pb = _load_module("eigen.api.v1.knowledge_base_service_pb2", _NEURO_API_ROOT / "knowledge_base_service_pb2.py")
kb_pb_grpc = _load_module("eigen.api.v1.knowledge_base_service_pb2_grpc", _NEURO_API_ROOT / "knowledge_base_service_pb2_grpc.py")

from .compiler import (
    CompilerValidationError,
    compile_eigen_lang,
    _normalize_options,
    _normalize_request_context,
    _resolve_source_bytes,
)
from .errors import abort_invalid_argument, annotate_violations
from .validation import validate_compile_circuit, validate_compile_job


_LOG = logging.getLogger("eigen_compiler")

_METRIC_LOCK = threading.Lock()
_RPC_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_STAGE_COUNT_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_STAGE_SECONDS_TOTALS: defaultdict[tuple[tuple[str, str], ...], float] = defaultdict(float)
_VALIDATION_FAILURE_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_AQO_DIGEST_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_REPLAY_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_EVALUATION_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_EVALUATION_LATENCY_SECONDS_COUNT_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_EVALUATION_LATENCY_SECONDS_SUM_TOTALS: defaultdict[tuple[tuple[str, str], ...], float] = defaultdict(float)
_SEEN_AQO_DIGESTS: set[str] = set()
_OBSERVABILITY_CONTRACT_VERSION = "1.0.0"
_REWRITE_OUTCOME_TAXONOMY = ("accepted", "rejected", "equivalent", "unsafe")

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
    "body",
    "debug_trace",
    "full_request_body",
    "headers",
    "http_headers",
    "large_trace_dump",
    "metadata",
    "payload",
    "raw_payload",
    "raw_request_body",
    "request_body",
    "stack_trace",
    "trace_dump",
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
_PHONE_RE = re.compile(r"(?i)(?<!\d)(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?){1,3}\d{2,4}(?!\d)")
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}\b")
_UUID_RE = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
_SENSITIVE_HEADER_LINE_RE = re.compile(
    r"(?im)^(?P<name>authorization|proxy-authorization|x-api-key|x-auth-token|x-access-token|cookie|set-cookie)\s*:\s*(?P<value>.+)$"
)
_INTERNAL_ENDPOINT_RE = re.compile(
    r"(?i)\b(?:https?|grpc)://"
    r"(?:"
    r"localhost"
    r"|127\.0\.0\.1"
    r"|0\.0\.0\.0"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|(?!-)(?:[a-z0-9-]+\.)*(?:internal|cluster\.local|svc\.cluster\.local|localdomain|corp|lan)"
    r")(?::\d+)?(?:/[^\s\"'<>]*)?"
)
_SECRET_PATH_RE = re.compile(
    r"(?i)(?P<path>(?:[A-Za-z]:\\|/)"
    r"(?:[^\s\"'<>]*/)*"
    r"(?:secrets?|secret|private|credentials?|tokens?|keys?)"
    r"(?:/[^\s\"'<>]*)?)"
)
_STACK_TRACE_MARKERS = (
    "Traceback (most recent call last):",
    "java.lang.",
    "Caused by:",
)
_STACK_TRACE_LINE_RE = re.compile(r"(?m)^\s*File \".+\", line \d+, in .+$|^\s*at [\w.$<>/]+\(.*\)$")


@dataclass(frozen=True)
class FeatureRedactionResult:
    feature_vector: bytes
    redacted_fields: tuple[str, ...]

_STAGE_LABELS = {
    "request_validation",
    "parse",
    "semantic_validation",
    "lowering_validation",
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


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _normalize_rewrite_outcome(value: object, *, field_name: str) -> str:
    text = str(value).strip().lower()
    if text not in _REWRITE_OUTCOME_TAXONOMY:
        allowed = ", ".join(_REWRITE_OUTCOME_TAXONOMY)
        raise ValueError(f"{field_name} must be one of: {allowed}")
    return text


def _rewrite_outcome_for_candidate(
    candidate: dict[str, object],
    *,
    selected: bool,
    result_present: bool,
    candidate_legal: bool,
) -> str:
    explicit = candidate.get("rewrite_outcome")
    if explicit not in (None, ""):
        return _normalize_rewrite_outcome(explicit, field_name="candidate.rewrite_outcome")
    if bool(candidate.get("unsafe", False)) or str(candidate.get("safety_status", "")).strip().lower() == "unsafe":
        return "unsafe"
    if bool(candidate.get("equivalent", False)) or str(candidate.get("rewrite_relation", "")).strip().lower() == "equivalent":
        return "equivalent"
    if selected and candidate_legal and result_present:
        return "accepted"
    return "rejected"


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


def _record_evaluation_metrics(
    *,
    compiler_version: str,
    job_type: str,
    decision_source: str,
    elapsed_seconds: float,
) -> None:
    labels = _label_tuple(
        compiler_version=compiler_version,
        job_type=job_type,
        decision_source=decision_source,
    )
    with _METRIC_LOCK:
        _EVALUATION_TOTALS[labels] += 1
        _EVALUATION_LATENCY_SECONDS_COUNT_TOTALS[labels] += 1
        _EVALUATION_LATENCY_SECONDS_SUM_TOTALS[labels] += elapsed_seconds


def reset_metrics() -> None:
    with _METRIC_LOCK:
        _RPC_TOTALS.clear()
        _STAGE_COUNT_TOTALS.clear()
        _STAGE_SECONDS_TOTALS.clear()
        _VALIDATION_FAILURE_TOTALS.clear()
        _AQO_DIGEST_TOTALS.clear()
        _REPLAY_TOTALS.clear()
        _EVALUATION_TOTALS.clear()
        _EVALUATION_LATENCY_SECONDS_COUNT_TOTALS.clear()
        _EVALUATION_LATENCY_SECONDS_SUM_TOTALS.clear()
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


def _diagnostic_stage(violations) -> str:
    for violation in violations:
        if getattr(violation, "stage", ""):
            return str(violation.stage)
    return "request_validation"


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
        lines.extend(_render_counter_family("eigen_compiler_evaluation_total", _EVALUATION_TOTALS))
        lines.extend(_render_counter_family("eigen_compiler_evaluation_latency_seconds_count", _EVALUATION_LATENCY_SECONDS_COUNT_TOTALS))
        lines.append("# TYPE eigen_compiler_evaluation_latency_seconds_sum counter")
        for labels, value in sorted(_EVALUATION_LATENCY_SECONDS_SUM_TOTALS.items(), key=lambda item: item[0]):
            lines.append(f"eigen_compiler_evaluation_latency_seconds_sum{_fmt_labels(labels)} {value:.9f}")
        return "\n".join(lines) + "\n"


_KB_GRPC_ENDPOINT_ENV = "EIGEN_KB_GRPC_ENDPOINT"
_KB_AUTH_TOKEN_ENV = "EIGEN_KB_AUTH_TOKEN"
_KB_SERVICE_IDENTITY_ENV = "EIGEN_KB_SERVICE_IDENTITY"
_KB_SERVICE_ROLE_ENV = "EIGEN_KB_SERVICE_ROLE"
_KB_ROLES_ENV = "EIGEN_KB_ROLES"
_KB_TIMEOUT_SECONDS_ENV = "EIGEN_KB_TIMEOUT_SECONDS"
_DEFAULT_KB_TIMEOUT_SECONDS = 2.0


def _kb_timeout_seconds() -> float:
    raw = os.getenv(_KB_TIMEOUT_SECONDS_ENV, str(_DEFAULT_KB_TIMEOUT_SECONDS)).strip()
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_KB_TIMEOUT_SECONDS
    return max(0.1, value)


def _request_timeout_seconds(request_context: dict[str, str]) -> float:
    """Return a bounded timeout for best-effort KB RPCs.

    The compiler must not let slow advisory side effects exceed the request
    deadline when one is available, but it also must keep a minimum budget so
    very small deadlines do not result in an immediate failure path.
    """

    deadline = str(request_context.get("deadline", "")).strip()
    timeout = _kb_timeout_seconds()
    if not deadline:
        return timeout

    parsed_deadline: float | None = None
    if deadline.endswith("s"):
        try:
            parsed_deadline = float(deadline[:-1])
        except ValueError:
            parsed_deadline = None
    elif ":" in deadline:
        try:
            days = 0
            time_part = deadline
            if " day" in deadline:
                day_part, time_part = deadline.split(",", 1)
                days = int(day_part.split()[0])
                time_part = time_part.strip()
            hours, minutes, seconds = time_part.split(":", 2)
            parsed_deadline = (
                days * 86400
                + int(hours) * 3600
                + int(minutes) * 60
                + float(seconds)
            )
        except Exception:
            parsed_deadline = None

    if parsed_deadline is None:
        return timeout
    return max(0.1, min(timeout, parsed_deadline))


def _kb_call_metadata(request_context: dict[str, str]) -> tuple[tuple[str, str], ...]:
    token = os.getenv(_KB_AUTH_TOKEN_ENV, os.getenv("SYSTEM_API_AUTH_TOKEN", "")).strip()
    roles = os.getenv(_KB_ROLES_ENV, "kb:read,kb:write").strip() or "kb:read,kb:write"
    service_identity = os.getenv(_KB_SERVICE_IDENTITY_ENV, "eigen-compiler").strip() or "eigen-compiler"
    service_role = os.getenv(_KB_SERVICE_ROLE_ENV, "internal-ingest").strip() or "internal-ingest"
    metadata: list[tuple[str, str]] = []
    if token:
        metadata.append(("authorization", f"Bearer {token}"))
    tenant_id = request_context.get("tenant_id", "").strip()
    if tenant_id:
        metadata.append(("x-eigen-tenant", tenant_id))
    if roles:
        metadata.append(("x-eigen-roles", roles))
    metadata.append(("x-eigen-service", service_identity))
    metadata.append(("x-eigen-service-role", service_role))
    sandbox_profile = request_context.get("sandbox_profile", "").strip()
    if sandbox_profile:
        metadata.append(("x-eigen-sandbox-profile", sandbox_profile))
    return tuple(metadata)


def _kb_request_envelope(request_context: dict[str, str]) -> kb_pb.ApiContractEnvelope:
    return kb_pb.ApiContractEnvelope(
        contract_version="1.0.0",
        request=api_types_pb2.ApiRequestEnvelope(
            contract_version="1.0.0",
            request_id=request_context.get("request_id", "").strip(),
            traceparent=request_context.get("traceparent", "").strip(),
            tenant_id=request_context.get("tenant_id", "").strip(),
            project_id=request_context.get("project_id", "").strip(),
            client_version="eigen-compiler/1.0.0",
        ),
    )


def _timestamp_now() -> Timestamp:
    ts = Timestamp()
    ts.FromDatetime(datetime.now(timezone.utc))
    return ts


def _selected_candidate_signature(candidate_set: dict[str, object]) -> str:
    if not isinstance(candidate_set, dict):
        return ""

    ranked_candidates = candidate_set.get("ranked_candidates", [])
    for candidate in ranked_candidates:
        if not isinstance(candidate, dict) or not candidate.get("legal", True):
            continue
        candidate_kind = candidate.get("features", {}).get("candidate_kind") if isinstance(candidate.get("features"), dict) else ""
        if candidate_kind == "terminal_measurement_normalized":
            candidate_id = str(candidate.get("candidate_id", "")).strip()
            if candidate_id:
                return candidate_id

    candidates = candidate_set.get("candidates", [])
    legal_candidates = [candidate for candidate in candidates if isinstance(candidate, dict) and candidate.get("legal")]
    for candidate in legal_candidates:
        candidate_kind = candidate.get("features", {}).get("candidate_kind") if isinstance(candidate.get("features"), dict) else ""
        if candidate_kind == "terminal_measurement_normalized":
            candidate_id = str(candidate.get("candidate_id", "")).strip()
            if candidate_id:
                return candidate_id

    selected_candidate_id = str(candidate_set.get("selected_candidate_id", "")).strip()
    if selected_candidate_id:
        return selected_candidate_id

    for candidate in ranked_candidates:
        if not isinstance(candidate, dict) or not candidate.get("legal", True):
            continue
        candidate_id = str(candidate.get("candidate_id", "")).strip()
        if candidate_id:
            return candidate_id
    if legal_candidates:
        return str(legal_candidates[0].get("candidate_id", "")).strip()
    if candidates:
        first = candidates[0]
        if isinstance(first, dict):
            return str(first.get("candidate_id", "")).strip()
    return ""


def _compiler_decision_source(candidate_set: dict[str, object], *, default: str = "symbolic_rules") -> str:
    if not isinstance(candidate_set, dict):
        return default

    explicit = str(candidate_set.get("decision_source", "")).strip()
    if explicit:
        return explicit

    ranker = candidate_set.get("ranker", {})
    if isinstance(ranker, dict):
        source = str(ranker.get("decision_source", "")).strip()
        if source:
            return source
        model_family = str(ranker.get("model_family", "")).strip().lower()
        fallback_used = bool(ranker.get("fallback_used", False))
        if fallback_used:
            return "fallback"
        if model_family in {"gnn", "graph_neural_network"} or "gnn" in model_family:
            return "gnn_ranking"
        if model_family in {"boosting", "boosted", "gradient_boosting", "xgboost", "lightgbm", "catboost"} or any(
            token in model_family for token in ("boost", "xgb", "lgbm", "cat")
        ):
            return "boosting_ranking"
    return default


def _trace_digest_payload(
    *,
    rpc: str,
    request_id: str,
    trace_id: str,
    source_sha256: str,
    request_sha256: str,
    aqo_sha256: str,
    pattern_signature: str,
    compiler_status: str,
    snapshot_id: str = "",
    model_snapshot_id: str = "",
    model_snapshot_digest: str = "",
    kb_version: str = "",
    kb_snapshot_id: str = "",
    kb_snapshot_digest: str = "",
    policy_mode: str = "",
    policy_snapshot_version: str = "",
    policy_snapshot_id: str = "",
    policy_digest: str = "",
    failure_stage: str = "",
    failure_reason: str = "",
    compiler_replay_sha256: str = "",
    compiler_diagnostics_sha256: str = "",
    decision_source: str = "",
) -> dict[str, str]:
    return {
        "rpc": rpc,
        "request_id": request_id,
        "trace_id": trace_id,
        "source_sha256": source_sha256,
        "request_sha256": request_sha256,
        "aqo_sha256": aqo_sha256,
        "pattern_signature": pattern_signature,
        "compiler_status": compiler_status,
        "snapshot_id": snapshot_id,
        "model_snapshot_id": model_snapshot_id,
        "model_snapshot_digest": model_snapshot_digest,
        "kb_version": kb_version,
        "kb_snapshot_id": kb_snapshot_id,
        "kb_snapshot_digest": kb_snapshot_digest,
        "policy_mode": policy_mode,
        "policy_snapshot_version": policy_snapshot_version,
        "policy_snapshot_id": policy_snapshot_id,
        "policy_digest": policy_digest,
        "failure_stage": failure_stage,
        "failure_reason": failure_reason,
        "compiler_replay_sha256": compiler_replay_sha256,
        "compiler_diagnostics_sha256": compiler_diagnostics_sha256,
        "decision_source": decision_source,
    }


def _canonical_compiler_trace_digest(payload: dict[str, str]) -> str:
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def _kb_index_compiler_trace(
    *,
    rpc: str,
    request_context: dict[str, str],
    source_digest: str,
    result: CompilationResult | None,
    failure_stage: str = "",
    failure_reason: str = "",
) -> None:
    endpoint = os.getenv(_KB_GRPC_ENDPOINT_ENV, "").strip()
    if not endpoint:
        return

    timeout_seconds = _request_timeout_seconds(request_context)

    try:
        channel = grpc.insecure_channel(endpoint)
        stub = kb_pb_grpc.KnowledgeBaseServiceStub(channel)
    except Exception as exc:  # pragma: no cover - best-effort indexing
        _LOG.debug("compiler KB channel unavailable: %s", exc)
        return

    try:
        metadata = result.metadata if result is not None else {}
        request_sha256 = str(metadata.get("request_sha256", "") if metadata else "").strip()
        aqo_sha256 = str(metadata.get("aqo_sha256", "") if metadata else "").strip()
        compiler_replay_sha256 = str(metadata.get("compiler_replay_sha256", "") if metadata else "").strip()
        compiler_diagnostics_json = str(metadata.get("compiler_diagnostics_json", "") if metadata else "").strip()
        compiler_diagnostics_sha256 = hashlib.sha256(compiler_diagnostics_json.encode("utf-8")).hexdigest() if compiler_diagnostics_json else ""
        candidate_set_json = str(metadata.get("symbolic_candidate_set_json", "") if metadata else "").strip()
        telemetry_feature_set_json = str(metadata.get("telemetry_feature_set_json", "") if metadata else "").strip()
        telemetry_feature_set_sha256 = str(metadata.get("telemetry_feature_set_sha256", "") if metadata else "").strip()
        snapshot_id = str(metadata.get("snapshot_id", "") if metadata else "").strip()
        model_snapshot_id = str(metadata.get("model_snapshot_id", metadata.get("model_version", os.getenv(_NEURO_MODEL_VERSION_ENV, "dpda-model-v1"))) if metadata else os.getenv(_NEURO_MODEL_VERSION_ENV, "dpda-model-v1")).strip() or os.getenv(_NEURO_MODEL_VERSION_ENV, "dpda-model-v1")
        model_snapshot_digest = str(metadata.get("model_snapshot_digest", "") if metadata else "").strip()
        kb_version = str(metadata.get("kb_version", _KB_CONTRACT_VERSION) if metadata else _KB_CONTRACT_VERSION).strip() or _KB_CONTRACT_VERSION
        kb_snapshot_id = str(metadata.get("kb_snapshot_id", kb_version) if metadata else kb_version).strip() or kb_version
        kb_snapshot_digest = str(metadata.get("kb_snapshot_digest", "") if metadata else "").strip()
        policy_mode = str(metadata.get("policy_mode", "deterministic") if metadata else "deterministic").strip() or "deterministic"
        policy_snapshot_version = str(metadata.get("policy_snapshot_version", _NEURO_POLICY_SNAPSHOT_DEFAULT) if metadata else _NEURO_POLICY_SNAPSHOT_DEFAULT).strip() or _NEURO_POLICY_SNAPSHOT_DEFAULT
        policy_snapshot_id = str(metadata.get("policy_snapshot_id", policy_snapshot_version) if metadata else policy_snapshot_version).strip() or policy_snapshot_version
        policy_digest = str(metadata.get("policy_digest", "") if metadata else "").strip()
        candidate_set = json.loads(candidate_set_json) if candidate_set_json else {"candidate_count": 0, "candidates": []}
        decision_source = _compiler_decision_source(
            candidate_set,
            default=str(metadata.get("decision_source", "") if metadata else "").strip() or "symbolic_rules",
        )
        candidate_entries = candidate_set.get("candidates", []) if isinstance(candidate_set, dict) else []
        pattern_signature = _selected_candidate_signature(candidate_set) if result is not None else f"failure:{failure_stage or 'compile'}"
        trace_payload = _trace_digest_payload(
            rpc=rpc,
            request_id=request_context.get("request_id", ""),
            trace_id=request_context.get("trace_id", ""),
            source_sha256=source_digest,
            request_sha256=request_sha256,
            aqo_sha256=aqo_sha256,
            pattern_signature=pattern_signature,
            compiler_status="success" if result is not None else "failure",
            snapshot_id=snapshot_id,
            model_snapshot_id=model_snapshot_id,
            model_snapshot_digest=model_snapshot_digest,
            kb_version=kb_version,
            kb_snapshot_id=kb_snapshot_id,
            kb_snapshot_digest=kb_snapshot_digest,
            policy_mode=policy_mode,
            policy_snapshot_version=policy_snapshot_version,
            policy_snapshot_id=policy_snapshot_id,
            policy_digest=policy_digest,
            failure_stage=failure_stage,
            failure_reason=failure_reason,
            compiler_replay_sha256=compiler_replay_sha256,
            compiler_diagnostics_sha256=compiler_diagnostics_sha256,
            decision_source=decision_source,
        )
        trace_digest = _canonical_compiler_trace_digest(trace_payload)

        candidate_ids = [str(candidate.get("candidate_id", "")).strip() for candidate in candidate_entries if isinstance(candidate, dict)]
        accepted = [pattern_signature] if pattern_signature else []
        rejected = [candidate_id for candidate_id in candidate_ids if candidate_id and candidate_id != pattern_signature]

        record_id = f"compiler-trace:{request_context.get('trace_id', '') or request_context.get('request_id', '')}:{trace_digest[:16]}"
        record = kb_pb.KnowledgeRecord(
            record_id=record_id,
            job_id=str(request_context.get("request_id", "").strip()),
            circuit_id=str(request_context.get("source_ref", "").strip()),
            artifact_ref=f"compiler-trace://{trace_digest}",
            dataset_ref="compiler-traces",
            backend_profile=str(metadata.get("workload_profile", "compiler")) if metadata else "compiler",
            optimizer_version=model_snapshot_id,
            qubit_count=int(candidate_entries[0].get("features", {}).get("qubits", 0) or 0) if candidate_entries else 0,
            entanglement_score=0.0,
            noise_profile_id="",
            backend_class=str(metadata.get("workload_profile", "compiler")) if metadata else "compiler",
            created_at=_timestamp_now(),
            provenance=kb_pb.RecordProvenance(
                compiler_ref=f"compiler://{request_context.get('trace_id', '') or request_context.get('request_id', '')}",
                optimizer_ref=f"pattern://{pattern_signature}" if pattern_signature else "",
                runtime_ref="",
                checkpoint_ref=f"trace-digest://{trace_digest}",
            ),
            attributes={
                "trace_id": request_context.get("trace_id", "").strip(),
                "request_id": request_context.get("request_id", "").strip(),
                "trace_digest_sha256": trace_digest,
                "pattern_signature": pattern_signature,
                "compiler_status": "success" if result is not None else "failure",
                "decision_source": decision_source,
                "failure_stage": failure_stage,
                "failure_reason": failure_reason,
                "source_sha256": source_digest,
                "request_sha256": request_sha256,
                "aqo_sha256": aqo_sha256,
                "snapshot_id": snapshot_id,
                "model_version": model_snapshot_id,
                "model_snapshot_id": model_snapshot_id,
                "model_snapshot_digest": model_snapshot_digest,
                "kb_version": kb_version,
                "kb_snapshot_id": kb_snapshot_id,
                "kb_snapshot_digest": kb_snapshot_digest,
                "policy_mode": policy_mode,
                "policy_snapshot_version": policy_snapshot_version,
                "policy_snapshot_id": policy_snapshot_id,
                "policy_digest": policy_digest,
                "compiler_replay_sha256": compiler_replay_sha256,
                "compiler_diagnostics_sha256": compiler_diagnostics_sha256,
                "symbolic_candidate_set_sha256": str(metadata.get("symbolic_candidate_set_sha256", "")).strip() if metadata else "",
                "telemetry_feature_set_json": telemetry_feature_set_json,
                "telemetry_feature_set_sha256": telemetry_feature_set_sha256,
                "accepted_rewrite_ids": _stable_json(accepted),
                "rejected_rewrite_ids": _stable_json(rejected),
                "selected_candidate_id": pattern_signature,
                "compiler_pass_pipeline_version": str(metadata.get("compiler_pass_pipeline_version", "1.0.0")).strip() if metadata else "1.0.0",
                "workload_profile": str(metadata.get("workload_profile", "")).strip() if metadata else "",
                "source_precedence": str(metadata.get("source_precedence", "")).strip() if metadata else "",
            },
            lineage=kb_pb.ModelLineage(
                model_version=model_snapshot_id,
                training_set_hash=request_sha256 or trace_digest,
                evaluation_bundle_hash=compiler_replay_sha256 or compiler_diagnostics_sha256,
                promotion_policy_version=policy_snapshot_version,
                promotion_outcome="PROMOTED" if result is not None else "REJECTED",
            ),
        )

        request_envelope = _kb_request_envelope(request_context)

        try:
            stub.UpsertRecord(
                kb_pb.UpsertRecordRequest(
                    envelope=request_envelope,
                    record=record,
                    allow_overwrite=True,
                ),
                metadata=_kb_call_metadata(request_context),
                timeout=timeout_seconds,
            )
        except Exception as exc:  # pragma: no cover - best-effort indexing
            _LOG.debug("compiler KB upsert timed out or failed: %s", exc)
            return

        for candidate in candidate_entries:
            if not isinstance(candidate, dict):
                continue
            candidate_id = str(candidate.get("candidate_id", "")).strip()
            candidate_legal = bool(candidate.get("legal", False))
            rewrite_outcome = _rewrite_outcome_for_candidate(
                candidate,
                selected=candidate_id == pattern_signature,
                result_present=result is not None,
                candidate_legal=candidate_legal,
            )
            accepted = [candidate_id] if candidate_legal and candidate_id == pattern_signature and result is not None else []
            rejected = [candidate_id] if candidate_id and candidate_id != pattern_signature else []
            feature_snapshot = {
                "trace_id": request_context.get("trace_id", "").strip(),
                "request_id": request_context.get("request_id", "").strip(),
                "trace_digest_sha256": trace_digest,
                "pattern_signature": candidate_id,
                "rewrite_outcome": rewrite_outcome,
                "selected": "true" if candidate_id == pattern_signature and rewrite_outcome == "accepted" else "false",
                "candidate_legal": "true" if candidate_legal else "false",
                "candidate_features": _stable_json(candidate.get("features", {})),
                "source_sha256": source_digest,
                "request_sha256": request_sha256,
                "aqo_sha256": aqo_sha256,
                "snapshot_id": snapshot_id,
                "model_version": model_snapshot_id,
                "model_snapshot_id": model_snapshot_id,
                "model_snapshot_digest": model_snapshot_digest,
                "kb_version": kb_version,
                "kb_snapshot_id": kb_snapshot_id,
                "kb_snapshot_digest": kb_snapshot_digest,
                "policy_mode": policy_mode,
                "policy_snapshot_version": policy_snapshot_version,
                "policy_snapshot_id": policy_snapshot_id,
                "policy_digest": policy_digest,
                "compiler_replay_sha256": compiler_replay_sha256,
                "compiler_diagnostics_sha256": compiler_diagnostics_sha256,
                "symbolic_candidate_set_sha256": str(metadata.get("symbolic_candidate_set_sha256", "")).strip() if metadata else "",
                "telemetry_feature_set_json": telemetry_feature_set_json,
                "telemetry_feature_set_sha256": telemetry_feature_set_sha256,
                "compiler_status": "success" if result is not None else "failure",
                "decision_source": decision_source,
                "accepted_rewrite_ids": _stable_json(accepted),
                "rejected_rewrite_ids": _stable_json(rejected),
                "failure_stage": failure_stage,
                "failure_reason": failure_reason,
            }
            decision_log = kb_pb.DecisionLog(
                decision_id=f"compiler-rewrite:{request_context.get('trace_id', '') or request_context.get('request_id', '')}:{candidate_id}",
                trace_id=request_context.get("trace_id", "").strip(),
                model_version=model_snapshot_id,
                component="compiler",
                policy_branch="symbolic_rewrite",
                selected_action=candidate_id,
                fallback_used=not candidate_legal or candidate_id != pattern_signature or result is None,
                feature_snapshot=feature_snapshot,
                decided_at=_timestamp_now(),
            )
            try:
                stub.AppendDecisionLog(
                    kb_pb.AppendDecisionLogRequest(
                        envelope=request_envelope,
                        decision_log=decision_log,
                    ),
                    metadata=_kb_call_metadata(request_context),
                    timeout=timeout_seconds,
                )
            except Exception as exc:  # pragma: no cover - best-effort indexing
                _LOG.debug("compiler KB decision log append timed out or failed: %s", exc)
                return
    except Exception as exc:  # pragma: no cover - best-effort indexing
        _LOG.debug("compiler KB indexing failed: %s", exc)
    finally:
        try:
            channel.close()
        except Exception:
            pass


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

    security_context = pick("security_context", "authorization")
    if security_context:
        security_context = _redact_scalar_text(security_context, "$.security_context", set())

    return {
        "request_id": pick("request_id", "x-eigen-request-id"),
        "trace_id": pick("trace_id", "x-eigen-trace-id"),
        "traceparent": pick("traceparent", "traceparent"),
        "deadline": deadline,
        "retry_policy": pick("retry_policy", "x-eigen-retry-policy"),
        "security_context": security_context,
        "sandbox_profile": pick("sandbox_profile", "x-eigen-sandbox-profile"),
        "tenant_id": pick("tenant_id", "x-eigen-tenant-id"),
        "project_id": pick("project_id", "x-eigen-project-id"),
    }


def _circuit_format_value(types_pb, *names: str) -> int:
    for name in names:
        if hasattr(types_pb, name):
            return int(getattr(types_pb, name))
    raise AttributeError(f"None of the enum names exist: {names}")


def _workload_kind_name(raw_kind: object) -> str | None:
    kind_aliases = {
        1: "QuantumJob",
        2: "HybridWorkflow",
        3: "DistributedJob",
        4: "BenchmarkJob",
        5: "PipelineJob",
        6: "ReplayJob",
        "QuantumJob": "QuantumJob",
        "HybridWorkflow": "HybridWorkflow",
        "DistributedJob": "DistributedJob",
        "BenchmarkJob": "BenchmarkJob",
        "PipelineJob": "PipelineJob",
        "ReplayJob": "ReplayJob",
        "WORKLOAD_FAMILY_KIND_QUANTUM_JOB": "QuantumJob",
        "WORKLOAD_FAMILY_KIND_HYBRID_WORKFLOW": "HybridWorkflow",
        "WORKLOAD_FAMILY_KIND_DISTRIBUTED_JOB": "DistributedJob",
        "WORKLOAD_FAMILY_KIND_BENCHMARK_JOB": "BenchmarkJob",
        "WORKLOAD_FAMILY_KIND_PIPELINE_JOB": "PipelineJob",
        "WORKLOAD_FAMILY_KIND_REPLAY_JOB": "ReplayJob",
    }
    if raw_kind in (None, "", 0):
        return None
    try:
        return kind_aliases[int(raw_kind)]
    except Exception:
        return kind_aliases.get(raw_kind)


def _request_metadata_workload_options(request_metadata) -> dict[str, str]:
    workload = getattr(request_metadata, "workload", None)
    kind = _workload_kind_name(getattr(workload, "kind", None))
    if kind is None:
        return {}

    options: dict[str, str] = {"spec.workload.kind": kind}
    backend_target = str(getattr(workload, "backend_target", "") or "").strip()
    if backend_target:
        options["spec.workload.backend_target"] = backend_target
    execution_profile = str(getattr(workload, "execution_profile", "") or "").strip()
    if execution_profile:
        options["spec.workload.execution_profile"] = execution_profile
    replayable = getattr(workload, "replayable", None)
    if replayable is not None:
        options["spec.workload.replayable"] = "true" if bool(replayable) else "false"
    return options


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
        normalized_options = _normalize_options(options)
        raw_request_context = request_context or {}
        request_context_payload = {
            "request_id": str(raw_request_context.get("request_id", "")).strip(),
            "trace_id": str(raw_request_context.get("trace_id", "")).strip(),
            "traceparent": str(raw_request_context.get("traceparent", "")).strip(),
            "deadline": str(raw_request_context.get("deadline", "")).strip(),
            "retry_policy": str(raw_request_context.get("retry_policy", "")).strip(),
            "security_context": str(raw_request_context.get("security_context", "")).strip(),
            "sandbox_profile": str(raw_request_context.get("sandbox_profile", "strict")).strip() or "strict",
            "tenant_id": str(raw_request_context.get("tenant_id", "")).strip(),
            "project_id": str(raw_request_context.get("project_id", "")).strip(),
        }

        source_digest = hashlib.sha256(
            source if source else (str(source_ref or "").encode("utf-8") if source_ref else b"")
        ).hexdigest()

        try:
            normalized_request_context = _normalize_request_context(request_context)
            request_context_payload.update(
                {
                    "request_id": normalized_request_context.request_id,
                    "trace_id": normalized_request_context.trace_id,
                    "traceparent": normalized_request_context.traceparent,
                    "deadline": normalized_request_context.deadline,
                    "retry_policy": normalized_request_context.retry_policy,
                    "security_context": normalized_request_context.security_context,
                    "sandbox_profile": normalized_request_context.sandbox_profile,
                    "tenant_id": normalized_request_context.tenant_id,
                    "project_id": normalized_request_context.project_id,
                }
            )
            resolved_source, _source_precedence = _resolve_source_bytes(source, source_ref)
            source_digest = hashlib.sha256(resolved_source).hexdigest()

            result = compile_eigen_lang(
                source,
                source_ref=source_ref,
                options=normalized_options,
                request_context=request_context_payload,
                observer=self._stage_observer(
                    rpc=rpc,
                    request_context=request_context_payload,
                ),
            )
        except CompilerValidationError as exc:
            _kb_index_compiler_trace(
                rpc=rpc,
                request_context=request_context_payload,
                source_digest=source_digest,
                result=None,
                failure_stage=_diagnostic_stage(exc.violations),
                failure_reason=_validation_reason(exc.violations),
            )
            raise
        except Exception as exc:  # pragma: no cover - best-effort indexing
            _kb_index_compiler_trace(
                rpc=rpc,
                request_context=request_context_payload,
                source_digest=source_digest,
                result=None,
                failure_stage="internal",
                failure_reason=type(exc).__name__,
            )
            raise

        _kb_index_compiler_trace(
            rpc=rpc,
            request_context=request_context_payload,
            source_digest=source_digest,
            result=result,
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

        violations = annotate_violations(
            validate_compile_circuit(request),
            stage="request_validation",
            rule="compiler.request.validation",
            pass_name="request_validation",
        )

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

        options = _request_metadata_workload_options(getattr(request, "request_metadata", None))
        options.update({str(k): str(v) for k, v in dict(request.options).items()})
        try:
            compile_started = perf_counter()
            resp = self._compile_response(
                rpc="CompileCircuit",
                source=source,
                source_ref=source_ref,
                options=options,
                request_context=request_context,
            )

            _record_rpc("CompileCircuit", "success")

            _record_evaluation_metrics(
                compiler_version=str(resp.metadata.get("compiler_contract_version", "1.0.0")).strip() or "1.0.0",
                job_type=str(resp.metadata.get("workload_profile", "unknown")).strip() or "unknown",
                decision_source=str(resp.metadata.get("decision_source", "symbolic_rules")).strip() or "symbolic_rules",
                elapsed_seconds=perf_counter() - compile_started,
            )

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
                _diagnostic_stage(exc.violations),
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

        violations = annotate_violations(
            validate_compile_job(request),
            stage="request_validation",
            rule="compiler.request.validation",
            pass_name="request_validation",
        )

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

        options = _request_metadata_workload_options(getattr(request, "request_metadata", None))
        options.update({str(k): str(v) for k, v in dict(request.options).items()})
        try:
            compile_started = perf_counter()
            compiled = self._compile_response(
                rpc="CompileJob",
                source=source,
                source_ref=source_ref,
                options=options,
                request_context=request_context,
            )

        except CompilerValidationError as exc:
            _record_rpc("CompileJob", "failure")

            _record_validation_failure(
                _diagnostic_stage(exc.violations),
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

        _record_evaluation_metrics(
            compiler_version=str(compiled.metadata.get("compiler_contract_version", "1.0.0")).strip() or "1.0.0",
            job_type=str(compiled.metadata.get("workload_profile", "unknown")).strip() or "unknown",
            decision_source=str(compiled.metadata.get("decision_source", "symbolic_rules")).strip() or "symbolic_rules",
            elapsed_seconds=perf_counter() - compile_started,
        )
        
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
_KB_CONTRACT_VERSION = "1.0.0"
_NEURO_MAX_FEATURE_VECTOR_BYTES_ENV = "EIGEN_NEURO_SYMBOLIC_MAX_FEATURE_VECTOR_BYTES"
_NEURO_MAX_FEATURE_VECTOR_BYTES_DEFAULT = 65536


def _redaction_path(parent: str, key: str) -> str:
    if not parent or parent == "$":
        return f"$.{key}"
    return f"{parent}.{key}"


def _record_redaction(redactions: set[str], path: str, reason: str) -> None:
    redactions.add(f"{path}:{reason}")


def _looks_like_stack_trace(value: str) -> bool:
    if any(marker in value for marker in _STACK_TRACE_MARKERS):
        return True
    return _STACK_TRACE_LINE_RE.search(value) is not None


def _redact_sensitive_text(value: str, path: str, redactions: set[str]) -> str:
    redacted = value

    if _SENSITIVE_HEADER_LINE_RE.search(redacted):
        redacted = _SENSITIVE_HEADER_LINE_RE.sub(_REDACTED_VALUE, redacted)
        _record_redaction(redactions, path, "masked_header")
    if _INTERNAL_ENDPOINT_RE.search(redacted):
        redacted = _INTERNAL_ENDPOINT_RE.sub(_REDACTED_VALUE, redacted)
        _record_redaction(redactions, path, "masked_endpoint")
    if _SECRET_PATH_RE.search(redacted):
        redacted = _SECRET_PATH_RE.sub(_REDACTED_VALUE, redacted)
        _record_redaction(redactions, path, "masked_path")

    return redacted

def _redact_scalar_text(value: str, path: str, redactions: set[str]) -> str:
    redacted = value

    if _looks_like_stack_trace(redacted):
        _record_redaction(redactions, path, "deleted")
        return _REDACTED_VALUE

    if _BEARER_RE.search(redacted):
        redacted = _BEARER_RE.sub(_REDACTED_VALUE, redacted)
        _record_redaction(redactions, path, "deleted")
    redacted = _redact_sensitive_text(redacted, path, redactions)
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


def _feature_vector_byte_limit() -> int:
    raw_limit = os.getenv(
        _NEURO_MAX_FEATURE_VECTOR_BYTES_ENV,
        str(_NEURO_MAX_FEATURE_VECTOR_BYTES_DEFAULT),
    ).strip()
    if not raw_limit:
        return _NEURO_MAX_FEATURE_VECTOR_BYTES_DEFAULT
    try:
        return max(0, int(raw_limit))
    except ValueError:
        return _NEURO_MAX_FEATURE_VECTOR_BYTES_DEFAULT


def _neuro_metadata(context: grpc.ServicerContext) -> dict[str, str]:
    return {k.lower(): v for k, v in (context.invocation_metadata() or [])}


def _require_tenant_project_binding(
    context: grpc.ServicerContext,
    *,
    method_name: str,
    tenant_id: str,
    project_id: str,
) -> None:
    md = _neuro_metadata(context)
    md_tenant_id = md.get("x-eigen-tenant-id", "").strip()
    md_project_id = md.get("x-eigen-project-id", "").strip()
    if not md_tenant_id or not md_project_id:
        context.abort(
            grpc.StatusCode.PERMISSION_DENIED,
            f"tenant/project binding required for {method_name}",
        )
    if md_tenant_id != tenant_id or md_project_id != project_id:
        context.abort(
            grpc.StatusCode.PERMISSION_DENIED,
            f"tenant/project scope mismatch for {method_name}",
        )


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


def _explainability_feature_set(
    *,
    feature_schema_version: str,
    model_hint: str,
    feature_digest_sha256: str,
    minimized_feature_vector: bytes,
    redacted_fields: tuple[str, ...],
) -> dict[str, object]:
    return {
        "schema_version": feature_schema_version,
        "model_hint": model_hint.strip(),
        "feature_digest_sha256": feature_digest_sha256,
        "minimized_feature_vector_sha256": _hex_digest(minimized_feature_vector),
        "minimized_feature_vector_bytes": len(minimized_feature_vector),
        "redacted_fields": list(redacted_fields),
    }


def _build_explainability_envelope(
    *,
    contract_version: str,
    request_id: str,
    tenant_id: str,
    project_id: str,
    feature_schema_version: str,
    policy_snapshot_version: str,
    model_version: str,
    confidence: float,
    feature_digest_sha256: str,
    replay_digest: str,
    minimized_feature_vector: bytes,
    redacted_fields: tuple[str, ...],
    model_hint: str,
) -> dict[str, object]:
    feature_set = _explainability_feature_set(
        feature_schema_version=feature_schema_version,
        model_hint=model_hint,
        feature_digest_sha256=feature_digest_sha256,
        minimized_feature_vector=minimized_feature_vector,
        redacted_fields=redacted_fields,
    )
    retrieval_references = [
        f"nsc://feature-set/{tenant_id}/{project_id}/{request_id}/{feature_digest_sha256}",
        f"nsc://policy-snapshot/{policy_snapshot_version}",
        f"nsc://model/{model_version}",
    ]
    return {
        "contract_version": contract_version,
        "request_id": request_id,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "policy_snapshot_version": policy_snapshot_version,
        "model_version": model_version,
        "confidence": round(float(confidence), 6),
        "feature_set": feature_set,
        "retrieval_references": retrieval_references,
        "retrieval_reference_count": len(retrieval_references),
        "replay_digest": replay_digest,
        "decision_digest": replay_digest,
        "explanation_ref": f"nsc://explanations/{request_id}/{replay_digest}",
    }


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
        _require_tenant_project_binding(
            context,
            method_name="ScoreCompilationPlan",
            tenant_id=tenant_id,
            project_id=project_id,
        )
        if not request.feature_vector:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "feature_vector is required")
        raw_feature_digest = _hex_digest(request.feature_vector)
        redaction = _redact_feature_vector(request.feature_vector)
        feature_vector = redaction.feature_vector
        feature_vector_limit = _feature_vector_byte_limit()
        if len(feature_vector) > feature_vector_limit:
            context.abort(
                grpc.StatusCode.RESOURCE_EXHAUSTED,
                f"feature_vector exceeds policy size limit ({len(feature_vector)} > {feature_vector_limit})",
            )
        active_policy_snapshot_version = self._policy_snapshot_version
        if req_context.policy_snapshot_version.strip() != active_policy_snapshot_version:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                "context.policy_snapshot_version must match the active immutable policy snapshot",
            )
        feature_digest = request.feature_digest_sha256.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", feature_digest):
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "feature_digest_sha256 must be a SHA-256 hex digest")
        computed_digest = _hex_digest(feature_vector)
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
                feature_vector,
            ]
        )
        replay_digest = _hex_digest(canonical)
        digest_bytes = hashlib.sha256(canonical).digest()
        score = round(_float_from_digest(digest_bytes, 0), 6)
        confidence = _confidence_from_score(score)
        decision_name = _decision_from_score(score)
        decision = getattr(self._nsc_pb, decision_name)
        model_version = str(cfg["model_version"])
        explainability_envelope = _build_explainability_envelope(
            contract_version=contract_version,
            request_id=request_id,
            tenant_id=tenant_id,
            project_id=project_id,
            feature_schema_version=feature_schema_version,
            policy_snapshot_version=active_policy_snapshot_version,
            model_version=model_version,
            confidence=confidence,
            feature_digest_sha256=raw_feature_digest,
            replay_digest=replay_digest,
            minimized_feature_vector=feature_vector,
            redacted_fields=redaction.redacted_fields,
            model_hint=request.model_hint.strip(),
        )

        response = self._nsc_pb.ScoreCompilationPlanResponse(
            contract_version=contract_version,
            request_id=request_id,
            tenant_id=tenant_id,
            project_id=project_id,
            feature_schema_version=feature_schema_version,
            policy_snapshot_version=active_policy_snapshot_version,
            model_version=model_version,
            decision=decision,
            score=score,
            confidence=confidence,
            explanation_ref=explainability_envelope["explanation_ref"],
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
                "model_version": model_version,
                "decision": decision_name,
                "feature_payload_bytes": len(request.feature_vector),
                "feature_payload_minimized_bytes": len(feature_vector),
                "feature_payload_limit_bytes": feature_vector_limit,
                "feature_redaction_fields": redaction.redacted_fields,
                "feature_redaction_count": len(redaction.redacted_fields),
                "replay_digest": replay_digest,
                "explainability_envelope": explainability_envelope,
                "explainability_envelope_json": _stable_json(explainability_envelope),
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
            "decision_source": metadata.get("decision_source", ""),
            "source_sha256": metadata.get("source_sha256", ""),
            "aqo_sha256": metadata.get("aqo_sha256", ""),
        },
    )
