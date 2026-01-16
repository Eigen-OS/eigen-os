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


def main() -> int:
    logging.basicConfig(
        level=os.getenv("SYSTEM_API_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    server = serve()
    server.wait_for_termination()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
