#!/usr/bin/env python3
"""Validate canonical markdown links for Product 1.0 contract docs.

The gate covers the canonical architecture/reference docs and the Product 1.0
planning docs that drive Wave 0. It scans markdown links plus inline-code
repository references, then fails when a referenced markdown path does not exist.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC_ROOTS = [ROOT / "docs" / "architecture", ROOT / "docs" / "reference"]
PRODUCT_DOCS = [
    ROOT / "docs" / "development" / "product-1.0-contract-alignment-plan.md",
    ROOT / "docs" / "development" / "product-1.0-wave-0-execution-plan.md",
    ROOT / "docs" / "development" / "product-1.0-contract-inventory.md",
    ROOT / "docs" / "development" / "product-1.0-version-policy.md",
    ROOT / "docs" / "development" / "product-1.0-wave-1-execution-plan.md",
    ROOT / "docs" / "development" / "product-1.0-wave-1-issue-pack.md",
    ROOT / "docs" / "development" / "product-1.0-wave-1-rfc-adr-gap-analysis.md",
    ROOT / "docs" / "development" / "product-1.0-wave-1-compatibility-report.md",
    ROOT / "docs" / "development" / "product-1.0-wave-1-release-readiness-checklist.md",
    ROOT / "docs" / "development" / "product-1.0-wave-1-exit-evidence-bundle.md",
]
REPO_PREFIXES = (
    "docs/",
    "proto/",
    "contracts/",
    "scripts/",
    ".github/",
)

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.md(?:#[^)]+)?)\)")
INLINE_CANONICAL_RE = re.compile(
    r"`((?:docs/)?(?:architecture|reference)/[^`\s)]+\.md(?:#[^`\s)]+)?)`"
)
INLINE_REPO_MD_RE = re.compile(
    r"`((?:docs/|proto/|contracts/|scripts/|\.github/|README\.md)[^`\s)]*\.md(?:#[^`\s)]+)?)`"
)


def _normalize_ref(source: pathlib.Path, ref: str) -> pathlib.Path | None:
    ref = ref.split("#", 1)[0]
    if "://" in ref or ref.startswith("mailto:"):
        return None
    if not ref.endswith(".md"):
        return None
    if ref == "README.md" or ref.startswith(REPO_PREFIXES):
        return ROOT / ref
    if ref.startswith("architecture/") or ref.startswith("reference/"):
        return ROOT / "docs" / ref
    if ref.startswith("/"):
        return ROOT / ref.lstrip("/")
    return (source.parent / ref).resolve()


def _iter_sources() -> list[pathlib.Path]:
    sources: list[pathlib.Path] = []
    for root in DOC_ROOTS:
        sources.extend(sorted(root.rglob("*.md")))
    sources.extend(path for path in PRODUCT_DOCS if path.exists())
    return sources

def main() -> int:
    failures: list[str] = []
    for source in _iter_sources():
        text = source.read_text(encoding="utf-8")
        refs = [m.group(1) for m in MARKDOWN_LINK_RE.finditer(text)]
        refs.extend(m.group(1) for m in INLINE_CANONICAL_RE.finditer(text))
        if source in PRODUCT_DOCS:
            refs.extend(m.group(1) for m in INLINE_REPO_MD_RE.finditer(text))
        for ref in refs:
            target = _normalize_ref(source, ref)
            if target is None:
                continue
            try:
                target.relative_to(ROOT)
            except ValueError:
                continue
            if not target.exists():
                failures.append(
                    f"{source.relative_to(ROOT)} references missing {target.relative_to(ROOT)}"
                )

    if failures:
        print("[docs-links] missing canonical markdown references:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("[docs-links] architecture/reference and Product 1.0 markdown references resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
