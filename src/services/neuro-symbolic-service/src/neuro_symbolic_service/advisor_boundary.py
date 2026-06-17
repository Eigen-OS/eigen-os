"""Boundary wrapper for the neuro-symbolic advisor RPC."""

from __future__ import annotations

from .grpc_impl import NeuroSymbolicService as _BaseNeuroSymbolicService
from .observability import append_security_audit_event, record_suggestion_outcome


_DECISION_OUTCOME = {
    1: "accepted",
    2: "transformed",
    3: "rejected",
}


class NeuroSymbolicService(_BaseNeuroSymbolicService):
    """Decorator that records compiler-facing suggestion outcomes.

    The base implementation remains authoritative for scoring, policy checks,
    and deterministic replay. This wrapper only records how the suggestion was
    consumed at the safe compiler boundary.
    """

    def ScoreCompilationPlan(self, request, context):  # noqa: N802 - gRPC method name
        response = super().ScoreCompilationPlan(request, context)
        outcome = _DECISION_OUTCOME.get(int(response.decision), "rejected")
        record_suggestion_outcome(outcome)
        append_security_audit_event(
            {
                "audit_kind": "advisor_suggestion_outcome",
                "operation": "ScoreCompilationPlan",
                "request_id": response.request_id,
                "tenant": response.tenant_id,
                "project_id": response.project_id,
                "policy_snapshot_version": response.policy_snapshot_version,
                "model_version": response.model_version,
                "suggestion_outcome": outcome,
                "decision": int(response.decision),
                "immutable": True,
            }
        )
        return response
