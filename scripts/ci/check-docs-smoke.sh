#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[docs-smoke] Verifying canonical tutorial assets exist"
test -f docs/tutorials/quickstart-local-sim.md
test -f docs/tutorials/first-job-eigen-lang.md
test -f examples/basic/vqe_cycle/job.yaml
test -f examples/basic/vqe_cycle/program.eigen.py
test -f src/rust/apps/cli/tests/fixtures/jobspec-valid-minimal.yaml

echo "[docs-smoke] Building/running CLI help used by tutorials"
cargo run -p cli --manifest-path src/rust/Cargo.toml -- --help >/dev/null

echo "[docs-smoke] Running tutorial smoke checks"
pytest src/services/system-api/tests/test_e2e_smoke_submit_watch_results.py -q
pytest src/services/system-api/tests/test_observability_smoke.py -q

echo "[docs-smoke] OK"
