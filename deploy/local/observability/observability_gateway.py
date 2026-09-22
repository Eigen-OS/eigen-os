from __future__ import annotations

import argparse
import html
import json
import socketserver
import threading
from collections.abc import Iterable, Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

_CONTRACT_VERSION = "1.0.0"

_STAGES = {
    "queue": (0.03, 0.12, 0.24),
    "validate": (0.01, 0.03, 0.05),
    "compile": (0.06, 0.22, 0.38),
    "optimize": (0.04, 0.15, 0.26),
    "schedule": (0.02, 0.08, 0.14),
    "execute": (0.18, 0.90, 1.80),
    "persist": (0.01, 0.04, 0.08),
    "result": (0.01, 0.05, 0.09),
    "finalize": (0.01, 0.02, 0.04),
}

_BENCHMARK_SNAPSHOT = {
    "queue_depth": 24,
    "run_duration_seconds": 84.250000,
    "runs_succeeded_total": 18,
    "runs_failed_total": 2,
    "ingestion_failures_total": 1,
    "stalled_runs": 1,
}

_ORCHESTRATION_SNAPSHOT = {
    "queue_depth": 24,
    "queue_oldest_age_seconds": 37.500000,
    "queue_avg_age_seconds": 8.250000,
    "fairness_lag_millis_total": 2450,
    "fairness_lag_millis_max": 180,
    "quota_denied_tenant_total": 2,
    "quota_denied_project_total": 1,
    "rebalance_trigger_total": 3,
    "starvation_prevention_total": 1,
    "schedule_decisions_total": 48,
    "reservation_events_total": 12,
    "split_merge_events_total": 2,
    "replay_events_total": 4,
}

_CLUSTER_SNAPSHOT = {
    "queue_backlog_depth": 8,
    "queue_oldest_age_seconds": 19.750000,
    "workers_ready": 6,
    "worker_heartbeats_total": 64,
    "worker_flaps_total": 1,
    "worker_restarts_total": 0,
    "queue_lease_churn_total": 7,
    "queue_redeliveries_total": 3,
    "queue_deliveries_total": 92,
    "dead_letter_total": 1,
    "trace_breakage_total": 2,
}

_RUNTIME_DECISION_MODES = ("latency", "throughput", "cost", "balanced")
_RUNTIME_EXPLAIN_LEVELS = ("summary", "detail")
_RUNTIME_OPT_OBJECTIVES = ("balanced", "latency_optimized", "cost_optimized", "availability_optimized")
_RUNTIME_OPT_RESULTS = ("selected", "fallback")
_RUNTIME_HANDOFFS = ("kernel_to_optimizer", "optimizer_to_downstream")

_PLUGIN_TYPES = ("core", "extension", "policy")
_PLUGIN_REJECTION_REASONS = ("compatibility", "signature", "sandbox", "discovery", "activation", "other")

_QUANTUM_SNAPSHOT = {
    "queue_depth": 2,
    "gate_fidelity": 0.993400,
    "readout_fidelity": 0.982100,
    "calibration_age_seconds": 1450.000000,
    "t1_seconds": 92.300000,
    "t2_seconds": 61.700000,
    "topology_degradation_total": 1,
}

_KERNEL_STAGES = ("queue", "validate", "compile", "optimize", "schedule", "execute", "result")


_DEMO_RENDER_LOCK = threading.Lock()
_DEMO_RENDER_COUNT = 0
_DEMO_RENDER_CONTEXT = threading.local()


def _next_demo_tick() -> int:
    global _DEMO_RENDER_COUNT
    with _DEMO_RENDER_LOCK:
        _DEMO_RENDER_COUNT += 1
        _DEMO_RENDER_CONTEXT.tick = _DEMO_RENDER_COUNT
        return _DEMO_RENDER_COUNT


def _current_demo_tick() -> int:
    return getattr(_DEMO_RENDER_CONTEXT, "tick", 0)


def _labels_to_text(labels: Mapping[str, str] | None = None) -> str:
    if not labels:
        return ""
    ordered = sorted((str(key), str(value)) for key, value in labels.items())
    return ",".join(f'{key}="{value.replace("\\", "\\\\").replace("\"", "\\\"")}"' for key, value in ordered)


def _line(name: str, value: object, labels: Mapping[str, str] | None = None) -> str:
    label_text = _labels_to_text(labels)
    if label_text:
        return f"{name}{{{label_text}}} {value}"
    return f"{name} {value}"


def _histogram(
    name: str,
    *,
    buckets: Iterable[float],
    count: int = 0,
    total_sum: float = 0.0,
    labels: Mapping[str, str] | None = None,
    include_type: bool = True,
) -> list[str]:
    base_labels = dict(labels or {})
    bucket_list = list(buckets)
    lines = [f"# TYPE {name} histogram"] if include_type else []
    previous = 0
    bucket_count = max(len(bucket_list), 1)
    for index, bucket in enumerate(bucket_list, start=1):
        bucket_labels = dict(base_labels)
        bucket_labels["le"] = str(bucket)
        cumulative = (count * index) // bucket_count if count > 0 else 0
        cumulative = max(previous, min(cumulative, count))
        lines.append(_line(f"{name}_bucket", cumulative, bucket_labels))
        previous = cumulative
    bucket_labels = dict(base_labels)
    bucket_labels["le"] = "+Inf"
    lines.append(_line(f"{name}_bucket", count, bucket_labels))
    lines.append(_line(f"{name}_sum", f"{total_sum:.6f}", base_labels))
    lines.append(_line(f"{name}_count", count, base_labels))
    return lines


def _summary(name: str, samples: Mapping[str, tuple[float, float, float]], *, labels: Mapping[str, str] | None = None) -> list[str]:
    lines = [f"# TYPE {name} summary"]
    for stage, (p50, p95, p99) in samples.items():
        stage_labels = dict(labels or {})
        stage_labels["stage"] = stage
        lines.append(_line(name, f"{p50:.6f}", {**stage_labels, "quantile": "0.50"}))
        lines.append(_line(name, f"{p95:.6f}", {**stage_labels, "quantile": "0.95"}))
        lines.append(_line(name, f"{p99:.6f}", {**stage_labels, "quantile": "0.99"}))
    return lines


def _render_stage_metrics() -> list[str]:
    lines = _summary("eigen_stage_latency_seconds", _STAGES)
    lines.append("# TYPE eigen_stage_error_rate gauge")
    lines.append("# TYPE eigen_stage_errors_total counter")
    lines.append("# TYPE eigen_stage_slo_violations_total gauge")
    error_rates = {
        "compile": 0.012,
        "optimize": 0.006,
        "schedule": 0.004,
        "execute": 0.018,
    }
    error_counts = {
        "compile": 2,
        "optimize": 1,
        "schedule": 1,
        "execute": 3,
    }
    for stage in _STAGES:
        lines.append(_line("eigen_stage_error_rate", f'{error_rates.get(stage, 0.000):.3f}', {"stage": stage}))
        lines.append(_line("eigen_stage_errors_total", error_counts.get(stage, 0), {"stage": stage}))
    lines.append("eigen_stage_slo_violations_total 2")
    return lines


def _render_benchmark_metrics() -> list[str]:
    tick = _current_demo_tick()
    queue_depth = _BENCHMARK_SNAPSHOT["queue_depth"] + (tick % 4)
    run_duration = _BENCHMARK_SNAPSHOT["run_duration_seconds"] + (tick * 0.45)
    runs_succeeded = _BENCHMARK_SNAPSHOT["runs_succeeded_total"] + (tick * 2)
    runs_failed = _BENCHMARK_SNAPSHOT["runs_failed_total"] + max(tick // 3, 0)
    ingestion_failures = _BENCHMARK_SNAPSHOT["ingestion_failures_total"] + max(tick // 6, 0)
    stalled_runs = _BENCHMARK_SNAPSHOT["stalled_runs"] + (1 if tick % 5 == 0 else 0)
    lines = ["# TYPE eigen_bench_contract_info gauge"]
    lines.append(_line("eigen_bench_contract_info", 1, {"version": _CONTRACT_VERSION}))
    lines.append("# TYPE eigen_bench_queue_depth gauge")
    lines.append(_line("eigen_bench_queue_depth", queue_depth))
    lines.append("# TYPE eigen_bench_run_duration_seconds gauge")
    lines.append(_line("eigen_bench_run_duration_seconds", f'{run_duration:.6f}'))
    for name, value in (
        ("runs_succeeded_total", runs_succeeded),
        ("runs_failed_total", runs_failed),
        ("ingestion_failures_total", ingestion_failures),
        ("stalled_runs", stalled_runs),
    ):
        metric = f"eigen_bench_{name}"
        kind = "counter" if name.endswith("_total") or name.endswith("_failures_total") else "gauge"
        lines.append(f"# TYPE {metric} {kind}")
        lines.append(_line(metric, value))
    return lines


def _render_orchestration_metrics() -> list[str]:
    tick = _current_demo_tick()
    lines = [
        "# TYPE eigen_orch_contract_info gauge",
        _line("eigen_orch_contract_info", 1, {"version": "2.3.0"}),
        "# TYPE eigen_multidevice_contract_info gauge",
        _line("eigen_multidevice_contract_info", 1, {"version": "3.1.0"}),
    ]
    values = {
        "queue_depth": _ORCHESTRATION_SNAPSHOT["queue_depth"] + (tick % 6),
        "queue_oldest_age_seconds": _ORCHESTRATION_SNAPSHOT["queue_oldest_age_seconds"] + (tick * 0.5),
        "queue_avg_age_seconds": _ORCHESTRATION_SNAPSHOT["queue_avg_age_seconds"] + (tick * 0.15),
        "fairness_lag_millis_total": _ORCHESTRATION_SNAPSHOT["fairness_lag_millis_total"] + (tick * 120),
        "fairness_lag_millis_max": _ORCHESTRATION_SNAPSHOT["fairness_lag_millis_max"] + (tick % 12),
        "quota_denied_tenant_total": _ORCHESTRATION_SNAPSHOT["quota_denied_tenant_total"] + (tick % 3),
        "quota_denied_project_total": _ORCHESTRATION_SNAPSHOT["quota_denied_project_total"] + (tick % 2),
        "rebalance_trigger_total": _ORCHESTRATION_SNAPSHOT["rebalance_trigger_total"] + max(tick // 2, 0),
        "starvation_prevention_total": _ORCHESTRATION_SNAPSHOT["starvation_prevention_total"] + (tick % 2),
        "schedule_decisions_total": _ORCHESTRATION_SNAPSHOT["schedule_decisions_total"] + (tick * 4),
        "reservation_events_total": _ORCHESTRATION_SNAPSHOT["reservation_events_total"] + (tick * 2),
        "split_merge_events_total": _ORCHESTRATION_SNAPSHOT["split_merge_events_total"] + max(tick // 4, 0),
        "replay_events_total": _ORCHESTRATION_SNAPSHOT["replay_events_total"] + max(tick // 3, 0),
    }
    for key, value in values.items():
        metric = f"eigen_orch_{key}"
        metric_type = "counter" if key.endswith("_total") else "gauge"
        lines.append(f"# TYPE {metric} {metric_type}")
        lines.append(_line(metric, value))
    return lines


def _render_cluster_metrics() -> list[str]:
    tick = _current_demo_tick()
    queue_backlog = _CLUSTER_SNAPSHOT["queue_backlog_depth"] + (tick % 5)
    queue_oldest_age = _CLUSTER_SNAPSHOT["queue_oldest_age_seconds"] + (tick * 0.75)
    workers_ready = _CLUSTER_SNAPSHOT["workers_ready"]
    lines = [
        "# TYPE eigen_cluster_runtime_contract_info gauge",
        _line("eigen_cluster_runtime_contract_info", 1, {"version": "1.0.0"}),
        "# TYPE eigen_cluster_queue_backlog_depth gauge",
        _line("eigen_cluster_queue_backlog_depth", queue_backlog),
        "# TYPE eigen_cluster_queue_oldest_age_seconds gauge",
        _line("eigen_cluster_queue_oldest_age_seconds", f'{queue_oldest_age:.6f}'),
        "# TYPE eigen_cluster_workers_ready gauge",
        _line("eigen_cluster_workers_ready", workers_ready),
    ]
    values = {
        "worker_heartbeats_total": _CLUSTER_SNAPSHOT["worker_heartbeats_total"] + (tick * 8),
        "worker_flaps_total": _CLUSTER_SNAPSHOT["worker_flaps_total"] + max(tick // 4, 0),
        "worker_restarts_total": _CLUSTER_SNAPSHOT["worker_restarts_total"] + max(tick // 8, 0),
        "queue_lease_churn_total": _CLUSTER_SNAPSHOT["queue_lease_churn_total"] + (tick * 2),
        "queue_redeliveries_total": _CLUSTER_SNAPSHOT["queue_redeliveries_total"] + max(tick // 3, 0),
        "queue_deliveries_total": _CLUSTER_SNAPSHOT["queue_deliveries_total"] + (tick * 11),
        "dead_letter_total": _CLUSTER_SNAPSHOT["dead_letter_total"] + max(tick // 10, 0),
        "trace_breakage_total": _CLUSTER_SNAPSHOT["trace_breakage_total"] + max(tick // 6, 0),
    }
    for key, value in values.items():
        metric = f"eigen_cluster_{key}"
        lines.append(f"# TYPE {metric} counter")
        lines.append(_line(metric, value))

    lines.extend(
        _histogram(
            "eigen_cluster_assignment_latency_ms",
            buckets=(10, 25, 50, 100, 200, 500, 1000),
            count=80 + (tick * 3),
            total_sum=(80 + (tick * 3)) * 132.5,
        )
    )
    lines.extend(
        _histogram(
            "eigen_cluster_trace_propagation_latency_ms",
            buckets=(1, 2, 5, 10, 25, 50, 100),
            count=120 + (tick * 2),
            total_sum=(120 + (tick * 2)) * 7.8,
        )
    )
    return lines


def _render_device_metrics() -> list[str]:
    tick = _current_demo_tick()
    lines = [
        "# TYPE eigen_available_devices gauge",
        _line("eigen_available_devices", 6 + (tick % 2)),
        "# TYPE eigen_cluster_workers_draining gauge",
        _line("eigen_cluster_workers_draining", 1 if tick % 4 == 0 else 0),
        "# TYPE eigen_kernel_queue_depth gauge",
        _line("eigen_kernel_queue_depth", 3 + (tick % 3)),
    ]
    return lines


def _render_runtime_metrics() -> list[str]:
    tick = _current_demo_tick()
    lines = [
        "# TYPE eigen_runtime_contract_info gauge",
        _line("eigen_runtime_contract_info", 1, {"contract_version": "2.1.0"}),
    ]
    decision_base = {
        "latency": 12,
        "throughput": 9,
        "cost": 7,
        "balanced": 15,
    }
    for mode in _RUNTIME_DECISION_MODES:
        lines.append(_line("eigen_runtime_decisions_total", decision_base[mode] + (tick * 2), {"policy_mode": mode}))
    lines.append(_line("eigen_runtime_scoring_failures_total", 2 + max(tick // 6, 0)))
    lines.append(_line("eigen_runtime_explain_errors_total", 1 + max(tick // 12, 0)))
    lines.append(_line("eigen_runtime_fallback_total", 3 + max(tick // 8, 0)))
    lines.append(_line("eigen_runtime_policy_branch_total", 24 + (tick * 3)))
    lines.append(_line("eigen_runtime_optimizer_selected_candidates_total", 19 + (tick * 2)))
    lines.append(_line("eigen_runtime_optimizer_last_confidence_score", "0.870000"))
    lines.append(_line("eigen_runtime_optimizer_fallbacks_total", 3 + max(tick // 10, 0)))
    lines.extend(
        _histogram(
            "eigen_runtime_scoring_latency_ms",
            buckets=(5, 10, 25, 50, 100, 250, 500),
            count=42 + (tick * 2),
            total_sum=(42 + (tick * 2)) * 38.25,
        )
    )
    for index, level in enumerate(_RUNTIME_EXPLAIN_LEVELS):
        lines.extend(
            _histogram(
                "eigen_runtime_explain_latency_ms",
                buckets=(5, 10, 25, 50, 100, 250, 500),
                labels={"level": level},
                count=28 + (tick * 2),
                total_sum=(28 + (tick * 2)) * (12.5 if level == "summary" else 27.5),
                include_type=(index == 0),
            )
        )
    for objective in _RUNTIME_OPT_OBJECTIVES:
        for result in _RUNTIME_OPT_RESULTS:
            base = 4 if result == "selected" else 2
            lines.append(_line("eigen_runtime_optimizer_candidate_traces_total", base + tick, {"objective": objective, "result": result}))
    for handoff in _RUNTIME_HANDOFFS:
        lines.append(_line("eigen_runtime_optimizer_trace_handoff_total", 18 + (tick * 2), {"handoff": handoff}))
    return lines


def _render_plugin_metrics() -> list[str]:
    tick = _current_demo_tick()
    lines = [
        "# TYPE eigen_plugin_observability_contract_info gauge",
        _line("eigen_plugin_observability_contract_info", 1, {"version": "1.0.0"}),
        "# TYPE eigen_plugin_inventory_total gauge",
    ]
    plugin_inventory = {"core": 4, "extension": 7, "policy": 2}
    for plugin_type in _PLUGIN_TYPES:
        lines.append(_line("eigen_plugin_inventory_total", plugin_inventory[plugin_type], {"plugin_type": plugin_type}))
    metric_bases = {
        "attempts_total": 26,
        "failures_total": 3,
        "discovery_failures_total": 1,
        "activation_failures_total": 1,
        "compatibility_rejects_total": 2,
        "signature_rejects_total": 1,
        "sandbox_rejects_total": 1,
        "startup_slo_breaches_total": 1,
    }
    for metric, base in metric_bases.items():
        lines.append(f"# TYPE eigen_plugin_{metric} counter")
        lines.append(_line(f"eigen_plugin_{metric}", base + tick))
    rejection_bases = {
        "compatibility": 2,
        "signature": 1,
        "sandbox": 1,
        "discovery": 1,
        "activation": 1,
        "other": 0,
    }
    for reason in _PLUGIN_REJECTION_REASONS:
        lines.append(_line("eigen_plugin_rejections_total", rejection_bases[reason] + max(tick // 2, 0), {"reason_code": reason}))
    lines.extend(
        _histogram(
            "eigen_plugin_activation_latency_ms",
            buckets=(5, 10, 25, 50, 100, 250, 500),
            count=34 + (tick * 2),
            total_sum=(34 + (tick * 2)) * 18.75,
        )
    )
    lines.extend(
        _histogram(
            "eigen_plugin_startup_critical_path_ms",
            buckets=(5, 10, 25, 50, 100, 250, 500),
            count=22 + (tick * 2),
            total_sum=(22 + (tick * 2)) * 45.0,
        )
    )
    return lines


def _render_quantum_metrics() -> list[str]:
    tick = _current_demo_tick()
    lines = [
        "# TYPE eigen_quantum_queue_depth gauge",
        _line("eigen_quantum_queue_depth", _QUANTUM_SNAPSHOT["queue_depth"] + (tick % 2)),
        "# TYPE eigen_quantum_gate_fidelity gauge",
        _line("eigen_quantum_gate_fidelity", f'{min(_QUANTUM_SNAPSHOT["gate_fidelity"] + (tick * 0.0001), 0.999900):.6f}'),
        "# TYPE eigen_quantum_readout_fidelity gauge",
        _line("eigen_quantum_readout_fidelity", f'{min(_QUANTUM_SNAPSHOT["readout_fidelity"] + (tick * 0.00008), 0.999500):.6f}'),
        "# TYPE eigen_quantum_calibration_age_seconds gauge",
        _line("eigen_quantum_calibration_age_seconds", f'{_QUANTUM_SNAPSHOT["calibration_age_seconds"] + (tick * 60):.6f}'),
        "# TYPE eigen_quantum_t1_seconds gauge",
        _line("eigen_quantum_t1_seconds", f'{_QUANTUM_SNAPSHOT["t1_seconds"]:.6f}'),
        "# TYPE eigen_quantum_t2_seconds gauge",
        _line("eigen_quantum_t2_seconds", f'{_QUANTUM_SNAPSHOT["t2_seconds"]:.6f}'),
        "# TYPE eigen_quantum_topology_degradation_total counter",
        _line("eigen_quantum_topology_degradation_total", _QUANTUM_SNAPSHOT["topology_degradation_total"] + max(tick // 10, 0)),
    ]
    return lines


def _render_system_support_metrics() -> list[str]:
    tick = _current_demo_tick()
    lines = [
        "# TYPE eigen_system_api_contract_info gauge",
        _line("eigen_system_api_contract_info", 1, {"version": "1.0.0"}),
        "# TYPE eigen_kernel_contract_info gauge",
        _line("eigen_kernel_contract_info", 1, {"version": "1.0.0"}),
        "# TYPE eigen_qfs_contract_info gauge",
        _line("eigen_qfs_contract_info", 1, {"version": "1.0.0"}),
        "# TYPE eigen_api_requests_total counter",
        _line("eigen_api_requests_total", 48 + (tick * 5)),
        "# TYPE eigen_api_job_submissions_total counter",
        _line("eigen_api_job_submissions_total", 19 + (tick * 2)),
        "# TYPE eigen_kernel_active_jobs gauge",
        _line("eigen_kernel_active_jobs", 4 + (tick % 2)),
        "# TYPE eigen_qfs_artifact_store_total counter",
        _line("eigen_qfs_artifact_store_total", 23 + (tick * 3)),
        "# TYPE eigen_qfs_artifact_load_total counter",
        _line("eigen_qfs_artifact_load_total", 19 + (tick * 3)),
        "# TYPE eigen_qfs_replay_bundles_total counter",
        _line("eigen_qfs_replay_bundles_total", 5 + max(tick // 4, 0)),
        "# TYPE eigen_kb_contract_info gauge",
        _line("eigen_kb_contract_info", 1, {"version": "1.0.0"}),
    ]

    kb_query_kinds = ("decision_logs", "learning_evidence", "learning_datasets", "learning_models")
    kb_kinds = ("decision_logs", "learning_evidence", "learning_datasets", "learning_models", "benchmark_runs", "runtime_decisions")
    kb_fallback_reasons = ("storage_unavailable", "replay_validation_failed", "ingest_failed")
    kb_quarantine_surfaces = ("runtime", "benchmark", "learning", "dataset", "model", "promotion", "rollback")
    kb_failure_reasons = ("decision_log_pressure", "dataset_assembly", "training", "evaluation", "promotion", "rollback", "ingest")
    kb_contract_outcomes = ("accepted", "error")

    for kind in kb_kinds:
        lines.append(_line("eigen_kb_queries_total", 6 + tick, {"kind": kind}))
        lines.append(_line("eigen_kb_hits_total", 4 + tick, {"kind": kind}))
        lines.append(_line("eigen_kb_misses_total", 2 + max(tick // 2, 0), {"kind": kind}))
    for reason in kb_fallback_reasons:
        lines.append(_line("eigen_kb_fallbacks_total", 1 + max(tick // 3, 0), {"reason": reason}))
    for surface in kb_quarantine_surfaces:
        lines.append(_line("eigen_kb_quarantine_total", 1 + max(tick // 4, 0), {"surface": surface}))
    for reason in kb_failure_reasons:
        lines.append(_line("eigen_kb_learning_failures_total", 1 + max(tick // 5, 0), {"reason": reason}))
    lines.append(_line("eigen_kb_replay_failures_total", 1 + max(tick // 6, 0)))
    for outcome in kb_contract_outcomes:
        
        lines.append(_line("eigen_kb_contract_requests_total", 12 + tick, {"contract_version": "1.0.0", "outcome": outcome}))

    api_count = 62 + (tick * 4)

    lines.extend(
        _histogram(
            "eigen_api_request_duration_seconds",
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
            count=api_count,
            total_sum=api_count * 0.0825,
        )
    )
    stages = ("queue", "validate", "compile", "optimize", "schedule", "execute", "result")
    for index, stage in enumerate(stages):
        stage_count = 18 + (tick * 2)
        lines.extend(
            _histogram(
                "eigen_kernel_stage_duration_seconds",
                buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
                labels={"stage": stage},
                count=stage_count,
                total_sum=stage_count * (0.018 if stage != "execute" else 0.225),
                include_type=(index == 0),
            )
        )
    return lines


def render_metrics_text() -> str:
    parts = [
        "# TYPE eigen_observability_contract_info gauge",
        f'eigen_observability_contract_info{{version="{_CONTRACT_VERSION}"}} 1',
    ]
    parts.extend(_render_stage_metrics())
    parts.extend(_render_benchmark_metrics())
    parts.extend(_render_orchestration_metrics())
    parts.extend(_render_cluster_metrics())
    parts.extend(_render_device_metrics())
    parts.extend(_render_runtime_metrics())
    parts.extend(_render_plugin_metrics())
    parts.extend(_render_quantum_metrics())
    parts.extend(_render_system_support_metrics())
    return "\n".join(parts) + "\n"


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/healthz"}:
            if self.path == "/":
                body = b"ok"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        body = render_metrics_text().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args, **_kwargs):  # pragma: no cover - keep stdout clean
        return


class LandingProxyHandler(BaseHTTPRequestHandler):
    upstream_base_url: str = ""
    title: str = "Service"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            body = self._landing_body().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        
        if self.path in {"/health", "/healthz"}:
            body = json.dumps(
                {
                    "ok": True,
                    "service": self.title,
                    "upstream": self.upstream_base_url,
                    "path": self.path,
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self._proxy()

    def _landing_body(self) -> str:
        upstream = html.escape(self.upstream_base_url)
        title = html.escape(self.title)
        return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>{title}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.45; }}
code, a {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
.card {{ max-width: 52rem; padding: 1.25rem 1.5rem; border: 1px solid #ddd; border-radius: 14px; }}
small {{ color: #666; }}
</style></head><body>
<div class=\"card\">
  <h1>{title}</h1>
  <p>This host port is a friendly landing page. The live upstream service is still available inside the Docker network at <code>{upstream}</code>.</p>
  <p><a href=\"/metrics\">/metrics</a> · <a href=\"/ready\">/ready</a> · <a href=\"/health\">/health</a></p>
  <small>Root path returns 200 instead of 404 so local checks stay clear.</small>
</div>
</body></html>"""

    def _proxy(self) -> None:
        upstream = urljoin(self.upstream_base_url.rstrip("/") + "/", self.path.lstrip("/"))
        request = Request(upstream, method="GET")
        try:
            with urlopen(request, timeout=5) as response:
                body = response.read()
                self.send_response(getattr(response, "status", 200))
                content_type = response.headers.get("Content-Type", "application/octet-stream")
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except HTTPError as exc:
            body = exc.read() if hasattr(exc, "read") else b""
            self.send_response(exc.code)
            content_type = exc.headers.get("Content-Type", "text/plain; charset=utf-8") if exc.headers else "text/plain; charset=utf-8"
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except URLError as exc:
            body = json.dumps({"error": f"upstream unavailable: {exc.reason}"}).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *_args, **_kwargs):  # pragma: no cover - keep stdout clean
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Local observability helper")
    parser.add_argument("--mode", choices=("metrics", "proxy"), required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--listen-host", default="0.0.0.0")
    parser.add_argument("--title", default="Observability")
    parser.add_argument("--upstream-base-url", default="")
    args = parser.parse_args()

    if args.mode == "proxy" and not args.upstream_base_url:
        raise SystemExit("--upstream-base-url is required in proxy mode")

    if args.mode == "metrics":
        handler_cls = MetricsHandler
    else:
        handler_cls = type(
            "_LandingProxyHandler",
            (LandingProxyHandler,),
            {"upstream_base_url": args.upstream_base_url, "title": args.title},
        )

    server = ThreadingHTTPServer((args.listen_host, args.port), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        thread.join()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
