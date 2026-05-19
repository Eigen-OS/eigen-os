from monitoring.metrics.aggregation.aggregator import StageLatencyAggregator
from monitoring.metrics.aggregation.alerts import StageSLOAlertEvaluator, default_stage_slos
from monitoring.metrics.prometheus.exporter import (
    BenchmarkMetricsSnapshot,
    BenchmarkTelemetryExporter,
    OrchestrationMetricsSnapshot,
    OrchestrationTelemetryExporter,
    StageTelemetryExporter,
)


def test_aggregator_quantiles_and_error_rate():
    agg = StageLatencyAggregator(max_samples_per_stage=256)
    for value in [0.1, 0.2, 0.3, 0.4, 0.5]:
        agg.observe(stage="compile", latency_seconds=value, is_error=value >= 0.4)

    stats = agg.snapshot()["compile"]
    assert stats.sample_count == 5
    assert stats.error_count == 2
    assert stats.p50_seconds == 0.3
    assert stats.p95_seconds == 0.5
    assert stats.p99_seconds == 0.5
    assert stats.error_rate == 0.4


def test_slo_alerts_trigger_for_degraded_stage():
    exporter = StageTelemetryExporter(max_samples_per_stage=512)
    for _ in range(60):
        exporter.observe_stage(stage="execute", latency_seconds=13.0, is_error=True)

    text = exporter.render_prometheus_text()
    assert 'eigen_stage_slo_violations_total 3' in text
    assert 'eigen_stage_slo_violation{stage="execute",metric="p99_seconds",severity="critical"} 1' in text
    assert 'eigen_stage_slo_violation{stage="execute",metric="error_rate",severity="critical"} 1' in text


def test_default_slo_configuration_covers_core_runtime_stages():
    slos = default_stage_slos()
    evaluator = StageSLOAlertEvaluator(slos)
    expected = {"queue", "compile", "schedule", "execute", "result"}
    assert set(evaluator._slos.keys()) == expected

def test_orchestration_metrics_exporter_renders_stable_contract_metrics():
    exporter = OrchestrationTelemetryExporter()
    exporter.update_snapshot(
        OrchestrationMetricsSnapshot(
            contract_version="2.3.0",
            queue_depth=42,
            queue_oldest_age_seconds=18.5,
            queue_avg_age_seconds=4.25,
            fairness_lag_millis_total=8123,
            fairness_lag_millis_max=600,
            quota_denied_tenant_total=3,
            quota_denied_project_total=5,
            rebalance_trigger_total=7,
            starvation_prevention_total=2,
        )
    )

    text = exporter.render_prometheus_text()

    assert 'eigen_orch_contract_info{version="2.3.0"} 1' in text
    assert "eigen_orch_queue_depth 42" in text
    assert "eigen_orch_queue_oldest_age_seconds 18.500000" in text
    assert "eigen_orch_queue_avg_age_seconds 4.250000" in text
    assert "eigen_orch_fairness_lag_millis_total 8123" in text
    assert "eigen_orch_fairness_lag_millis_max 600" in text
    assert "eigen_orch_quota_denied_tenant_total 3" in text
    assert "eigen_orch_quota_denied_project_total 5" in text
    assert "eigen_orch_rebalance_trigger_total 7" in text
    assert "eigen_orch_starvation_prevention_total 2" in text


def test_benchmark_metrics_exporter_renders_stable_contract_metrics():
    exporter = BenchmarkTelemetryExporter()
    exporter.update_snapshot(
        BenchmarkMetricsSnapshot(
            contract_version="1.0.0",
            queue_depth=9,
            run_duration_seconds=97.125,
            runs_succeeded_total=120,
            runs_failed_total=8,
            ingestion_failures_total=3,
            stalled_runs=1,
        )
    )

    text = exporter.render_prometheus_text()

    assert 'eigen_bench_contract_info{version="1.0.0"} 1' in text
    assert "eigen_bench_queue_depth 9" in text
    assert "eigen_bench_run_duration_seconds 97.125000" in text
    assert "eigen_bench_runs_succeeded_total 120" in text
    assert "eigen_bench_runs_failed_total 8" in text
    assert "eigen_bench_ingestion_failures_total 3" in text
    assert "eigen_bench_stalled_runs 1" in text

def test_runtime_data_alert_pack_has_required_rules_and_runbooks():
    text = open("monitoring/metrics/prometheus/runtime-data-alerts.yaml", "r", encoding="utf-8").read()
    expected_alerts = {
        "EigenRuntimeDataQueuePressureCritical",
        "EigenRuntimeDataCompileRegressionP95",
        "EigenRuntimeDataCompileRegressionP99Critical",
        "EigenRuntimeDataDriverDegradationErrorRate",
        "EigenRuntimeDataCorrelationBreakage",
    }

    for alert in expected_alerts:
        assert f"alert: {alert}" in text

    assert text.count('runbook: "docs/howto/runtime-data-observability-runbook.md#') == 5
    
def test_adaptive_loop_alert_pack_has_required_rules_runbooks_and_noise_suppression():
    text = open("monitoring/metrics/prometheus/adaptive-loop-alerts.yaml", "r", encoding="utf-8").read()
    expected_alerts = {
        "EigenAdaptiveLoopRetrainQueuePressureCritical",
        "EigenAdaptiveLoopPromotionFailuresSpike",
        "EigenAdaptiveLoopRollbackRateHigh",
        "EigenAdaptiveLoopRollbackRateCritical",
    }

    for alert in expected_alerts:
        assert f"alert: {alert}" in text

    assert text.count('runbook: "docs/howto/adaptive-loop-observability-runbook.md#') == 4
    assert text.count('noise_suppression: "') == 4
    