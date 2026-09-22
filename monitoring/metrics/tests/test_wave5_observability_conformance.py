from monitoring.metrics.prometheus.exporter import (
    BenchmarkMetricsSnapshot,
    BenchmarkTelemetryExporter,
    OrchestrationMetricsSnapshot,
    OrchestrationTelemetryExporter,
    IntelligentRuntimeTelemetryExporter,
    StageTelemetryExporter,
    sanitize_observability_metadata,
)


def test_wave5_contract_markers_and_bounded_metrics_are_present() -> None:
    exporter = OrchestrationTelemetryExporter()
    exporter.update_snapshot(
        OrchestrationMetricsSnapshot(
            contract_version="3.1.0",
            runtime_contract_version="2.1.0",
            cluster_contract_version="1.0.0",
            multidevice_contract_version="3.1.0",
            queue_depth=7,
            queue_oldest_age_seconds=12.5,
            queue_avg_age_seconds=4.25,
            fairness_lag_millis_total=19,
            fairness_lag_millis_max=6,
            quota_denied_tenant_total=1,
            quota_denied_project_total=2,
            rebalance_trigger_total=3,
            starvation_prevention_total=4,
            schedule_decisions_total=5,
            reservation_events_total=6,
            split_merge_events_total=7,
            replay_events_total=8,
        )
    )

    text = exporter.render_prometheus_text()

    assert 'eigen_observability_contract_info{version="1.0.0"} 1' in text
    assert 'eigen_orch_contract_info{version="3.1.0"} 1' in text
    assert 'eigen_observability_contract_info{version="1.0.0"} 1' in text
    assert 'eigen_runtime_contract_info{version="2.1.0"} 1' in text
    assert 'eigen_cluster_runtime_contract_info{version="1.0.0"} 1' in text
    assert 'eigen_multidevice_contract_info{version="3.1.0"} 1' in text
    assert "job_id=" not in text
    assert "trace_id=" not in text
    assert "request_id=" not in text


def test_stage_labels_are_bounded_and_deterministic() -> None:
    exporter = StageTelemetryExporter(max_samples_per_stage=128)
    exporter.observe_stage(stage="Execute", latency_seconds=0.50)
    exporter.observe_stage(stage="execute", latency_seconds=0.75)
    exporter.observe_stage(stage="traceparent::evil", latency_seconds=1.25)

    text = exporter.render_prometheus_text()

    assert 'stage="execute"' in text
    assert 'stage="other"' in text
    assert "traceparent" not in text
    assert "request_id" not in text


def test_sanitized_metadata_drops_sensitive_fields() -> None:
    safe = sanitize_observability_metadata(
        {
            "traceparent": "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01",
            "request_id": "req-001",
            "backend_id": "backend-a",
            "subject": "alice@example.com",
            "token": "secret-token",
            "note": "ok",
        }
    )

    assert "traceparent" not in safe
    assert "subject" not in safe
    assert "token" not in safe
    assert safe["request_id"] == "req-001"
    assert safe["backend_id"] == "backend-a"
    assert safe["note"] == "ok"


def test_wave7a_optimizer_candidate_traces_are_bounded_and_visible() -> None:
    exporter = IntelligentRuntimeTelemetryExporter()
    exporter.record_optimizer_candidate_trace(
        objective="balanced",
        confidence_score=0.92,
        fallback_reason="none",
        selected=True,
    )
    exporter.record_optimizer_candidate_trace(
        objective="latency-optimized",
        confidence_score=0.74,
        fallback_reason="confidence-too-low",
        selected=False,
    )
    text = exporter.render_prometheus_text()

    assert 'eigen_runtime_contract_info{version="2.1.0"} 1' in text
    assert 'eigen_runtime_optimizer_candidate_traces_total{objective="balanced",result="selected"} 1' in text
    assert 'eigen_runtime_optimizer_candidate_traces_total{objective="latency_optimized",result="fallback"} 1' in text
    assert 'eigen_runtime_optimizer_fallbacks_total{reason="confidence_too_low"} 1' in text
    assert 'eigen_runtime_optimizer_trace_handoff_total{handoff="kernel_to_optimizer"} 2' in text
    assert 'eigen_runtime_optimizer_trace_handoff_total{handoff="optimizer_to_downstream"} 2' in text
    assert 'eigen_runtime_optimizer_last_confidence_score 0.740000' in text
    assert 'trace_id=' not in text
    assert 'request_id=' not in text
    