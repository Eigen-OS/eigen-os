#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
CLI_CRATE_PATH="${REPO_ROOT}/src/rust/apps/cli"

if ! command -v cargo >/dev/null 2>&1; then
  echo "error: cargo is required but was not found in PATH" >&2
  exit 1
fi

if [[ "${EUID}" -eq 0 ]]; then
  echo "error: do not run this script as root/sudo." >&2
  echo "       activate your user shell (and virtualenv, if any) and run it normally." >&2
  exit 1
fi

INSTALL_ROOT=""
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  INSTALL_ROOT="${VIRTUAL_ENV}"
else
  INSTALL_ROOT="${HOME}/.local"
fi

INSTALL_DIR="${INSTALL_ROOT}/bin"
mkdir -p "${INSTALL_DIR}"

echo "[1/2] Installing Eigen CLI with cargo (release profile)..."
cargo install --path "${CLI_CRATE_PATH}" --root "${INSTALL_ROOT}" --force --locked

echo "[2/2] Installing launcher at: ${INSTALL_DIR}/eigen"

if [[ ":${PATH}:" != *":${INSTALL_DIR}:"* ]]; then
  echo
  echo "Installed, but ${INSTALL_DIR} is not in PATH for this shell."
  echo "Run: export PATH=\"${INSTALL_DIR}:\$PATH\""
fi

echo
"${INSTALL_DIR}/eigen" --help >/dev/null
echo "Done. Try: eigen --help"