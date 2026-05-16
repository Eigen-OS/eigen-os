from __future__ import annotations

import json
from pathlib import Path


def test_knowledge_base_error_model_fixture_is_frozen_v1() -> None:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "contracts"
        / "knowledge_base_v1"
        / "error_model_v1_0_0.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert payload["contract"] == "knowledge_base_api"
    assert payload["version"] == "1.0.0"
    assert payload["reason_codes"] == [
        "KB_INVALID_ARGUMENT",
        "KB_NOT_FOUND",
        "KB_INDEX_UNAVAILABLE",
        "KB_RATE_LIMITED",
        "KB_INTERNAL",
    ]
    assert payload["deprecation_policy"] == {
        "min_supported_minor_releases": 2,
        "min_supported_days": 90,
    }
