#!/usr/bin/env python3
"""Validate canonical markdown links in architecture/reference docs.

Wave 0 intentionally keeps this check lightweight: it scans markdown links and
inline-code canonical references under docs/architecture and docs/reference, then
fails when a referenced docs/architecture or docs/reference markdown path does
not exist.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC_ROOTS = [ROOT / "docs" / "architecture", ROOT / "docs" / "reference"]

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+\.md(?:#[^)]+)?)\)")
INLINE_DOC_RE = re.compile(r"`((?:docs/)?(?:architecture|reference)/[^`\s)]+\.md(?:#[^`\s)]+)?)`")


def _normalize_ref(source: pathlib.Path, ref: str) -> pathlib.Path | None:
    ref = ref.split("#", 1)[0]
    if "://" in ref or ref.startswith("mailto:"):
        return None
    if not ref.endswith(".md"):
        return None
    if ref.startswith("docs/"):
        return ROOT / ref
    if ref.startswith("architecture/") or ref.startswith("reference/"):
        return ROOT / "docs" / ref
    if ref.startswith("/"):
        return ROOT / ref.lstrip("/")
    return (source.parent / ref).resolve()


def main() -> int:
    failures: list[str] = []
    for root in DOC_ROOTS:
        for source in sorted(root.rglob("*.md")):
            text = source.read_text(encoding="utf-8")
            refs = [m.group(1) for m in MARKDOWN_LINK_RE.finditer(text)]
            refs.extend(m.group(1) for m in INLINE_DOC_RE.finditer(text))
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

    print("[docs-links] architecture/reference markdown references resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
