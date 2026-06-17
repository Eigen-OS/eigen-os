"""Boundary wrapper for the compiler-facing neuro-symbolic advisor."""

from __future__ import annotations

from collections import Counter
import logging
import threading

from .grpc_impl import NeuroSymbolicService as _BaseNeuroSymbolicService, render_metrics_text as _base_render_metrics_text

_LOG = logging.getLogger("eigen_compiler")
_METRICS_LOCK = threading.Lock()
_SUGGESTION_OUTCOMES_TOTAL = Counter()

_DECISION_TO_OUTCOME = {
    1: "accepted",
    2: "transformed",
    3: "rejected",
}


def record_suggestion_outcome(outcome: str) -> None:
    with _METRICS_LOCK:
        _SUGGESTION_OUTCOMES_TOTAL[str(outcome)] += 1


def render_metrics_text() -> str:
    with _METRICS_LOCK:
        lines = [_base_render_metrics_text().rstrip("\n")]
        lines.append("# TYPE eigen_compiler_suggestion_outcomes_total counter")
        for outcome, count in sorted(_SUGGESTION_OUTCOMES_TOTAL.items()):
            lines.append(f'eigen_compiler_suggestion_outcomes_total{{outcome="{outcome}"}} {count}')
        return "\n".join(lines) + "\n"


def _request_context(request) -> object:
    return getattr(request, "context", None)


class NeuroSymbolicService(_BaseNeuroSymbolicService):
    """Decorator that records compiler boundary suggestion outcomes."""

    def ScoreCompilationPlan(self, request, context):  # noqa: N802 - gRPC method name
        response = super().ScoreCompilationPlan(request, context)
        outcome = _DECISION_TO_OUTCOME.get(int(response.decision), "rejected")
        record_suggestion_outcome(outcome)
        request_context = _request_context(request)
        _LOG.info(
            "compiler advisor suggestion outcome recorded",
            extra={
                "rpc": "ScoreCompilationPlan",
                "request_id": getattr(response, "request_id", ""),
                "tenant_id": getattr(response, "tenant_id", ""),
                "project_id": getattr(response, "project_id", ""),
                "subject_id": getattr(request_context, "subject_id", ""),
                "workload_id": getattr(request_context, "workload_id", ""),
                "authz_decision_id": getattr(request_context, "authz_decision_id", ""),
                "trace_id": getattr(request_context, "trace_id", ""),
                "traceparent": getattr(request_context, "traceparent", ""),
                "policy_snapshot_version": getattr(response, "policy_snapshot_version", ""),
                "model_version": getattr(response, "model_version", ""),
                "decision": int(response.decision),
                "suggestion_outcome": outcome,
            },
        )
        return response
