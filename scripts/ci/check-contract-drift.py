from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "scripts" / "ci" / "contract-version-manifest.json"


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []

    for item in manifest.get("artifacts", []):
        rel = item["path"]
        expected = item["sha256"]
        full = ROOT / rel
        if not full.exists():
            failures.append(f"missing artifact: {rel}")
            continue
        actual = _sha256(full)
        if actual != expected:
            failures.append(
                f"drift detected for {rel}: expected {expected}, got {actual}"
            )

    if failures:
        print("[contract-drift] undocumented contract drift detected:")
        for failure in failures:
            print(f" - {failure}")
        print(
            "[contract-drift] if intentional, update scripts/ci/contract-version-manifest.json in the same PR."
        )
        return 1

    print("[contract-drift] contract artifacts match manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
