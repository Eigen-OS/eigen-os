"""Minimal observability helpers for System API."""

from __future__ import annotations

import logging
import json
import re
import threading
import time
import uuid
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import grpc

_LOG = logging.getLogger("system_api")
_AUDIT_LOG = logging.getLogger("system_api.security_audit")
_AUDIT_LOCK = threading.Lock()
_AUDIT_SINK_PATH = os.getenv("SYSTEM_API_AUDIT_SINK_PATH", "/tmp/eigen-system-api-audit.jsonl")

_TRACEPARENT_RE = re.compile(
    r"^(?P<version>[0-9a-f]{2})-(?P<trace_id>[0-9a-f]{32})-(?P<span_id>[0-9a-f]{16})-(?P<trace_flags>[0-9a-f]{2})$"
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
        for field in ("trace_id", "job_id", "traceparent", "method", "request_id", "subject", "permission", "policy_version", "service_identity", "sandbox_profile", "replay_marker", "auth_mode"):
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


def append_security_audit_event(event: dict[str, object]) -> None:
    """Append-only audit sink for security decisions.

    The file is never truncated; every record is written as one JSON line.
    """
    record = json.dumps(event, sort_keys=True, separators=(",", ":"))
    line = record + "\n"
    with _AUDIT_LOCK:
        os.makedirs(os.path.dirname(_AUDIT_SINK_PATH), exist_ok=True)
        with open(_AUDIT_SINK_PATH, "a", encoding="utf-8") as fh:
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
        _MetricsState.submit_job_outcomes_total[outcome] = (
            _MetricsState.submit_job_outcomes_total.get(outcome, 0) + 1
        )


def record_public_api_contract_marker(contract_version: str, outcome: str) -> None:
    """Increment the public-boundary contract marker metric with bounded labels."""
    version_label = (
        contract_version if contract_version in PUBLIC_API_CONTRACT_VERSION_LABELS else "unsupported"
    )
    outcome_label = outcome if outcome in PUBLIC_API_CONTRACT_OUTCOMES else "error"
    with _MetricsState.lock:
        _MetricsState.public_api_contract_requests_total[(version_label, outcome_label)] = (
            _MetricsState.public_api_contract_requests_total.get((version_label, outcome_label), 0)
            + 1
        )
