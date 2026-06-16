from __future__ import annotations

import json
import logging
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_METRICS_LOCK = threading.Lock()
_REQUESTS_TOTAL = Counter()
_DENIALS_TOTAL = Counter()
_DECISIONS_TOTAL = Counter()
_READY = False
_CONTRACT_VERSION = "1.0.0"


def set_ready(ready: bool) -> None:
    global _READY
    with _METRICS_LOCK:
        _READY = bool(ready)


def record_request(outcome: str) -> None:
    with _METRICS_LOCK:
        _REQUESTS_TOTAL[str(outcome)] += 1


def record_denial(reason: str) -> None:
    with _METRICS_LOCK:
        _DENIALS_TOTAL[str(reason)] += 1


def record_decision(decision: str) -> None:
    with _METRICS_LOCK:
        _DECISIONS_TOTAL[str(decision)] += 1


def render_metrics_text() -> str:
    with _METRICS_LOCK:
        lines = [
            '# TYPE eigen_observability_contract_info gauge',
            f'eigen_observability_contract_info{{version="{_CONTRACT_VERSION}"}} 1',
            '# TYPE eigen_neuro_requests_total counter',
            '# TYPE eigen_neuro_denials_total counter',
            '# TYPE eigen_neuro_decisions_total counter',
        ]
        for outcome, count in sorted(_REQUESTS_TOTAL.items()):
            lines.append(f'eigen_neuro_requests_total{{outcome="{outcome}"}} {count}')
        for reason, count in sorted(_DENIALS_TOTAL.items()):
            lines.append(f'eigen_neuro_denials_total{{reason="{reason}"}} {count}')
        for decision, count in sorted(_DECISIONS_TOTAL.items()):
            lines.append(f'eigen_neuro_decisions_total{{decision="{decision}"}} {count}')
        return "\n".join(lines) + "\n"


class JsonFormatter(logging.Formatter):
    def format(self, record):  # type: ignore[override]
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "service": "neuro-symbolic-service",
            "message": record.getMessage(),
        }
        for field in (
            "rpc",
            "request_id",
            "tenant_id",
            "project_id",
            "subject_id",
            "workload_id",
            "policy_snapshot_version",
            "model_version",
            "decision",
            "caller_id",
            "trace_id",
            "traceparent",
        ):
            value = getattr(record, field, None)
            if value:
                payload[field] = value
        return json.dumps(payload)


class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            body = render_metrics_text().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/healthz":
            with _METRICS_LOCK:
                ready = _READY
            body = json.dumps({"ready": ready}).encode("utf-8")
            self.send_response(200 if ready else 503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, *_args, **_kwargs):  # pragma: no cover
        return


def start_metrics_server(port: int) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), _MetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()


_AUDIT_LOCK = threading.Lock()
_KB_LOCK = threading.Lock()
_KB_QUERY_TOTAL = Counter()
_KB_FALLBACK_TOTAL = Counter()
_KB_REPLAY_FAILURES = 0
_KB_CONTRACT_TOTAL = Counter()


def _audit_sink_path() -> str:
    import os
    raw = os.getenv("NEURO_SYMBOLIC_AUDIT_SINK_PATH", "").strip() or os.getenv("SYSTEM_API_AUDIT_SINK_PATH", "").strip()
    if raw:
        return raw
    tmpdir = os.getenv("TMPDIR", "/tmp").strip() or "/tmp"
    return os.path.join(tmpdir, "neuro-symbolic-service", "audit.jsonl")


def append_security_audit_event(event: dict[str, object]) -> None:
    import json
    import os

    record = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    sink_path = _audit_sink_path()
    with _AUDIT_LOCK:
        os.makedirs(os.path.dirname(sink_path), exist_ok=True)
        with open(sink_path, "a", encoding="utf-8") as fh:
            fh.write(record + "\n")
            fh.flush()
            os.fsync(fh.fileno())


def trace_id_from_traceparent(traceparent: str | None) -> str | None:
    import re
    if not traceparent:
        return None
    match = re.match(r"^\s*00-(?P<trace_id>[0-9a-f]{32})-[0-9a-f]{16}-0[01]\s*$", traceparent, re.IGNORECASE)
    if not match:
        return None
    return match.group("trace_id")


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


def log_authz_denied(*, method: str, subject: str, permission: str, job_id: str | None = None, trace_id: str | None = None, traceparent: str | None = None) -> None:
    _LOG.warning(
        "authz_denied",
        extra={
            "method": method,
            "subject": subject,
            "permission": permission,
            "job_id": job_id,
            "trace_id": trace_id,
            "traceparent": traceparent,
        },
    )


def record_kb_query(kind: str, *, hit: bool) -> None:
    with _KB_LOCK:
        _KB_QUERY_TOTAL[kind] += 1
        if hit:
            _KB_QUERY_TOTAL[f"{kind}:hit"] += 1
        else:
            _KB_QUERY_TOTAL[f"{kind}:miss"] += 1


def record_kb_fallback(reason: str) -> None:
    with _KB_LOCK:
        _KB_FALLBACK_TOTAL[reason] += 1


def record_kb_replay_failure() -> None:
    global _KB_REPLAY_FAILURES
    with _KB_LOCK:
        _KB_REPLAY_FAILURES += 1


def record_kb_contract_marker(contract_version: str, outcome: str) -> None:
    with _KB_LOCK:
        _KB_CONTRACT_TOTAL[(contract_version or "unsupported", outcome or "error")] += 1
