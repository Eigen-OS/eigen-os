#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

"$REPO_ROOT/scripts/ci/lint.sh"
"$REPO_ROOT/scripts/test/run-unit-tests.sh"
