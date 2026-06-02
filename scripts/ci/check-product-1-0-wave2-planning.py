#!/usr/bin/env python3
"""Validate Product 1.0 Wave 2 planning package structure."""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "development"
REQUIRED_FILES = [
    DOCS / "product-1.0-wave-2-execution-plan.md",
    DOCS / "product-1.0-wave-2-issue-pack.md",
    DOCS / "product-1.0-wave-2-rfc-adr-gap-analysis.md",
    DOCS / "product-1.0-wave-2-compatibility-report.md",
    DOCS / "product-1.0-wave-2-release-readiness-checklist.md",
    DOCS / "product-1.0-wave-2-exit-evidence-bundle.md",
    ROOT / "rfcs" / "0050-product-1.0-kernel-qrtx-lifecycle-authority.md",
    ROOT / "docs" / "adr" / "0036-product-1.0-kernel-qrtx-lifecycle-authority.md",
]
ISSUES = [f"W2-{i:02d}" for i in range(1, 9)]
EVIDENCE = [f"W2-E{i:02d}" for i in range(1, 9)]
COMPAT_ROW_RE = re.compile(r"^\| W2-(0[1-8]) ")


def _failures() -> list[str]:
    failures: list[str] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            failures.append(f"missing required file: {path.relative_to(ROOT)}")
    if failures:
        return failures

    issue_pack = (DOCS / "product-1.0-wave-2-issue-pack.md").read_text(encoding="utf-8")
    for issue in ISSUES:
        if f"### {issue}" not in issue_pack:
            failures.append(f"issue pack missing section for {issue}")

    compat = (DOCS / "product-1.0-wave-2-compatibility-report.md").read_text(encoding="utf-8")
    rows = [line for line in compat.splitlines() if COMPAT_ROW_RE.match(line)]
    if len(rows) != 8:
        failures.append(f"expected 8 Wave 2 compatibility rows, found {len(rows)}")
    for issue in ISSUES:
        if issue not in compat:
            failures.append(f"compatibility report missing {issue}")

    bundle = (DOCS / "product-1.0-wave-2-exit-evidence-bundle.md").read_text(encoding="utf-8")
    for evidence_id in EVIDENCE:
        if evidence_id not in bundle:
            failures.append(f"evidence bundle missing {evidence_id}")

    readiness = (DOCS / "product-1.0-wave-2-release-readiness-checklist.md").read_text(encoding="utf-8")
    for required_ref in ["RFC 0050", "ADR 0036", "Wave 3 handoff"]:
        if required_ref not in readiness:
            failures.append(f"readiness checklist missing {required_ref}")

    return failures


def main() -> int:
    failures = _failures()
    if failures:
        print("[product-1.0-wave2-planning] validation failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("[product-1.0-wave2-planning] Wave 2 planning package is structurally complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
