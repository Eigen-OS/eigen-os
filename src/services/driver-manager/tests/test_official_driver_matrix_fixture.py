from __future__ import annotations

import json
from pathlib import Path


def test_phase9a_official_driver_matrix_fixture_is_versioned_and_pinned() -> None:
    fixture = (
        Path(__file__).resolve().parents[4]
        / "docs"
        / "development"
        / "fixtures"
        / "phase9a"
        / "official_driver_matrix_v1_3_0.json"
    )
    payload = json.loads(fixture.read_text(encoding="utf-8"))

    assert payload["matrix_version"] == "1.3.0"
    assert payload["phase"] == "9A"
    assert payload["official_targets"] == ["simulator", "ibm", "aws"]

    entries = payload["entries"]
    assert len(entries) == 3
    for entry in entries:
        assert entry["driver_version"] == "1.3.0"
        assert entry["artifact_digest"].startswith("sha256:")
        assert entry["manifest_digest"].startswith("sha256:")
