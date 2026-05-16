from __future__ import annotations

import json
from pathlib import Path


def test_learning_control_plane_fixture_is_frozen_v1() -> None:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "contracts"
        / "learning_control_plane_v1"
        / "control_plane_contract_v1_0_0.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert payload["contract"] == "continuous_learning_control_plane"
    assert payload["version"] == "1.0.0"
    assert payload["lifecycle"]["states"] == ["DRAFT", "TRAINED", "VALIDATED", "SHADOW", "CANARY", "PROMOTED", "RETIRED"]
    assert payload["lifecycle"]["allowed_transitions"]["CANARY"] == ["PROMOTED", "ROLLBACK_TO_VALIDATED", "RETIRED"]
    assert payload["idempotency"] == {
        "required_fields": ["command", "model_version", "idempotency_key"],
        "same_key_same_payload": "return_previous_result",
        "same_key_different_payload": "LEARN_IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD",
    }
    assert payload["deprecation_policy"] == {
        "min_supported_minor_releases": 2,
        "min_supported_days": 90,
    }
