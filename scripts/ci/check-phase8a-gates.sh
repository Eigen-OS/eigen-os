#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT_DIR"

echo "[phase8a-gates] contract drift"
python3 scripts/ci/check-contract-drift.py

echo "[phase8a-gates] vertical slice deterministic replay"
(
  cd src/rust
  cargo test -p eigen-kernel integration_phase8a_vertical_slice_fixture_replay_is_deterministic
)

echo "[phase8a-gates] runtime decision determinism"
bash scripts/ci/check-runtime-decision-determinism.sh

echo "[phase8a-gates] probe fixtures"
python3 scripts/ci/check-phase8a-probe-fixtures.py

echo "[phase8a-gates] ✅ all gates passed"
