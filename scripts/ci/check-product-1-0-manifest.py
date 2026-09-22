#!/usr/bin/env python3
"""Validate the Product 1.0 contract manifest required by Wave 0."""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "contracts" / "product-1.0" / "manifest.json"
ALLOWED_IMPLEMENTATION = {"documented", "partial", "planned", "implemented"}
ALLOWED_COMPATIBILITY = {"frozen-for-wave-0", "needs-alignment", "planned", "compatible"}
REQUIRED_TOP_LEVEL = {
    "schema_version": "1.0.0",
    "product_release_target": "1.0.0",
    "version_policy": "docs/development/product-1.0-version-policy.md",
    "inventory": "docs/development/product-1.0-contract-inventory.md",
}
COMMAND_MAPPINGS = {"buf lint", "buf breaking", "python3 scripts/ci/check-docs-links.py", "python3 scripts/ci/check-product-1-0-manifest.py"}
EXPLICITLY_PLANNED_PREFIXES = ("Product 1.0", "planned ")


def _has_values(item: dict, key: str) -> bool:
    value = item.get(key)
    return isinstance(value, list) and any(str(entry).strip() for entry in value)

def _is_path_like(value: str) -> bool:
    return value.startswith(("docs/", "proto/", "contracts/", "scripts/", "src/", ".github/"))


def _inventory_contract_names(inventory_path: pathlib.Path) -> set[str]:
    if not inventory_path.exists():
        return set()
    names: set[str] = set()
    row_re = re.compile(r"^\| (?P<name>[^|]+?) \|")
    for line in inventory_path.read_text(encoding="utf-8").splitlines():
        match = row_re.match(line)
        if not match:
            continue
        raw_name = match.group("name").strip()
        if raw_name == "Contract":
            continue
        # Drop explanatory namespace suffixes while preserving semantic qualifiers
        # such as "QFS layout (CircuitFS)".
        name = re.sub(r" \(`[^`]+`\)$", "", raw_name)
        names.add(name)
    return names


def _validate_existing_paths(label: str, key: str, values: list[str], failures: list[str]) -> None:
    for rel in values:
        rel = str(rel).strip()
        if not rel:
            continue
        if key == "conformance_tests":
            if rel in COMMAND_MAPPINGS or rel.startswith(EXPLICITLY_PLANNED_PREFIXES):
                continue
            if not _is_path_like(rel):
                failures.append(f"{label}: conformance_tests entry must be a repo path, known command, or explicit planned mapping: {rel}")
                continue
        path = ROOT / rel
        if not path.exists():
            failures.append(f"{label}: {key} path does not exist: {rel}")

def main() -> int:
    failures: list[str] = []
    if not MANIFEST_PATH.exists():
        print(f"[product-1.0-manifest] missing {MANIFEST_PATH.relative_to(ROOT)}")
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for key, expected in REQUIRED_TOP_LEVEL.items():
        actual = manifest.get(key)
        if actual != expected:
            failures.append(f"manifest.{key} must be {expected!r}, got {actual!r}")

    for key in ["version_policy", "inventory"]:
        rel = manifest.get(key)
        if not rel or not (ROOT / rel).exists():
            failures.append(f"manifest.{key} missing or path does not exist: {rel!r}")

    contracts = manifest.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        failures.append("manifest.contracts must be a non-empty list")
        contracts = []
    
    seen_names: set[str] = set()
    inventory_names = _inventory_contract_names(ROOT / str(manifest.get("inventory", "")))

    for idx, item in enumerate(contracts):
        label = item.get("name") or f"contracts[{idx}]"
        for key in ["name", "contract_version", "owner", "implementation_status", "compatibility_status"]:
            if not str(item.get(key, "")).strip():
                failures.append(f"{label}: missing {key}")
        if label in seen_names:
            failures.append(f"{label}: duplicate contract name")
        seen_names.add(label)
        if inventory_names and label not in inventory_names:
            failures.append(f"{label}: missing matching row in inventory")
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

        for key in ["sources", "proto_schema_files", "conformance_tests"]:
            _validate_existing_paths(label, key, item.get(key, []) or [], failures)

    for key in ["version_policy", "inventory"]:
        rel = manifest.get(key)
        if not rel or not (ROOT / rel).exists():
            failures.append(f"manifest.{key} missing or path does not exist: {rel!r}")
    missing_from_manifest = inventory_names - seen_names
    for name in sorted(missing_from_manifest):
        failures.append(f"inventory row missing from manifest: {name}")

    if failures:
        print("[product-1.0-manifest] validation failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print(f"[product-1.0-manifest] validated {len(contracts)} contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
