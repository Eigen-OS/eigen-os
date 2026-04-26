#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "[compat] JobSpec parser conformance"
(
  cd "$ROOT_DIR/src/services/system-api"
  pytest tests/test_jobspec_parser.py
)

echo "[compat] AQO simulator contract"
(
  cd "$ROOT_DIR/src/services/driver-manager"
  pytest tests/test_simulator_driver.py
)

echo "[compat] QFS metadata/version contract"
(
  cd "$ROOT_DIR/src/rust"
  cargo test -p qfs store_source_bundle_writes_metadata_hashes
  cargo test -p qfs compiled_artifacts_roundtrip_with_optional_qasm_and_metadata
)

echo "[compat] ✅ all contract compatibility checks passed"