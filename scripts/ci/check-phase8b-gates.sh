#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT_DIR"

echo "[phase8b-gates] contract drift"
python3 scripts/ci/check-contract-drift.py

echo "[phase8b-gates] scale + latency fixtures"
python3 scripts/ci/check-phase8b-gate-fixtures.py

echo "[phase8b-gates] artifact integrity suite"
(
  cd src/services/system-api
  pytest tests/test_qfs_blob_backends.py -k "layout_validator or retention_executor"
)

echo "[phase8b-gates] checkpoint integrity suite"
(
  cd src/rust
  cargo test -p qfs checkpoint_envelope
)

echo "[phase8b-gates] ✅ all gates passed"
