#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROTO_DIR="$ROOT_DIR/proto"
OUT_DIR="$ROOT_DIR/gen/python"

PYTHON_BIN="${PYTHON_BIN:-python3}"

# Ensure grpcio-tools is available.
$PYTHON_BIN - <<'PY'
import sys
try:
    import grpc_tools  # noqa: F401
except Exception as e:
    print("grpcio-tools is not installed. Install with:")
    print("  python -m pip install grpcio grpcio-tools protobuf")
    raise
PY

PROTO_INCLUDE="$($PYTHON_BIN - <<'PY'
import os
import grpc_tools
print(os.path.join(os.path.dirname(grpc_tools.__file__), '_proto'))
PY
)"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# Collect all protos.
mapfile -t PROTOS < <(find "$PROTO_DIR" -type f -name "*.proto" | sort)

if [[ ${#PROTOS[@]} -eq 0 ]]; then
  echo "No .proto files found under $PROTO_DIR" >&2
  exit 1
fi

$PYTHON_BIN -m grpc_tools.protoc \
  -I"$PROTO_DIR" \
  -I"$PROTO_INCLUDE" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  "${PROTOS[@]}"

# Make packages importable.
# protoc does not create __init__.py files.
while IFS= read -r -d '' d; do
  touch "$d/__init__.py"
done < <(find "$OUT_DIR" -type d -print0)

echo "✅ Generated Python stubs into: $OUT_DIR"
