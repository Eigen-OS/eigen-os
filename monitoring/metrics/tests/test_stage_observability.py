from monitoring.metrics.aggregation.aggregator import StageLatencyAggregator
from monitoring.metrics.aggregation.alerts import StageSLOAlertEvaluator, default_stage_slos
from monitoring.metrics.prometheus.exporter import StageTelemetryExporter


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
