#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT_DIR"

echo "[phase9a-gates] contract drift"
python3 scripts/ci/check-contract-drift.py

echo "[phase9a-gates] fault-injection deterministic suite"
(
  cd src/services/system-api
  pip install -e .[dev]
  pytest -q tests/test_security_baseline.py::test_static_token_mode_fails_closed_on_missing_auth_context
)
(
  cd src/services/driver-manager
  pip install -e .[dev]
  pytest -q \
    tests/test_qdriver_v1_conformance.py::test_qdriver_v1_profile_matrix_fail_closed \
    tests/test_rollback_governance.py::test_rollback_safety_fails_closed_when_controls_are_missing \
    tests/test_parity_tolerance_suite.py::test_cross_provider_tolerance_fails_closed_on_drift
)
(
  cd src/rust
  cargo test -p cli plugin_conflicts_fail_closed_with_reason
)

echo "[phase9a-gates] runtime deterministic replay"
bash scripts/ci/check-runtime-decision-determinism.sh

echo "[phase9a-gates] ✅ complete"
