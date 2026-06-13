"""Minimal observability helpers for System API."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import grpc

_LOG = logging.getLogger("system_api")
_AUDIT_LOG = logging.getLogger("system_api.security_audit")
_AUDIT_LOCK = threading.Lock()

_TRACEPARENT_RE = re.compile(
    r"^(?P<version>[0-9a-f]{2})-(?P<trace_id>[0-9a-f]{32})-(?P<span_id>[0-9a-f]{16})-(?P<trace_flags>[0-9a-f]{2})$"
)

_KB_CONTRACT_VERSION = "1.0.0"
_KB_QUERY_KINDS = (
    "records",
    "decision_logs",
    "benchmark_runs",
    "runtime_decisions",
    "learning_evidence",
    "learning_datasets",
    "learning_models",
    "learning_promotions",
    "learning_rollbacks",
)
_KB_FALLBACK_REASONS = (
    "storage_unavailable",
    "replay_validation_failed",
    "ingest_failed",
)
_KB_QUARANTINE_SURFACES = (
    "runtime",
    "benchmark",
    "learning",
    "dataset",
    "model",
    "promotion",
    "rollback",
)
_KB_FAILURE_REASONS = (
    "decision_log_pressure",
    "dataset_assembly",
    "training",
    "evaluation",
    "promotion",
    "rollback",
    "ingest",
)


@dataclass
class RequestContext:
    request_id: str
    traceparent: str | None
    trace_id: str | None
    job_id: str | None = None
    subject: str | None = None
    roles: tuple[str, ...] | None = None
    auth_mode: str | None = None
    policy_version: str | None = None
    service_identity: str | None = None
    sandbox_profile: str | None = None
    replay_marker: str | None = None


class JsonFormatter(logging.Formatter):
    """JSON log formatter with stable schema for MVP observability."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "service": "system-api",
            "message": record.getMessage(),
        }
        for field in (
            "trace_id",
            "job_id",
            "traceparent",
            "method",
            "request_id",
            "subject",
            "permission",
            "policy_version",
            "service_identity",
            "sandbox_profile",
            "replay_marker",
            "auth_mode",
        ):
            value = getattr(record, field, None)
            if value:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False)


PUBLIC_API_CONTRACT_OUTCOMES = {"accepted", "replayed", "conflict", "limit", "error"}
PUBLIC_API_CONTRACT_VERSION_LABELS = {"1.0.0", "unsupported"}


class _MetricsState:
    lock = threading.Lock()
    requests_total = 0
    request_duration_seconds_sum = 0.0
    authz_denied_total = 0
    submit_job_outcomes_total: dict[str, int] = {
        "accepted": 0,
        "replayed": 0,
        "conflict": 0,
        "limit": 0,
    }
    public_api_contract_requests_total: dict[tuple[str, str], int] = {
        (version, outcome): 0
        for version in sorted(PUBLIC_API_CONTRACT_VERSION_LABELS)
        for outcome in sorted(PUBLIC_API_CONTRACT_OUTCOMES)
    }
    kb_contract_info = {(_KB_CONTRACT_VERSION): 1}
    kb_queries_total: dict[str, int] = {kind: 0 for kind in _KB_QUERY_KINDS}
    kb_hits_total: dict[str, int] = {kind: 0 for kind in _KB_QUERY_KINDS}
    kb_misses_total: dict[str, int] = {kind: 0 for kind in _KB_QUERY_KINDS}
    kb_fallbacks_total: dict[str, int] = {reason: 0 for reason in _KB_FALLBACK_REASONS}
    kb_quarantine_total: dict[str, int] = {surface: 0 for surface in _KB_QUARANTINE_SURFACES}
    kb_learning_failures_total: dict[str, int] = {reason: 0 for reason in _KB_FAILURE_REASONS}
    kb_replay_failures_total = 0
    kb_contract_requests_total: dict[tuple[str, str], int] = {
        (version, outcome): 0
        for version in sorted(PUBLIC_API_CONTRACT_VERSION_LABELS)
        for outcome in sorted(PUBLIC_API_CONTRACT_OUTCOMES)
    }


class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        with _MetricsState.lock:
            req_total = _MetricsState.requests_total
            req_sum = _MetricsState.request_duration_seconds_sum
            authz_denied = _MetricsState.authz_denied_total
            submit_outcomes = dict(_MetricsState.submit_job_outcomes_total)
            public_contract_outcomes = dict(_MetricsState.public_api_contract_requests_total)
            kb_contract_info = dict(_MetricsState.kb_contract_info)
            kb_queries = dict(_MetricsState.kb_queries_total)
            kb_hits = dict(_MetricsState.kb_hits_total)
            kb_misses = dict(_MetricsState.kb_misses_total)
            kb_fallbacks = dict(_MetricsState.kb_fallbacks_total)
            kb_quarantine = dict(_MetricsState.kb_quarantine_total)
            kb_learning_failures = dict(_MetricsState.kb_learning_failures_total)
            kb_replay_failures = _MetricsState.kb_replay_failures_total
            kb_contract_outcomes = dict(_MetricsState.kb_contract_requests_total)

        outcome_lines = "".join(
            f'eigen_api_submit_job_outcomes_total{{outcome="{outcome}"}} {count}\n'
            for outcome, count in sorted(submit_outcomes.items())
        )
        contract_marker_lines = "".join(
            (
                "eigen_api_public_contract_requests_total"
                f'{{contract_version="{contract_version}",outcome="{outcome}"}} {count}\n'
            )
            for (contract_version, outcome), count in sorted(public_contract_outcomes.items())
        )
        public_api_contract_marker_lines = "".join(
            (
                "eigen_public_api_contract_requests_total"
                f'{{contract_version="{contract_version}",outcome="{outcome}"}} {count}\n'
            )
            for (contract_version, outcome), count in sorted(public_contract_outcomes.items())
        )
        kb_query_lines = "".join(
            f'eigen_kb_queries_total{{kind="{kind}"}} {count}\n'
            for kind, count in sorted(kb_queries.items())
        )
        kb_hit_lines = "".join(
            f'eigen_kb_hits_total{{kind="{kind}"}} {count}\n'
            for kind, count in sorted(kb_hits.items())
        )
        kb_miss_lines = "".join(
            f'eigen_kb_misses_total{{kind="{kind}"}} {count}\n'
            for kind, count in sorted(kb_misses.items())
        )
        kb_fallback_lines = "".join(
            f'eigen_kb_fallbacks_total{{reason="{reason}"}} {count}\n'
            for reason, count in sorted(kb_fallbacks.items())
        )
        kb_quarantine_lines = "".join(
            f'eigen_kb_quarantine_total{{surface="{surface}"}} {count}\n'
            for surface, count in sorted(kb_quarantine.items())
        )
        kb_learning_failure_lines = "".join(
            f'eigen_kb_learning_failures_total{{reason="{reason}"}} {count}\n'
            for reason, count in sorted(kb_learning_failures.items())
        )
        kb_contract_marker_lines = "".join(
            (
                "eigen_kb_contract_requests_total"
                f'{{contract_version="{contract_version}",outcome="{outcome}"}} {count}\n'
            )
            for (contract_version, outcome), count in sorted(kb_contract_outcomes.items())
        )
        kb_contract_info_lines = "".join(
            f'eigen_kb_contract_info{{version="{version}"}} {value}\n'
            for version, value in sorted(kb_contract_info.items())
        )
        body = (
            "# TYPE eigen_api_requests_total counter\n"
            f"eigen_api_requests_total {req_total}\n"
            "# TYPE eigen_api_request_duration_seconds counter\n"
            f"eigen_api_request_duration_seconds {req_sum:.6f}\n"
            "# TYPE eigen_api_authz_denied_total counter\n"
            f"eigen_api_authz_denied_total {authz_denied}\n"
            "# TYPE eigen_api_submit_job_outcomes_total counter\n"
            f"{outcome_lines}"
            "# TYPE eigen_api_public_contract_requests_total counter\n"
            f"{contract_marker_lines}"
            "# TYPE eigen_public_api_contract_requests_total counter\n"
            f"{public_api_contract_marker_lines}"
            "# TYPE eigen_kb_contract_info gauge\n"
            f"{kb_contract_info_lines}"
            "# TYPE eigen_kb_queries_total counter\n"
            f"{kb_query_lines}"
            "# TYPE eigen_kb_hits_total counter\n"
            f"{kb_hit_lines}"
            "# TYPE eigen_kb_misses_total counter\n"
            f"{kb_miss_lines}"
            "# TYPE eigen_kb_fallbacks_total counter\n"
            f"{kb_fallback_lines}"
            "# TYPE eigen_kb_quarantine_total counter\n"
            f"{kb_quarantine_lines}"
            "# TYPE eigen_kb_learning_failures_total counter\n"
            f"{kb_learning_failure_lines}"
            "# TYPE eigen_kb_replay_failures_total counter\n"
            f"eigen_kb_replay_failures_total {kb_replay_failures}\n"
            "# TYPE eigen_kb_contract_requests_total counter\n"
            f"{kb_contract_marker_lines}"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args, **_kwargs):  # pragma: no cover
        return


def start_metrics_server(port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", port), _MetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _audit_sink_path() -> str:
    raw = os.getenv("SYSTEM_API_AUDIT_SINK_PATH", "").strip()
    if raw:
        return raw
    tmpdir = os.getenv("TMPDIR", "/tmp").strip() or "/tmp"
    return os.path.join(tmpdir, "system-api", "audit.jsonl")


def append_security_audit_event(event: dict[str, object]) -> None:
    """Append-only audit sink for security decisions.

    The file is never truncated; every record is written as one JSON line.
    """
    record = json.dumps(event, sort_keys=True, separators=(",", ":"))
    line = record + "\n"
    sink_path = _audit_sink_path()
    with _AUDIT_LOCK:
        os.makedirs(os.path.dirname(sink_path), exist_ok=True)
        with open(sink_path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
    _AUDIT_LOG.info("security_audit", extra=event)


def trace_id_from_traceparent(traceparent: str | None) -> str | None:
    if not traceparent:
        return None
    m = _TRACEPARENT_RE.match(traceparent)
    if not m:
        return None
    return m.group("trace_id")


def sanitized_security_metadata(*, subject: str, roles: tuple[str, ...], auth_mode: str, policy_version: str, service_identity: str | None, sandbox_profile: str | None, replay_marker: str | None) -> dict[str, object]:
    return {
        "subject": subject,
        "roles": ",".join(roles),
        "auth_mode": auth_mode,
        "policy_version": policy_version,
        "service_identity": service_identity or "",
        "sandbox_profile": sandbox_profile or "",
        "replay_marker": replay_marker or "",
    }


def new_request_context(context: grpc.ServicerContext) -> RequestContext:
    md = {k.lower(): v for (k, v) in (context.invocation_metadata() or [])}

    traceparent = md.get("traceparent")
    trace_id = md.get("trace_id") or trace_id_from_traceparent(traceparent)

    return RequestContext(
        request_id=str(uuid.uuid4()),
        traceparent=traceparent,
        trace_id=trace_id,
        replay_marker=md.get("x-eigen-replay-marker"),
    )


def log_request_start(method: str, rc: RequestContext) -> None:
    setattr(rc, "_started_at", time.perf_counter())
    _LOG.info(
        "rpc_start",
        extra={
            "method": method,
            "request_id": rc.request_id,
            "trace_id": rc.trace_id,
            "traceparent": rc.traceparent,
            "job_id": rc.job_id,
        },
    )


def log_request_end(method: str, rc: RequestContext) -> None:
    elapsed = max(time.perf_counter() - getattr(rc, "_started_at", time.perf_counter()), 0.0)
    with _MetricsState.lock:
        _MetricsState.requests_total += 1
        _MetricsState.request_duration_seconds_sum += elapsed
    _LOG.info(
        "rpc_end",
        extra={
            "method": method,
            "request_id": rc.request_id,
            "trace_id": rc.trace_id,
            "job_id": rc.job_id,
        },
    )


def log_authz_denied(*, method: str, subject: str, permission: str, job_id: str | None = None) -> None:
    with _MetricsState.lock:
        _MetricsState.authz_denied_total += 1
    _LOG.warning(
        "authz_denied",
        extra={
            "method": method,
            "subject": subject,
            "permission": permission,
            "job_id": job_id,
        },
    )


def record_submit_job_outcome(outcome: str) -> None:
    """Increment bounded-label SubmitJob outcome metrics."""
    if outcome not in {"accepted", "replayed", "conflict", "limit"}:
        outcome = "limit"
    with _MetricsState.lock:
        _MetricsState.submit_job_outcomes_total[outcome] = _MetricsState.submit_job_outcomes_total.get(outcome, 0) + 1


def record_public_api_contract_marker(contract_version: str, outcome: str) -> None:
    """Increment the public-boundary contract marker metric with bounded labels."""
    version_label = contract_version if contract_version in PUBLIC_API_CONTRACT_VERSION_LABELS else "unsupported"
    outcome_label = outcome if outcome in PUBLIC_API_CONTRACT_OUTCOMES else "error"
    with _MetricsState.lock:
        _MetricsState.public_api_contract_requests_total[(version_label, outcome_label)] = (
            _MetricsState.public_api_contract_requests_total.get((version_label, outcome_label), 0) + 1
        )


def record_kb_query(kind: str, *, hit: bool) -> None:
    kind_label = kind if kind in _MetricsState.kb_queries_total else "records"
    with _MetricsState.lock:
        _MetricsState.kb_queries_total[kind_label] = _MetricsState.kb_queries_total.get(kind_label, 0) + 1
        if hit:
            _MetricsState.kb_hits_total[kind_label] = _MetricsState.kb_hits_total.get(kind_label, 0) + 1
        else:
            _MetricsState.kb_misses_total[kind_label] = _MetricsState.kb_misses_total.get(kind_label, 0) + 1


def record_kb_fallback(reason: str) -> None:
    reason_label = reason if reason in _MetricsState.kb_fallbacks_total else "ingest_failed"
    with _MetricsState.lock:
        _MetricsState.kb_fallbacks_total[reason_label] = _MetricsState.kb_fallbacks_total.get(reason_label, 0) + 1


def record_kb_quarantine_event(surface: str) -> None:
    surface_label = surface if surface in _MetricsState.kb_quarantine_total else "learning"
    with _MetricsState.lock:
        _MetricsState.kb_quarantine_total[surface_label] = _MetricsState.kb_quarantine_total.get(surface_label, 0) + 1


def record_kb_learning_failure(reason: str) -> None:
    reason_label = reason if reason in _MetricsState.kb_learning_failures_total else "ingest"
    with _MetricsState.lock:
        _MetricsState.kb_learning_failures_total[reason_label] = _MetricsState.kb_learning_failures_total.get(reason_label, 0) + 1


def record_kb_replay_failure() -> None:
    with _MetricsState.lock:
        _MetricsState.kb_replay_failures_total += 1


def record_kb_contract_marker(contract_version: str, outcome: str) -> None:
    version_label = contract_version if contract_version in PUBLIC_API_CONTRACT_VERSION_LABELS else "unsupported"
    outcome_label = outcome if outcome in PUBLIC_API_CONTRACT_OUTCOMES else "error"
    with _MetricsState.lock:
        _MetricsState.kb_contract_requests_total[(version_label, outcome_label)] = (
            _MetricsState.kb_contract_requests_total.get((version_label, outcome_label), 0) + 1
        )
