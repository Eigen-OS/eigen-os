"""driver-manager entrypoint for internal DriverManagerService."""


from __future__ import annotations

import logging
import os

from .grpc_server import serve


def main() -> int:
    logging.basicConfig(
        level=os.getenv("DRIVER_MANAGER_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    server = serve()
    server.wait_for_termination()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

