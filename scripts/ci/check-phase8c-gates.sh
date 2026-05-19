#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT_DIR"

echo "[phase8c-gates] contract drift"
python3 scripts/ci/check-contract-drift.py

echo "[phase8c-gates] trigger/canary/rollback/reproducibility fixture"
python3 scripts/ci/check-phase8c-gate-fixtures.py

echo "[phase8c-gates] learning pipeline reproducibility suite"
(
  cd src/services/benchmark-service
  PYTHONPATH=src pytest -q tests/test_optimizer_evaluation_harness.py
)

echo "[phase8c-gates] ✅ all gates passed"
