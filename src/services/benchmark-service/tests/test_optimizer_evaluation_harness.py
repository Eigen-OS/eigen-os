from __future__ import annotations

import json
from pathlib import Path

from benchmark_service.optimizer_evaluation import (
    ContinuousLearningPipeline,
    OptimizerEvaluationHarness,
)

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
    assert first["contract_version"] == "1.5.0"
    assert first["quality_signal"]["schema_version"] == "1.0.0"
    assert first["quality_signal"]["swap_count"] == 2
    assert "confidence" in first["quality_signal"]
    assert first["explainability"]["trace_context"]["traceparent"] == fixture["trace_context"]["traceparent"]
    assert first["explainability"]["confidence_metadata"]["score"] == first["quality_signal"]["confidence"]
    assert first["quality_signal"]["metric_bounds"]["confidence_score"]["min"] == 0.0
    assert first["quality_signal"]["metric_bounds"]["confidence_score"]["max"] == 1.0


def test_shadow_harness_emits_block_recommendation_with_gate_reasons() -> None:
    harness = OptimizerEvaluationHarness()
    fixture = _fixture()

    result = harness.evaluate_shadow(fixture)

    assert result["recommendation"] == "BLOCK_PROMOTION"
    assert "REGRESSION_VS_BASELINE_HEURISTIC" in result["gate_reasons"]
    assert "INSUFFICIENT_SHADOW_SAMPLES" in result["gate_reasons"]
    assert result["offline_bundle"]["explainability"]["fallback_metadata"]["used"] is True
    assert result["offline_bundle"]["explainability"]["fallback_metadata"]["reason_code"] == "EIGEN_OPT_CONFIDENCE_TOO_LOW"

def test_offline_harness_trace_and_metric_bounds_are_bounded() -> None:
    harness = OptimizerEvaluationHarness()
    fixture = _fixture()

    result = harness.evaluate_offline(fixture)

    explainability = result["explainability"]
    metric_bounds = result["quality_signal"]["metric_bounds"]

    assert explainability["trace_fields"] == ["request_id", "trace_id", "traceparent"]
    assert explainability["decision_lineage"]["dataset_ref"] == fixture["dataset_ref"]
    assert explainability["decision_lineage"]["topology_hash"].startswith("sha256:")
    assert metric_bounds["confidence_score"] == {"min": 0.0, "max": 1.0}
    assert metric_bounds["predicted_error"] == {"min": 0.0, "max": 1.0}
    assert metric_bounds["observed_shadow_samples"]["min"] == 0
    assert metric_bounds["observed_shadow_samples"]["max"] >= fixture["observed_shadow_samples"]

def test_pipeline_generates_artifact_and_rollback_reason_codes_when_regression_detected() -> None:
    pipeline = ContinuousLearningPipeline()
    fixture = _fixture()

    result = pipeline.evaluate(fixture)

    assert result["trigger"]["should_retrain"] is True
    assert result["artifact"]["artifact_version"] == "phase8c-candidate-0007"
    assert result["artifact"]["lineage"]["lineage_hash"].startswith("sha256:")
    assert result["artifact"]["training_config_digest"].startswith("sha256:")
    assert result["artifact"]["dataset_snapshot_manifest"]["snapshot_hash"] == fixture["dataset_hash"]
    assert result["artifact"]["model_artifact_hashes"]["weights"].startswith("sha256:")
    assert result["promotion"]["recommendation"] == "BLOCK_PROMOTION"
    assert result["rollback"]["action"] == "ROLLBACK_TO_STABLE"
    assert result["audit_events"][0]["event_type"] == "RETRAIN_TRIGGER_EVALUATED"
    assert result["audit_events"][1]["linked_model_version"] == "phase8c-candidate-0007"
    assert result["canary"]["cohort"]["dimension"] == "backend_class"
    assert result["canary"]["cohort"]["value"] == "simulator"
    assert result["canary"]["evaluation_window_minutes"] == 45
    assert result["canary"]["decision"] == "ROLLBACK"
    assert result["rollback"]["target_model_version"] == "phase8c-stable-0006"
    assert result["rollback"]["slo_minutes"] == 15
    assert result["rollback"]["reason_codes"] == [
        "CANARY_INSUFFICIENT_SHADOW_SAMPLES",
        "CANARY_REGRESSION_VS_BASELINE_HEURISTIC",
    ]

def test_pipeline_auto_mints_artifact_version_when_not_supplied() -> None:
    pipeline = ContinuousLearningPipeline()
    fixture = _fixture()
    fixture.pop("artifact_version", None)

    result = pipeline.evaluate(fixture)

    assert result["artifact"]["artifact_version"] == "phase8c-candidate-1000"
    assert result["artifact"]["lineage"]["lineage_hash"].startswith("sha256:")
    assert "benchmark_service.reproduce_training" in result["artifact"]["reproduce"]["command"]

def test_pipeline_does_not_trigger_retrain_before_threshold() -> None:
    pipeline = ContinuousLearningPipeline()
    fixture = _fixture()
    fixture["observed_new_circuits"] = 999

    result = pipeline.evaluate(fixture)

    assert result["trigger"]["should_retrain"] is False
    assert result["audit_events"][0]["should_retrain"] is False
    assert result["artifact"] is None
    assert result["promotion"] is None
    assert result["rollback"] is None

def test_pipeline_triggers_retrain_on_time_cap_without_threshold() -> None:
    pipeline = ContinuousLearningPipeline()
    fixture = _fixture()
    fixture["observed_new_circuits"] = 10
    fixture["elapsed_minutes_since_last_train"] = 2000
    fixture["trigger_policy"]["max_interval_minutes"] = 1440

    result = pipeline.evaluate(fixture)

    assert result["trigger"]["rules"]["new_data_threshold"] is False
    assert result["trigger"]["rules"]["time_cap_exceeded"] is True
    assert result["trigger"]["should_retrain"] is True


def test_pipeline_triggers_retrain_on_manual_override() -> None:
    pipeline = ContinuousLearningPipeline()
    fixture = _fixture()
    fixture["observed_new_circuits"] = 1
    fixture["manual_retrain_override"] = True

    result = pipeline.evaluate(fixture)

    assert result["trigger"]["rules"]["manual_override"] is True
    assert result["trigger"]["should_retrain"] is True


def test_wave7a_quality_gate_fixture_blocks_release_and_preserves_bounded_evidence() -> None:
    harness = OptimizerEvaluationHarness()
    pipeline = ContinuousLearningPipeline()
    fixture = _fixture()

    offline = harness.evaluate_offline(fixture)
    shadow = harness.evaluate_shadow(fixture)
    result = pipeline.evaluate(fixture)

    assert offline["comparison"]["summary"] == {
        "metric_count": 2,
        "regression_count": 1,
        "has_regression": True,
        "regression_metrics": ["latency_ms"],
    }
    assert offline["explainability"]["trace_fields"] == ["request_id", "trace_id", "traceparent"]
    assert offline["explainability"]["fallback_metadata"] == {
        "used": True,
        "reason_code": "EIGEN_OPT_CONFIDENCE_TOO_LOW",
        "reason": "Confidence below minimum policy threshold",
    }
    assert shadow["recommendation"] == "BLOCK_PROMOTION"
    assert shadow["gate_reasons"] == [
        "REGRESSION_VS_BASELINE_HEURISTIC",
        "INSUFFICIENT_SHADOW_SAMPLES",
    ]
    assert result["promotion"]["recommendation"] == "BLOCK_PROMOTION"
    assert result["rollback"]["action"] == "ROLLBACK_TO_STABLE"
    assert result["rollback"]["target_model_version"] == fixture["stable_model_version"]
    