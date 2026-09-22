# How to generate protobuf stubs (MVP)

Eigen OS treats `proto/` as the **single source of truth** for all RPC contracts.

This guide describes how to generate **Python gRPC stubs** from the `.proto` files.

> In later phases we may add additional generators (Rust/Go/TS) via Buf.

---

## Prerequisites

- Python 3.12+
- `pip`

Install required packages:

```bash
python -m pip install --upgrade pip
python -m pip install grpcio grpcio-tools protobuf
```

---

## Generate Python stubs

From the repo root:

```bash
bash scripts/dev/generate-protos.sh
```

Generated code is written to:

```text
gen/python/
  eigen_api/v1/*_pb2.py
  eigen_api/v1/*_pb2_grpc.py
  eigen_internal/v1/*_pb2.py
  eigen_internal/v1/*_pb2_grpc.py
```

### Import example

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gen" / "python"))

from eigen_api.v1 import job_service_pb2
from eigen_api.v1 import job_service_pb2_grpc
```

---

## Verify generation (integration test)

```bash
bash scripts/test/run-integration-tests.sh
```
