# Examples

This folder contains small, runnable examples for Eigen OS.

## Python gRPC skeleton servers (MVP)

These examples prove that the generated protobuf stubs are usable and can be wired into a server.

Prerequisites:

```bash
python -m pip install grpcio grpcio-tools protobuf
bash scripts/dev/generate-protos.sh
```

Run public API skeleton:

```bash
python examples/python/public_api_skeleton_server.py
```

Run internal API skeleton:

```bash
python examples/python/internal_api_skeleton_server.py
```
