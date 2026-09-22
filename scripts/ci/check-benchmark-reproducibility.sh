#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT_DIR/src/services/benchmark-service"
PYTHONPATH=src pytest -q tests/test_reproducibility_gate.py
