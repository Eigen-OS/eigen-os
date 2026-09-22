#!/usr/bin/env python3
"""Validate Product 1.0 Wave 1 closure evidence documents."""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
COMPAT = ROOT / "docs" / "development" / "product-1.0-wave-1-compatibility-report.md"
BUNDLE = ROOT / "docs" / "development" / "product-1.0-wave-1-exit-evidence-bundle.md"
READINESS = ROOT / "docs" / "development" / "product-1.0-wave-1-release-readiness-checklist.md"
GAP = ROOT / "docs" / "development" / "product-1.0-wave-1-rfc-adr-gap-analysis.md"

ISSUE_RE = re.compile(r"^\| W1-(0[1-8]) ")


def _failures() -> list[str]:
    failures: list[str] = []
    compat = COMPAT.read_text(encoding="utf-8")
    rows = [line for line in compat.splitlines() if ISSUE_RE.match(line)]
    if len(rows) != 8:
        failures.append(f"expected 8 Wave 1 compatibility rows, found {len(rows)}")
    for row in rows:
        cols = [col.strip() for col in row.strip().strip("|").split("|")]
        issue, version_impact, _affected, compatibility, breaking_marker, migration, release, evidence = cols
        if version_impact not in {"MAJOR", "MINOR", "PATCH", "NONE"}:
            failures.append(f"{issue}: invalid Version Impact {version_impact!r}")
        if breaking_marker not in {"true", "false"}:
            failures.append(f"{issue}: invalid Breaking Marker {breaking_marker!r}")
        for label, value in {
            "Compatibility": compatibility,
            "Migration Notes": migration,
            "Release Notes Draft": release,
            "Evidence": evidence,
        }.items():
            if value in {"", "TBD"}:
                failures.append(f"{issue}: unresolved {label}")
    for path in (READINESS, GAP):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.startswith("- [ ]"):
                failures.append(f"{path.relative_to(ROOT)}:{lineno}: unchecked Wave 1 closure item")
    bundle = BUNDLE.read_text(encoding="utf-8")
    for evidence_id in [f"W1-E{i:02d}" for i in range(1, 9)]:
        if evidence_id not in bundle:
            failures.append(f"missing evidence row {evidence_id}")
    return failures


def main() -> int:
    failures = _failures()
    if failures:
        print("[product-1.0-wave1-closure] validation failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("[product-1.0-wave1-closure] Wave 1 closure docs are complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
