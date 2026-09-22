"""driver-manager entrypoint for internal DriverManagerService."""


from __future__ import annotations

import json
import logging
import os
import threading
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .grpc_server import serve


_METRICS_LOCK = threading.Lock()
_REQUESTS_TOTAL = Counter()
_REQUESTS_LATENCY_MS_BUCKET = defaultdict(Counter)
_REQUESTS_LATENCY_MS_BUCKETS = (1, 5, 10, 25, 50, 100, 250, 500, 1000)
_SESSION_TOTAL = Counter()
_BACKEND_FAILURES_TOTAL = Counter()


def record_driver_request(rpc: str, code: str, duration_ms: float) -> None:
    rpc = str(rpc)
    code = str(code)
    latency_ms = max(0.0, float(duration_ms))
    with _METRICS_LOCK:
        _REQUESTS_TOTAL[(rpc, code)] += 1
        for bucket in _REQUESTS_LATENCY_MS_BUCKETS:
            if latency_ms <= bucket:
                _REQUESTS_LATENCY_MS_BUCKET[rpc][bucket] += 1
        _REQUESTS_LATENCY_MS_BUCKET[rpc]["+Inf"] += 1


def record_driver_session(driver: str, state: str) -> None:
    with _METRICS_LOCK:
        _SESSION_TOTAL[(str(driver), str(state))] += 1


def record_backend_failure(component: str, taxonomy: str) -> None:
    with _METRICS_LOCK:
        _BACKEND_FAILURES_TOTAL[(str(component), str(taxonomy))] += 1


def render_metrics_text() -> str:
    with _METRICS_LOCK:
        lines = [
            '# TYPE eigen_driver_requests_total counter',
            '# TYPE eigen_driver_request_latency_ms_bucket counter',
            '# TYPE eigen_driver_sessions counter',
            '# TYPE eigen_driver_backend_failures_total counter',
        ]
        for (rpc, code), count in sorted(_REQUESTS_TOTAL.items()):
            lines.append(f'eigen_driver_requests_total{{rpc="{rpc}",code="{code}"}} {count}')
        for rpc, buckets in sorted(_REQUESTS_LATENCY_MS_BUCKET.items()):
            for bucket, count in buckets.items():
                lines.append(f'eigen_driver_request_latency_ms_bucket{{rpc="{rpc}",le="{bucket}"}} {count}')
        for (driver, state), count in sorted(_SESSION_TOTAL.items()):
            lines.append(f'eigen_driver_sessions{{driver="{driver}",state="{state}"}} {count}')
        for (component, taxonomy), count in sorted(_BACKEND_FAILURES_TOTAL.items()):
            lines.append(f'eigen_driver_backend_failures_total{{component="{component}",taxonomy="{taxonomy}"}} {count}')
        return "\n".join(lines) + "\n"


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "service": "driver-manager",
            "message": record.getMessage(),
        }
        for field in ("trace_id", "job_id", "traceparent", "method", "rpc_method", "grpc_status", "error_reason", "artifact_ref"):
            value = getattr(record, field, None)
            if value:
                payload[field] = value
        return json.dumps(payload)


_metrics = {"requests_total": 0}
_metrics_lock = threading.Lock()
_health_state = {"registry": None}


class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            body = render_metrics_text().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/healthz":
            registry = _health_state["registry"]
            if registry is None:
                payload = {"ready": False, "reason": "registry is not initialized"}
                body = json.dumps(payload).encode("utf-8")
                self.send_response(503)
            else:
                health = registry.health_snapshot()
                ready = all(item.ready for item in health.values()) if health else False
                payload = {
                    "ready": ready,
                    "drivers": {
                        name: {
                            "ready": info.ready,
                            "reason": info.reason,
                            "details": info.details,
                        }
                        for name, info in health.items()
                    },
                    "capabilities": {
                        name: {
                            "driver_api_version": caps.driver_api_version,
                            "features": caps.features,
                        }
                        for name, caps in registry.capability_snapshot().items()
                    },
                }
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200 if ready else 503)

            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        
        self.send_response(404)
        self.end_headers()

    def log_message(self, *_args, **_kwargs):
        return


def _start_metrics_server(port: int) -> None:
    server = ThreadingHTTPServer(("0.0.0.0", port), _MetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()


def main() -> int:
    root = logging.getLogger()
    root.setLevel(os.getenv("DRIVER_MANAGER_LOG_LEVEL", "INFO"))
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root.handlers[:] = [handler]
    _start_metrics_server(int(os.getenv("DRIVER_MANAGER_METRICS_PORT", "9092")))

    server = serve()
    _health_state["registry"] = getattr(server, "driver_registry", None)
    server.wait_for_termination()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
