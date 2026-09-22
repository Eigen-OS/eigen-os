#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[phase9b-gates] quality schema + non-regression gate"
python3 scripts/ci/check-phase9b-quality-gates.py

echo "[phase9b-gates] optimizer evaluation suite"
(
  cd src/services/benchmark-service
  PYTHONPATH=src pytest -q tests/test_optimizer_evaluation_harness.py
)

echo "[phase9b-gates] ✅ all gates passed"
