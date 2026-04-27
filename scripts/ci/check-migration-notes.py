from __future__ import annotations

import json
import os
import pathlib
import re


def _extract_section(body: str, heading: str) -> str:
    pattern = re.compile(
        rf"^\s*(?:[-*]\s*)?\*\*{re.escape(heading)}\*\*:\s*(.*)$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(body)
    if not match:
        return ""
    return match.group(1).strip()


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("[migration-gate] GITHUB_EVENT_PATH is not set; skipping.")
        return 0

    event = json.loads(pathlib.Path(event_path).read_text(encoding="utf-8"))
    pr = event.get("pull_request")
    if not pr:
        print("[migration-gate] Not a pull_request event; skipping.")
        return 0

    body = pr.get("body") or ""
    migration_notes = _extract_section(body, "Migration Notes")
    version_impact = _extract_section(body, "Version Impact")

    if not version_impact:
        print("[migration-gate] Missing '**Version Impact**' in PR body.")
        return 1

    placeholders = {
        "",
        "<!-- Required actions for operators/clients, or \"None\" -->",
        "<!-- required actions for operators/clients, or \"none\" -->",
    }
    normalized = migration_notes.strip()

    if normalized in placeholders:
        print("[migration-gate] Missing '**Migration Notes**' value in PR body.")
        return 1

    if normalized.lower() == "none":
        print("[migration-gate] Migration Notes explicitly marked as None.")
        return 0

    if len(normalized) < 8:
        print("[migration-gate] Migration Notes are too short; provide actionable details or 'None'.")
        return 1

    print("[migration-gate] Migration Notes present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
