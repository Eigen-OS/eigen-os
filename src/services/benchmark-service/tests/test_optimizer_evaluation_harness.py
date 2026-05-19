from __future__ import annotations

import json
from pathlib import Path

from benchmark_service.optimizer_evaluation import OptimizerEvaluationHarness

FIXTURE = Path(__file__).parent / "fixtures" / "optimizer_evaluation" / "offline_online_fixture.json"


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_offline_harness_is_reproducible_for_frozen_fixture() -> None:
    harness = OptimizerEvaluationHarness()
    fixture = _fixture()

    first = harness.evaluate_offline(fixture)
    second = harness.evaluate_offline(fixture)

    assert first == second
    assert first["comparison"]["summary"]["has_regression"] is True


def test_shadow_harness_emits_block_recommendation_with_gate_reasons() -> None:
    harness = OptimizerEvaluationHarness()
    fixture = _fixture()

    result = harness.evaluate_shadow(fixture)

    assert result["recommendation"] == "BLOCK_PROMOTION"
    assert "REGRESSION_VS_BASELINE_HEURISTIC" in result["gate_reasons"]
    assert "INSUFFICIENT_SHADOW_SAMPLES" in result["gate_reasons"]
