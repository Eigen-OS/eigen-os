#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$REPO_ROOT/src/rust"
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings

cd "$REPO_ROOT"
python3 -m ruff check src/services
