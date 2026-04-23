"""system-api entrypoint.

In Phase 0 (MVP) this service is the **public ingress** to Eigen OS.

Issue #24 implements a minimal gRPC server skeleton exposing:
- eigen.api.v1.JobService
- eigen.api.v1.DeviceService

See:
- rfcs/0004-public-gRPC-API-v0.1.md
- docs/reference/error-model.md
- docs/reference/error-mapping.md
"""

from __future__ import annotations

import logging
import os

from .grpc_server import serve
from .observability import JsonFormatter, start_metrics_server


def main() -> int:
    level = os.getenv("SYSTEM_API_LOG_LEVEL", "INFO")
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers[:] = [handler]

    metrics_port = int(os.getenv("SYSTEM_API_METRICS_PORT", "9090"))
    start_metrics_server(metrics_port)

    server = serve()
    server.wait_for_termination()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
