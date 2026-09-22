#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "[scheduler-compat] contract compatibility snapshots (DTOs, reason codes, manifests)"
(
  cd "$ROOT_DIR/src/rust"
  cargo test -p resource-manager --test scheduler_contract_compatibility
)

echo "[scheduler-compat] deterministic replay drift gate (scoring + policy + explain)"
(
  cd "$ROOT_DIR"
  bash scripts/ci/check-runtime-decision-determinism.sh
)

echo "[scheduler-compat] ✅ scheduler compatibility suite passed"
