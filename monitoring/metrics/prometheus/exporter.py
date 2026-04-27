"""Prometheus text exporter for stage latency breakdown and SLO status."""

from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread

from monitoring.metrics.aggregation.aggregator import StageLatencyAggregator, StageLatencyStats
from monitoring.metrics.aggregation.alerts import StageSLOAlertEvaluator, default_stage_slos


@dataclass(frozen=True)
class OrchestrationMetricsSnapshot:
    """Stable orchestration metrics contract (version 2.3.0)."""

    contract_version: str
    queue_depth: int
    queue_oldest_age_seconds: float
    queue_avg_age_seconds: float
    fairness_lag_millis_total: int
    fairness_lag_millis_max: int
    quota_denied_tenant_total: int
    quota_denied_project_total: int
    rebalance_trigger_total: int
    starvation_prevention_total: int


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

            for stage, stats in sorted(stats_by_stage.items()):
                lines.extend(_encode_stage_stats(stage, stats))

            lines.append(f"eigen_stage_slo_violations_total {len(violations)}")
            for violation in violations:
                lines.append(
                    f'eigen_stage_slo_violation{{stage="{violation.stage}",metric="{violation.metric}",severity="{violation.severity}"}} 1'
                )
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
            "# TYPE eigen_orch_queue_depth gauge",
            "# TYPE eigen_orch_queue_oldest_age_seconds gauge",
            "# TYPE eigen_orch_queue_avg_age_seconds gauge",
            "# TYPE eigen_orch_fairness_lag_millis_total counter",
            "# TYPE eigen_orch_fairness_lag_millis_max gauge",
            "# TYPE eigen_orch_quota_denied_tenant_total counter",
            "# TYPE eigen_orch_quota_denied_project_total counter",
            "# TYPE eigen_orch_rebalance_trigger_total counter",
            "# TYPE eigen_orch_starvation_prevention_total counter",
            f'eigen_orch_contract_info{{version="{snapshot.contract_version}"}} 1',
            f"eigen_orch_queue_depth {snapshot.queue_depth}",
            f"eigen_orch_queue_oldest_age_seconds {snapshot.queue_oldest_age_seconds:.6f}",
            f"eigen_orch_queue_avg_age_seconds {snapshot.queue_avg_age_seconds:.6f}",
            f"eigen_orch_fairness_lag_millis_total {snapshot.fairness_lag_millis_total}",
            f"eigen_orch_fairness_lag_millis_max {snapshot.fairness_lag_millis_max}",
            f"eigen_orch_quota_denied_tenant_total {snapshot.quota_denied_tenant_total}",
            f"eigen_orch_quota_denied_project_total {snapshot.quota_denied_project_total}",
            f"eigen_orch_rebalance_trigger_total {snapshot.rebalance_trigger_total}",
            f"eigen_orch_starvation_prevention_total {snapshot.starvation_prevention_total}",
        ]
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
    labels = f'stage="{stage}"'
    return [
        f'eigen_stage_latency_seconds{{quantile="0.50",{labels}}} {stats.p50_seconds:.6f}',
        f'eigen_stage_latency_seconds{{quantile="0.95",{labels}}} {stats.p95_seconds:.6f}',
        f'eigen_stage_latency_seconds{{quantile="0.99",{labels}}} {stats.p99_seconds:.6f}',
        f"eigen_stage_errors_total{{{labels}}} {stats.error_count}",
        f"eigen_stage_samples_total{{{labels}}} {stats.sample_count}",
        f"eigen_stage_error_rate{{{labels}}} {stats.error_rate:.6f}",
    ]
