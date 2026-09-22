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


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {
        "",
        "<!-- major | minor | patch | none -->",
        "<!-- backward-compatible | breaking (requires major) -->",
        "<!-- true | false -->",
        "<!-- required when breaking marker=true (or version impact=major); otherwise \"none\" is allowed -->",
        "<!-- required actions for operators/clients, or \"none\" -->",
    }


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
    version_impact = _extract_section(body, "Version Impact")
    compatibility = _extract_section(body, "Compatibility")
    breaking_marker = _extract_section(body, "Breaking Marker")
    migration_notes = _extract_section(body, "Migration Notes")

    if _is_placeholder(version_impact):
        print("[migration-gate] Missing '**Version Impact**' value in PR body.")
        return 1

    if _is_placeholder(compatibility):
        print("[migration-gate] Missing '**Compatibility**' value in PR body.")
        return 1

    requires_migration = (
        version_impact.strip().upper() == "MAJOR"
        or compatibility.strip().lower().startswith("breaking")
        or breaking_marker.strip().lower() == "true"
    )

    if _is_placeholder(migration_notes):
        print("[migration-gate] Missing '**Migration Notes**' value in PR body.")
        return 1

    if requires_migration and migration_notes.strip().lower() == "none":
        print("[migration-gate] Breaking changes require non-empty migration notes.")
        return 1

    if requires_migration and len(migration_notes.strip()) < 8:
        print("[migration-gate] Migration Notes are too short for breaking changes.")
        return 1

    print("[migration-gate] Versioning section is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
