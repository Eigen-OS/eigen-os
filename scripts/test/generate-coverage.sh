#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COVERAGE_DIR="$ROOT_DIR/artifacts/coverage"
mkdir -p "$COVERAGE_DIR"

services=(
  "system-api:system_api"
  "driver-manager:driver_manager"
  "eigen-compiler:eigen_compiler"
)

for entry in "${services[@]}"; do
  service="${entry%%:*}"
  module="${entry##*:}"

  tests_dir="$ROOT_DIR/src/services/$service/tests"
  if [[ -d "$tests_dir" ]]; then
    echo "==> Running coverage for $service"
    pytest -q "$tests_dir" \
      --cov="$module" \
      --cov-report="term-missing" \
      --cov-report="xml:$COVERAGE_DIR/coverage-$service.xml"
  else
    echo "==> Skipping $service (no tests directory found)"
  fi
done

if [[ -d "$ROOT_DIR/src/services/eigen-lang" ]]; then
  echo "==> Skipping eigen-lang (service scaffold has no tests yet)"
fi

echo "Coverage XML reports are available in: $COVERAGE_DIR"