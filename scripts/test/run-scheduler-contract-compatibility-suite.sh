#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "[scheduler-compat] contract compatibility snapshots (DTOs, reason codes, manifests)"
(
  cd "$ROOT_DIR/src/rust"
  cargo test -p resource-manager --test scheduler_contract_compatibility
)

echo "[scheduler-compat] ✅ scheduler compatibility suite passed"