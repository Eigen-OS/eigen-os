"""Prometheus text exporter for stage latency breakdown and SLO status."""

from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from typing import Mapping

from monitoring.metrics.aggregation.aggregator import StageLatencyAggregator, StageLatencyStats
from monitoring.metrics.aggregation.alerts import StageSLOAlertEvaluator, default_stage_slos


_OBSERVABILITY_CONTRACT_VERSION = "1.0.0"


def _observability_contract_marker_lines() -> list[str]:
    return [
        "# TYPE eigen_observability_contract_info gauge",
        f'eigen_observability_contract_info{{version="{_OBSERVABILITY_CONTRACT_VERSION}"}} 1',
    ]


_ALLOWED_STAGE_LABELS = {
    "validate",
    "compile",
    "optimize",
    "schedule",
    "execute",
    "persist",
    "observability",
    "record-knowledge-observability",
    "finalize",
}

_SENSITIVE_LOG_KEYS = {
    "authorization",
    "password",
    "secret",
    "stacktrace",
    "subject",
    "token",
    "traceparent",
}


_OBSERVABILITY_CONTRACT_VERSION = "1.0.0"


def _observability_contract_marker_lines() -> list[str]:
    return [
        "# TYPE eigen_observability_contract_info gauge",
        f'eigen_observability_contract_info{{version="{_OBSERVABILITY_CONTRACT_VERSION}"}} 1',
    ]


@dataclass(frozen=True)
class OrchestrationMetricsSnapshot:
    """Stable orchestration metrics contract (version 2.3.0, bounded-label baseline)."""

    queue_depth: int
    queue_oldest_age_seconds: float
    queue_avg_age_seconds: float
    fairness_lag_millis_total: int
    fairness_lag_millis_max: int
    quota_denied_tenant_total: int
    quota_denied_project_total: int
    rebalance_trigger_total: int
    starvation_prevention_total: int
    contract_version: str
    schedule_decisions_total: int = 0
    reservation_events_total: int = 0
    split_merge_events_total: int = 0
    replay_events_total: int = 0
    runtime_contract_version: str = "2.1.0"
    cluster_contract_version: str = "1.0.0"
    multidevice_contract_version: str = "3.1.0"


@dataclass(frozen=True)
class BenchmarkMetricsSnapshot:
    """Stable benchmark observability metrics contract (version 1.0.0)."""

    contract_version: str
    queue_depth: int
    run_duration_seconds: float
    runs_succeeded_total: int
    runs_failed_total: int
    ingestion_failures_total: int
    stalled_runs: int


class StageTelemetryExporter:
    def __init__(self, *, max_samples_per_stage: int = 4096) -> None:
        self._aggregator = StageLatencyAggregator(max_samples_per_stage=max_samples_per_stage)
        self._alert_evaluator = StageSLOAlertEvaluator(default_stage_slos())
        self._lock = Lock()

    def observe_stage(self, *, stage: str, latency_seconds: float, is_error: bool = False) -> None:
        self._aggregator.observe(stage=stage, latency_seconds=latency_seconds, is_error=is_error)

    def render_prometheus_text(self) -> str:
        with self._lock:
            stats_by_stage = self._aggregator.snapshot()
            violations = self._alert_evaluator.evaluate(stats_by_stage)

            lines: list[str] = [
                "# TYPE eigen_stage_latency_seconds summary",
                "# TYPE eigen_stage_errors_total counter",
                "# TYPE eigen_stage_samples_total counter",
                "# TYPE eigen_stage_error_rate gauge",
                "# TYPE eigen_stage_slo_violations_total gauge",
            ]
            lines.extend(_observability_contract_marker_lines())

            for stage, stats in sorted(stats_by_stage.items()):
                lines.extend(_encode_stage_stats(stage, stats))

            lines.append(f"eigen_stage_slo_violations_total {len(violations)}")
            for violation in violations:
                lines.append(
                    f'eigen_stage_slo_violation{{stage="{violation.stage}",metric="{violation.metric}",severity="{violation.severity}"}} 1'
                )
            return "\n".join(lines) + "\n"


class BenchmarkTelemetryExporter:
    """Exporter for benchmark queue/run/ingestion lifecycle metrics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot = BenchmarkMetricsSnapshot(
            contract_version="1.0.0",
            queue_depth=0,
            run_duration_seconds=0.0,
            runs_succeeded_total=0,
            runs_failed_total=0,
            ingestion_failures_total=0,
            stalled_runs=0,
        )

    def update_snapshot(self, snapshot: BenchmarkMetricsSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot

    def render_prometheus_text(self) -> str:
        with self._lock:
            snapshot = self._snapshot

        lines: list[str] = [
            "# TYPE eigen_bench_contract_info gauge",
            "# TYPE eigen_bench_queue_depth gauge",
            "# TYPE eigen_bench_run_duration_seconds gauge",
            "# TYPE eigen_bench_runs_succeeded_total counter",
            "# TYPE eigen_bench_runs_failed_total counter",
            "# TYPE eigen_bench_ingestion_failures_total counter",
            "# TYPE eigen_bench_stalled_runs gauge",
        ]
        lines.extend(_observability_contract_marker_lines())
        lines.extend([
            f'eigen_bench_contract_info{{version="{snapshot.contract_version}"}} 1',
            f"eigen_bench_queue_depth {snapshot.queue_depth}",
            f"eigen_bench_run_duration_seconds {snapshot.run_duration_seconds:.6f}",
            f"eigen_bench_runs_succeeded_total {snapshot.runs_succeeded_total}",
            f"eigen_bench_runs_failed_total {snapshot.runs_failed_total}",
            f"eigen_bench_ingestion_failures_total {snapshot.ingestion_failures_total}",
            f"eigen_bench_stalled_runs {snapshot.stalled_runs}",
        ])
        return "\n".join(lines) + "\n"
    
    
class OrchestrationTelemetryExporter:
    """Exporter for queue/fairness/quota/rebalance orchestration metrics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot = OrchestrationMetricsSnapshot(
            contract_version="2.3.0",
            queue_depth=0,
            queue_oldest_age_seconds=0.0,
            queue_avg_age_seconds=0.0,
            fairness_lag_millis_total=0,
            fairness_lag_millis_max=0,
            quota_denied_tenant_total=0,
            quota_denied_project_total=0,
            rebalance_trigger_total=0,
            starvation_prevention_total=0,
        )

    def update_snapshot(self, snapshot: OrchestrationMetricsSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot

    def render_prometheus_text(self) -> str:
        with self._lock:
            snapshot = self._snapshot

        lines: list[str] = [
            "# TYPE eigen_orch_contract_info gauge",
            "# TYPE eigen_runtime_contract_info gauge",
            "# TYPE eigen_cluster_runtime_contract_info gauge",
            "# TYPE eigen_multidevice_contract_info gauge",
            "# TYPE eigen_orch_contract_info gauge",
            "# TYPE eigen_orch_queue_depth gauge",
            "# TYPE eigen_orch_queue_oldest_age_seconds gauge",
            "# TYPE eigen_orch_queue_avg_age_seconds gauge",
            "# TYPE eigen_orch_fairness_lag_millis_total counter",
            "# TYPE eigen_orch_fairness_lag_millis_max gauge",
            "# TYPE eigen_orch_quota_denied_tenant_total counter",
            "# TYPE eigen_orch_quota_denied_project_total counter",
            "# TYPE eigen_orch_schedule_decisions_total counter",
            "# TYPE eigen_orch_reservation_events_total counter",
            "# TYPE eigen_orch_split_merge_events_total counter",
            "# TYPE eigen_orch_replay_events_total counter",
            "# TYPE eigen_orch_rebalance_trigger_total counter",
            "# TYPE eigen_orch_starvation_prevention_total counter",
            ]
        lines.extend(_observability_contract_marker_lines())
        lines.extend([
            f'eigen_orch_contract_info{{version="{snapshot.contract_version}"}} 1',
            f'eigen_runtime_contract_info{{version="{snapshot.runtime_contract_version}"}} 1',
            f'eigen_cluster_runtime_contract_info{{version="{snapshot.cluster_contract_version}"}} 1',
            f'eigen_multidevice_contract_info{{version="{snapshot.multidevice_contract_version}"}} 1',
            f"eigen_orch_queue_depth {snapshot.queue_depth}",
            f"eigen_orch_queue_oldest_age_seconds {snapshot.queue_oldest_age_seconds:.6f}",
            f"eigen_orch_queue_avg_age_seconds {snapshot.queue_avg_age_seconds:.6f}",
            f"eigen_orch_fairness_lag_millis_total {snapshot.fairness_lag_millis_total}",
            f"eigen_orch_fairness_lag_millis_max {snapshot.fairness_lag_millis_max}",
            f"eigen_orch_quota_denied_tenant_total {snapshot.quota_denied_tenant_total}",
            f"eigen_orch_quota_denied_project_total {snapshot.quota_denied_project_total}",
            f"eigen_orch_rebalance_trigger_total {snapshot.rebalance_trigger_total}",
            f"eigen_orch_starvation_prevention_total {snapshot.starvation_prevention_total}",
            f"eigen_orch_schedule_decisions_total {snapshot.schedule_decisions_total}",
            f"eigen_orch_reservation_events_total {snapshot.reservation_events_total}",
            f"eigen_orch_split_merge_events_total {snapshot.split_merge_events_total}",
            f"eigen_orch_replay_events_total {snapshot.replay_events_total}",
        ])
        return "\n".join(lines) + "\n"
    
    
class _MetricsHandler(BaseHTTPRequestHandler):
    exporter: StageTelemetryExporter

    def do_GET(self) -> None:
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        body = self.exporter.render_prometheus_text().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args, **_kwargs):  # pragma: no cover
        return


def start_stage_metrics_server(port: int, exporter: StageTelemetryExporter) -> ThreadingHTTPServer:
    handler_cls = type("StageMetricsHandler", (_MetricsHandler,), {"exporter": exporter})
    server = ThreadingHTTPServer(("0.0.0.0", port), handler_cls)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _encode_stage_stats(stage: str, stats: StageLatencyStats) -> list[str]:
    labels = f'stage="{_bounded_stage_label(stage)}"'
    return [
        f'eigen_stage_latency_seconds{{quantile="0.50",{labels}}} {stats.p50_seconds:.6f}',
        f'eigen_stage_latency_seconds{{quantile="0.95",{labels}}} {stats.p95_seconds:.6f}',
        f'eigen_stage_latency_seconds{{quantile="0.99",{labels}}} {stats.p99_seconds:.6f}',
        f"eigen_stage_errors_total{{{labels}}} {stats.error_count}",
        f"eigen_stage_samples_total{{{labels}}} {stats.sample_count}",
        f"eigen_stage_error_rate{{{labels}}} {stats.error_rate:.6f}",
    ]


def _bounded_stage_label(stage: str) -> str:
    normalized = stage.strip().lower().replace("_", "-")
    return normalized if normalized in _ALLOWED_STAGE_LABELS else "other"


_ALLOWED_OPTIMIZER_OBJECTIVE_LABELS = {
    "balanced",
    "latency_optimized",
    "cost_optimized",
    "availability_optimized",
    "deterministic",
    "compliance",
    "emergency",
    "manual_override",
}

_ALLOWED_OPTIMIZER_RESULT_LABELS = {"selected", "fallback"}

_ALLOWED_FALLBACK_REASON_LABELS = {
    "none",
    "backend_unavailable",
    "confidence_too_low",
    "model_unavailable",
    "timeout",
    "internal_error",
    "policy_rejected",
    "other",
}


def _bounded_optimizer_objective(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    return normalized if normalized in _ALLOWED_OPTIMIZER_OBJECTIVE_LABELS else "balanced"


def _bounded_optimizer_result(value: str) -> str:
    normalized = value.strip().lower()
    return normalized if normalized in _ALLOWED_OPTIMIZER_RESULT_LABELS else "selected"


def _bounded_fallback_reason(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    return normalized if normalized in _ALLOWED_FALLBACK_REASON_LABELS else "other"


def sanitize_observability_metadata(metadata: Mapping[str, str], *, max_value_length: int = 128) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, value in metadata.items():
        normalized_key = key.strip().lower()
        if normalized_key in _SENSITIVE_LOG_KEYS:
            continue
        normalized_value = value.strip()
        if not normalized_value:
            continue
        safe[normalized_key] = normalized_value[:max_value_length]
    return {key: safe[key] for key in sorted(safe)}



@dataclass(frozen=True)
class IntelligentRuntimeMetricsSnapshot:
    """Bounded optimizer-evidence snapshot for the intelligent-runtime surface."""

    contract_version: str = "2.1.0"
    last_confidence_score: float = 0.0
    candidate_trace_counts: dict[tuple[str, str], int] = field(default_factory=dict)
    fallback_reason_counts: dict[str, int] = field(default_factory=dict)
    handoff_counts: dict[str, int] = field(default_factory=dict)
    selected_candidates_total: int = 0


class IntelligentRuntimeTelemetryExporter:
    """Prometheus text exporter for bounded optimizer evidence and trace continuity."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot = IntelligentRuntimeMetricsSnapshot()

    def record_optimizer_candidate_trace(
        self,
        *,
        objective: str,
        confidence_score: float,
        fallback_reason: str,
        selected: bool,
        kernel_to_optimizer_handoff: bool = True,
        optimizer_to_downstream_handoff: bool = True,
    ) -> None:
        objective_label = _bounded_optimizer_objective(objective)
        result_label = _bounded_optimizer_result("selected" if selected else "fallback")
        fallback_label = _bounded_fallback_reason(fallback_reason)
        with self._lock:
            snapshot = self._snapshot
            candidate_counts = dict(snapshot.candidate_trace_counts)
            fallback_counts = dict(snapshot.fallback_reason_counts)
            handoff_counts = dict(snapshot.handoff_counts)

            candidate_key = (objective_label, result_label)
            candidate_counts[candidate_key] = candidate_counts.get(candidate_key, 0) + 1

            if fallback_label != "none":
                fallback_counts[fallback_label] = fallback_counts.get(fallback_label, 0) + 1

            if kernel_to_optimizer_handoff:
                handoff_counts["kernel_to_optimizer"] = handoff_counts.get("kernel_to_optimizer", 0) + 1
            if optimizer_to_downstream_handoff:
                handoff_counts["optimizer_to_downstream"] = handoff_counts.get("optimizer_to_downstream", 0) + 1

            self._snapshot = IntelligentRuntimeMetricsSnapshot(
                contract_version=snapshot.contract_version,
                last_confidence_score=confidence_score,
                candidate_trace_counts=candidate_counts,
                fallback_reason_counts=fallback_counts,
                handoff_counts=handoff_counts,
                selected_candidates_total=snapshot.selected_candidates_total + (1 if selected else 0),
            )

    def render_prometheus_text(self) -> str:
        with self._lock:
            snapshot = self._snapshot

        lines: list[str] = [
            "# TYPE eigen_runtime_contract_info gauge",
            "# TYPE eigen_runtime_optimizer_candidate_traces_total counter",
            "# TYPE eigen_runtime_optimizer_selected_candidates_total counter",
            "# TYPE eigen_runtime_optimizer_fallbacks_total counter",
            "# TYPE eigen_runtime_optimizer_last_confidence_score gauge",
            "# TYPE eigen_runtime_optimizer_trace_handoff_total counter",
            "# TYPE eigen_observability_contract_info gauge",
            f'eigen_observability_contract_info{{version="{_OBSERVABILITY_CONTRACT_VERSION}"}} 1',
            f'eigen_runtime_contract_info{{version="{snapshot.contract_version}"}} 1',
        ]

        for (objective, result), count in sorted(snapshot.candidate_trace_counts.items()):
            lines.append(
                f'eigen_runtime_optimizer_candidate_traces_total{{objective="{objective}",result="{result}"}} {count}'
            )

        lines.append(f"eigen_runtime_optimizer_selected_candidates_total {snapshot.selected_candidates_total}")

        for reason, count in sorted(snapshot.fallback_reason_counts.items()):
            lines.append(f'eigen_runtime_optimizer_fallbacks_total{{reason="{reason}"}} {count}')

        lines.append(f"eigen_runtime_optimizer_last_confidence_score {snapshot.last_confidence_score:.6f}")

        for handoff, count in sorted(snapshot.handoff_counts.items()):
            lines.append(f'eigen_runtime_optimizer_trace_handoff_total{{handoff="{handoff}"}} {count}')

        return "\n".join(lines) + "\n"
    