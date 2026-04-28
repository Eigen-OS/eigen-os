#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "[runtime-determinism] replaying recorded scoring/policy/explain artifacts"
(
  cd "$ROOT_DIR/src/rust"
  cargo test -p resource-manager --test deterministic_replay_gate
)

echo "[runtime-determinism] ✅ deterministic replay gate passed"
