"""Bounded intelligent-runtime observability fixtures for optimizer traces."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

_ALLOWED_OBJECTIVES = {
    "balanced",
    "latency_optimized",
    "cost_optimized",
    "availability_optimized",
    "deterministic",
    "compliance",
    "emergency",
    "manual_override",
}

_ALLOWED_RESULTS = {"selected", "fallback"}

_ALLOWED_FALLBACK_REASONS = {
    "none",
    "backend_unavailable",
    "confidence_too_low",
    "model_unavailable",
    "timeout",
    "internal_error",
    "policy_rejected",
    "other",
}

_ALLOWED_HANDOFFS = {
    "kernel_to_optimizer",
    "optimizer_to_downstream",
}


def _bounded_objective(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    return normalized if normalized in _ALLOWED_OBJECTIVES else "balanced"


def _bounded_result(value: str) -> str:
    normalized = value.strip().lower()
    return normalized if normalized in _ALLOWED_RESULTS else "selected"


def _bounded_fallback_reason(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    return normalized if normalized in _ALLOWED_FALLBACK_REASONS else "other"


def _bounded_handoff(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    return normalized if normalized in _ALLOWED_HANDOFFS else "optimizer_to_downstream"


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
        objective_label = _bounded_objective(objective)
        result_label = _bounded_result("selected" if selected else "fallback")
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
