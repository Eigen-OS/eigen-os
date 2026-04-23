"""Minimal observability helpers for System API."""

from __future__ import annotations

import logging
import json
import re
import threading
import time
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import grpc

_LOG = logging.getLogger("system_api")

_TRACEPARENT_RE = re.compile(
    r"^(?P<version>[0-9a-f]{2})-(?P<trace_id>[0-9a-f]{32})-(?P<span_id>[0-9a-f]{16})-(?P<trace_flags>[0-9a-f]{2})$"
)


@dataclass
class RequestContext:
    request_id: str
    traceparent: str | None
    trace_id: str | None
    job_id: str | None = None


class JsonFormatter(logging.Formatter):
    """JSON log formatter with stable schema for MVP observability."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "service": "system-api",
            "message": record.getMessage(),
        }
        for field in ("trace_id", "job_id", "traceparent", "method", "request_id"):
            value = getattr(record, field, None)
            if value:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False)


class _MetricsState:
    lock = threading.Lock()
    requests_total = 0
    request_duration_seconds_sum = 0.0


class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        with _MetricsState.lock:
            req_total = _MetricsState.requests_total
            req_sum = _MetricsState.request_duration_seconds_sum
        body = (
            "# TYPE eigen_api_requests_total counter\n"
            f"eigen_api_requests_total {req_total}\n"
            "# TYPE eigen_api_request_duration_seconds counter\n"
            f"eigen_api_request_duration_seconds {req_sum:.6f}\n"
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


def new_request_context(context: grpc.ServicerContext) -> RequestContext:
    md = {k.lower(): v for (k, v) in (context.invocation_metadata() or [])}

    traceparent = md.get("traceparent")
    trace_id = md.get("trace_id")

    if trace_id is None and traceparent:
        m = _TRACEPARENT_RE.match(traceparent)
        if m:
            trace_id = m.group("trace_id")

    return RequestContext(
        request_id=str(uuid.uuid4()),
        traceparent=traceparent,
        trace_id=trace_id,
    )


def log_request_start(method: str, rc: RequestContext) -> None:
    setattr(rc, "_started_at", time.perf_counter())
    _LOG.info("rpc_start", extra={"method": method, "request_id": rc.request_id, "trace_id": rc.trace_id, "traceparent": rc.traceparent, "job_id": rc.job_id})


def log_request_end(method: str, rc: RequestContext) -> None:
    elapsed = max(time.perf_counter() - getattr(rc, "_started_at", time.perf_counter()), 0.0)
    with _MetricsState.lock:
        _MetricsState.requests_total += 1
        _MetricsState.request_duration_seconds_sum += elapsed
    _LOG.info("rpc_end", extra={"method": method, "request_id": rc.request_id, "trace_id": rc.trace_id, "job_id": rc.job_id})

