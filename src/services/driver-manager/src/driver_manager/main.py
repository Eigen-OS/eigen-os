"""driver-manager entrypoint for internal DriverManagerService."""


from __future__ import annotations

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .grpc_server import serve


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "service": "driver-manager",
            "message": record.getMessage(),
        }
        for field in ("trace_id", "job_id", "traceparent", "method"):
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
            with _metrics_lock:
                total = _metrics["requests_total"]
            body = f"# TYPE eigen_driver_requests_total counter\neigen_driver_requests_total {total}\n".encode()
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
