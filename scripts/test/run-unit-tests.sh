#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

services=(
  "system-api"
  "driver-manager"
  "eigen-compiler"
  "benchmark-service"
)

for service in "${services[@]}"; do
  tests_dir="$ROOT_DIR/src/services/$service/tests"
  if [[ -d "$tests_dir" ]]; then
    echo "==> Running unit tests for $service"
    pytest -q "$tests_dir"
    if [[ "$service" == "benchmark-service" ]]; then
      PYTHONPATH="$ROOT_DIR/src/services/benchmark-service/src" pytest -q "$tests_dir"
    else
      pytest -q "$tests_dir"
    fi
  else
    echo "==> Skipping $service (no tests directory found)"
  fi
done

if [[ -d "$ROOT_DIR/src/services/eigen-lang" ]]; then
  echo "==> Skipping eigen-lang (service scaffold has no tests yet)"
fi
if [[ -x "$ROOT_DIR/scripts/ci/check-benchmark-reproducibility.sh" ]]; then
  echo "==> Running benchmark reproducibility drift gate"
  "$ROOT_DIR/scripts/ci/check-benchmark-reproducibility.sh"
fi
