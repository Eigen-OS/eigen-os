from __future__ import annotations

import json
from pathlib import Path


def test_optimizer_contract_fixture_is_frozen_v1() -> None:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "contracts"
        / "optimizer_v1"
        / "service_contract_v1_0_0.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert payload["contract"] == "optimizer_service"
    assert payload["version"] == "1.0.0"
    assert payload["request"]["deterministic_defaults"] == {
        "candidate_budget": 1,
        "timeout_ms": 100,
        "trace_context": {},
    }
    assert payload["response"]["fallback_contract"] == {
        "fallback_used": True,
        "requires_fallback_reason": True,
    }
    assert payload["reason_codes"] == [
        "OPT_INVALID_AQO",
        "OPT_TOPOLOGY_MISSING",
        "OPT_MODEL_UNAVAILABLE",
        "OPT_TIMEOUT",
        "OPT_INTERNAL",
    ]
