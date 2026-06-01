#!/usr/bin/env python3
"""Validate the Product 1.0 contract manifest required by Wave 0."""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "contracts" / "product-1.0" / "manifest.json"
ALLOWED_IMPLEMENTATION = {"documented", "partial", "planned", "implemented"}
ALLOWED_COMPATIBILITY = {"frozen-for-wave-0", "needs-alignment", "planned", "compatible"}


def _has_values(item: dict, key: str) -> bool:
    value = item.get(key)
    return isinstance(value, list) and any(str(entry).strip() for entry in value)


def main() -> int:
    failures: list[str] = []
    if not MANIFEST_PATH.exists():
        print(f"[product-1.0-manifest] missing {MANIFEST_PATH.relative_to(ROOT)}")
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    contracts = manifest.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        failures.append("manifest.contracts must be a non-empty list")
        contracts = []

    for idx, item in enumerate(contracts):
        label = item.get("name") or f"contracts[{idx}]"
        for key in ["name", "contract_version", "owner", "implementation_status", "compatibility_status"]:
            if not str(item.get(key, "")).strip():
                failures.append(f"{label}: missing {key}")
        if item.get("implementation_status") not in ALLOWED_IMPLEMENTATION:
            failures.append(f"{label}: invalid implementation_status {item.get('implementation_status')!r}")
        if item.get("compatibility_status") not in ALLOWED_COMPATIBILITY:
            failures.append(f"{label}: invalid compatibility_status {item.get('compatibility_status')!r}")
        if not _has_values(item, "sources"):
            failures.append(f"{label}: missing sources")
        if not _has_values(item, "conformance_tests"):
            failures.append(f"{label}: missing conformance_tests")
        if not (_has_values(item, "proto_schema_files") or _has_values(item, "planned_proto_schema_files")):
            failures.append(f"{label}: must list proto_schema_files or planned_proto_schema_files")

        for key in ["sources", "proto_schema_files"]:
            for rel in item.get(key, []) or []:
                if rel.startswith("Product 1.0") or rel.startswith("OpenAPI"):
                    continue
                path = ROOT / rel
                if not path.exists():
                    failures.append(f"{label}: {key} path does not exist: {rel}")

    for key in ["version_policy", "inventory"]:
        rel = manifest.get(key)
        if not rel or not (ROOT / rel).exists():
            failures.append(f"manifest.{key} missing or path does not exist: {rel!r}")

    if failures:
        print("[product-1.0-manifest] validation failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print(f"[product-1.0-manifest] validated {len(contracts)} contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
