"""neuro-symbolic-service entrypoint."""

from __future__ import annotations

import logging
import os

from .grpc_server import serve
from .observability import JsonFormatter, start_metrics_server


def main() -> int:
    level = os.getenv("NEURO_SYMBOLIC_LOG_LEVEL", "INFO")
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers[:] = [handler]

    metrics_port = int(os.getenv("NEURO_SYMBOLIC_METRICS_PORT", "50082"))
    start_metrics_server(metrics_port)

    server = serve()
    server.wait_for_termination()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
