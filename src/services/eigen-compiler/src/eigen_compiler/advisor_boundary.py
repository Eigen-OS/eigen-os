"""Boundary wrapper for the compiler-facing neuro-symbolic advisor."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
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


def _stable_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _explainability_envelope(request, response) -> dict[str, object]:
    request_context = _request_context(request)
    feature_vector = getattr(request, "feature_vector", b"") or b""
    feature_digest = str(getattr(request, "feature_digest_sha256", "")).strip().lower()
    model_hint = str(getattr(request, "model_hint", "")).strip()
    schema_version = str(getattr(request_context, "feature_schema_version", "")).strip()
    request_id = str(getattr(response, "request_id", "")).strip()
    tenant_id = str(getattr(response, "tenant_id", "")).strip()
    project_id = str(getattr(response, "project_id", "")).strip()
    policy_snapshot_version = str(getattr(response, "policy_snapshot_version", "")).strip()
    model_version = str(getattr(response, "model_version", "")).strip()
    replay_digest = str(getattr(response, "replay_digest", "")).strip()
    explanation_ref = str(getattr(response, "explanation_ref", "")).strip()

    if not feature_digest:
        feature_digest = hashlib.sha256(feature_vector).hexdigest()

    return {
        "contract_version": str(getattr(response, "contract_version", "")).strip(),
        "request_id": request_id,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "policy_snapshot_version": policy_snapshot_version,
        "model_version": model_version,
        "confidence": float(getattr(response, "confidence", 0.0)),
        "feature_set": {
            "schema_version": schema_version,
            "model_hint": model_hint,
            "feature_digest_sha256": feature_digest,
            "minimized_feature_vector_sha256": hashlib.sha256(feature_vector).hexdigest(),
            "minimized_feature_vector_bytes": len(feature_vector),
            "redacted_fields": [],
        },
        "retrieval_references": [
            f"nsc://feature-set/{tenant_id}/{project_id}/{request_id}/{feature_digest}",
            f"nsc://policy-snapshot/{policy_snapshot_version}",
            f"nsc://model/{model_version}",
        ],
        "retrieval_reference_count": 3,
        "replay_digest": replay_digest,
        "decision_digest": replay_digest,
        "explanation_ref": explanation_ref,
    }


class NeuroSymbolicService(_BaseNeuroSymbolicService):
    """Decorator that records compiler boundary suggestion outcomes."""

    def ScoreCompilationPlan(self, request, context):  # noqa: N802 - gRPC method name
        response = super().ScoreCompilationPlan(request, context)
        outcome = _DECISION_TO_OUTCOME.get(int(response.decision), "rejected")
        record_suggestion_outcome(outcome)
        request_context = _request_context(request)
        envelope = _explainability_envelope(request, response)
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
                "explainability_envelope": envelope,
                "explainability_envelope_json": _stable_json(envelope),
            },
        )
        return response
