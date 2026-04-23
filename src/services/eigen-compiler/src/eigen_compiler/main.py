"""eigen-compiler entrypoint."""

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
            "service": "eigen-compiler",
            "message": record.getMessage(),
        }
        for field in ("trace_id", "job_id", "traceparent", "method"):
            value = getattr(record, field, None)
            if value:
                payload[field] = value
        return json.dumps(payload)

_metrics = {"requests_total": 0}
_metrics_lock = threading.Lock()


class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        with _metrics_lock:
            total = _metrics["requests_total"]
        body = f"# TYPE eigen_compiler_requests_total counter\neigen_compiler_requests_total {total}\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args, **_kwargs):
        return


def _start_metrics_server(port: int) -> None:
    server = ThreadingHTTPServer(("0.0.0.0", port), _MetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()


def main() -> int:
    root = logging.getLogger()
    root.setLevel(os.getenv("EIGEN_COMPILER_LOG_LEVEL", "INFO"))
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root.handlers[:] = [handler]
    _start_metrics_server(int(os.getenv("EIGEN_COMPILER_METRICS_PORT", "9093")))
    server = serve()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:  # pragma: no cover
        server.stop(grace=0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
