#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
MANIFEST_PATH="${REPO_ROOT}/src/rust/Cargo.toml"
BIN_PATH="${REPO_ROOT}/src/rust/target/debug/eigen"

if ! command -v cargo >/dev/null 2>&1; then
  echo "error: cargo is required but was not found in PATH" >&2
  exit 1
fi

INSTALL_DIR=""
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  INSTALL_DIR="${VIRTUAL_ENV}/bin"
else
  INSTALL_DIR="${HOME}/.local/bin"
fi

mkdir -p "${INSTALL_DIR}"

echo "[1/2] Building Eigen CLI (debug profile)..."
cargo build -p cli --manifest-path "${MANIFEST_PATH}"

echo "[2/2] Installing launcher at: ${INSTALL_DIR}/eigen"
ln -sfn "${BIN_PATH}" "${INSTALL_DIR}/eigen"
chmod +x "${BIN_PATH}"

if [[ ":${PATH}:" != *":${INSTALL_DIR}:"* ]]; then
  echo
  echo "Installed, but ${INSTALL_DIR} is not in PATH for this shell."
  echo "Run: export PATH=\"${INSTALL_DIR}:\$PATH\""
fi

echo
"${INSTALL_DIR}/eigen" --help >/dev/null
echo "Done. Try: eigen --help"