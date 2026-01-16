"""system-api entrypoint (scaffold).

In Phase 0 this service is the **public ingress**:
- API-key authn/authz
- request validation
- forwarding to eigen-kernel via internal gRPC
"""


def main() -> int:
    print("system-api scaffold: not implemented")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
