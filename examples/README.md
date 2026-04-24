# Examples

This directory contains practical examples for validating contracts and service wiring.

## Structure

- `basic/` — minimal examples.
- `advanced/` — more complete scenarios.
- `python/` — Python/gRPC skeleton services.

## Python gRPC skeleton servers

These examples prove generated protobuf stubs are usable in server code.

### Prerequisites

```bash
python -m pip install grpcio grpcio-tools protobuf
bash scripts/dev/generate-protos.sh
```

### Run public API skeleton

```bash
python examples/python/public_api_skeleton_server.py
```

### Run internal API skeleton

```bash
python examples/python/internal_api_skeleton_server.py
```

## Related docs

- API contracts: [`../docs/reference/api/`](../docs/reference/api/)
- Protobuf source of truth: [`../proto/README.md`](../proto/README.md)
