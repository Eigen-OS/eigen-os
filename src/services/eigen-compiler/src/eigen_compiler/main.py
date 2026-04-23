"""eigen-compiler entrypoint."""

import logging

from .grpc_server import serve


logging.basicConfig(level=logging.INFO)


def main() -> int:
    server = serve()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:  # pragma: no cover
        server.stop(grace=0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
