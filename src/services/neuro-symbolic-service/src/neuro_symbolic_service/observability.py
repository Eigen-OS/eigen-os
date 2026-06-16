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
