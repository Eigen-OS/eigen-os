"""Boundary wrapper for the compiler-facing neuro-symbolic advisor."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import logging
import threading

from .grpc_impl import NeuroSymbolicService as _BaseNeuroSymbolicService, _redact_feature_vector, render_metrics_text as _base_render_metrics_text


_LOG = logging.getLogger("eigen_compiler")
_METRICS_LOCK = threading.Lock()
_SUGGESTION_OUTCOMES_TOTAL = Counter()

_DECISION_TO_OUTCOME = {
    1: "accepted",
    2: "transformed",
    3: "rejected",
}


_TABULAR_FEATURE_SCHEMA_VERSION = "telemetry-tabular-v1"
_TABULAR_FEATURE_ORDER = (
    "graph_size_nodes",
    "graph_size_edges",
    "graph_size_total",
    "graph_fanout_max",
    "graph_fanout_mean",
    "stage_count",
    "stage_success_count",
    "stage_failure_count",
    "stage_success_rate",
    "past_success_count",
    "past_failure_count",
    "past_success_rate",
    "latency_ms",
    "backend",
    "policy_state",
)


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


def _feature_vector_payload(feature_vector: bytes) -> dict[str, object]:
    if not feature_vector:
        return {}
    try:
        payload = json.loads(feature_vector.decode("utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _first_mapping(payload: dict[str, object], *keys: str) -> dict[str, object]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _graph_summary(payload: dict[str, object]) -> dict[str, object]:
    graph = _first_mapping(payload, "telemetry_feature_set", "graph", "graph_encoding", "graph_summary", "logical_graph_schema")
    if not graph:
        graph_interface = _first_mapping(payload, "graph_interface", "optimizer_graph_interface")
        if graph_interface:
            graph = _first_mapping(graph_interface, "logical_graph", "physical_graph") or graph_interface
    if not graph and isinstance(payload.get("nodes"), list):
        graph = payload
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(edges, list):
        edges = []
    outgoing: dict[str, int] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = str(edge.get("source", "")).strip()
        if not source:
            continue
        outgoing[source] = outgoing.get(source, 0) + 1
    node_count = len(nodes)
    edge_count = len(edges)
    return {
        "graph_kind": str(graph.get("graph_kind", payload.get("graph_kind", "telemetry_graph"))).strip() or "telemetry_graph",
        "graph_size_nodes": node_count,
        "graph_size_edges": edge_count,
        "graph_size_total": node_count + edge_count,
        "graph_fanout_max": max(outgoing.values(), default=0),
        "graph_fanout_mean": round(edge_count / max(node_count, 1), 6),
    }


def _tabular_feature_set(payload: dict[str, object], *, response, feature_schema_version: str) -> dict[str, object]:
    source = _first_mapping(payload, "telemetry_feature_set")
    if not source:
        source = dict(payload)

    graph = _graph_summary(source)
    compiler = _first_mapping(source, "compiler", "compiler_telemetry")
    kb = _first_mapping(source, "kb", "kb_telemetry")
    telemetry_sources = [
        name
        for name in ("compiler", "kb")
        if any(key in source for key in (name, f"{name}_telemetry"))
    ] or ["compiler", "kb"]

    stage_count = max(int(compiler.get("stage_count", 0) or 0), 0)
    stage_success_count = max(int(compiler.get("stage_success_count", stage_count) or stage_count), 0)
    stage_failure_count = max(int(compiler.get("stage_failure_count", 0) or 0), 0)
    if stage_count <= 0:
        stage_count = stage_success_count + stage_failure_count
    stage_success_rate = round(stage_success_count / max(stage_success_count + stage_failure_count, 1), 6)

    latency_value = compiler.get("latency_ms", source.get("latency_ms", 0.0))
    try:
        latency_ms = round(float(latency_value or 0.0), 6)
    except (TypeError, ValueError):
        latency_ms = 0.0

    backend = str(
        compiler.get("backend")
        or source.get("backend")
        or source.get("backend_profile")
        or source.get("backend_target")
        or getattr(response, "model_version", "")
    ).strip()
    policy_state = str(
        compiler.get("policy_state")
        or source.get("policy_state")
        or source.get("policy_snapshot_version")
        or getattr(response, "policy_snapshot_version", "")
    ).strip()

    past_success_count = max(int(kb.get("past_success_count", 0) or 0), 0)
    past_failure_count = max(int(kb.get("past_failure_count", 0) or 0), 0)
    past_success_rate = kb.get("past_success_rate")
    if past_success_rate in (None, ""):
        past_success_rate = round(
            past_success_count / max(past_success_count + past_failure_count, 1),
            6,
        )
    else:
        try:
            past_success_rate = round(float(past_success_rate), 6)
        except (TypeError, ValueError):
            past_success_rate = 0.0

    feature_values = {
        "graph_size_nodes": graph["graph_size_nodes"],
        "graph_size_edges": graph["graph_size_edges"],
        "graph_size_total": graph["graph_size_total"],
        "graph_fanout_max": graph["graph_fanout_max"],
        "graph_fanout_mean": graph["graph_fanout_mean"],
        "stage_count": stage_count,
        "stage_success_count": stage_success_count,
        "stage_failure_count": stage_failure_count,
        "stage_success_rate": stage_success_rate,
        "past_success_count": past_success_count,
        "past_failure_count": past_failure_count,
        "past_success_rate": past_success_rate,
        "latency_ms": latency_ms,
        "backend": backend,
        "policy_state": policy_state,
    }
    feature_digest_sha256 = hashlib.sha256(_stable_json(feature_values).encode("utf-8")).hexdigest()

    return {
        "schema_version": _TABULAR_FEATURE_SCHEMA_VERSION,
        "source": "compiler_and_kb_telemetry",
        "offline_online_parity": True,
        "feature_order": list(_TABULAR_FEATURE_ORDER),
        "feature_count": len(feature_values),
        "feature_values": feature_values,
        "feature_digest_sha256": feature_digest_sha256,
        "graph": graph,
        "compiler": {
            "stage_count": stage_count,
            "stage_success_count": stage_success_count,
            "stage_failure_count": stage_failure_count,
            "stage_success_rate": stage_success_rate,
            "latency_ms": latency_ms,
            "backend": backend,
            "policy_state": policy_state,
        },
        "kb": {
            "past_success_count": past_success_count,
            "past_failure_count": past_failure_count,
            "past_success_rate": past_success_rate,
        },
        "telemetry_sources": telemetry_sources,
    }


def _explainability_envelope(request, response) -> dict[str, object]:
    request_context = _request_context(request)
    feature_vector = getattr(request, "feature_vector", b"") or b""
    feature_digest = hashlib.sha256(feature_vector).hexdigest() if feature_vector else str(getattr(request, "feature_digest_sha256", "")).strip().lower()
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
        feature_digest = hashlib.sha256(_redact_feature_vector(feature_vector).feature_vector).hexdigest()

    feature_payload = _feature_vector_payload(feature_vector)
    telemetry_feature_set = _tabular_feature_set(feature_payload, response=response, feature_schema_version=schema_version)
    telemetry_feature_set_json = _stable_json(telemetry_feature_set)
    telemetry_feature_set_sha256 = hashlib.sha256(telemetry_feature_set_json.encode("utf-8")).hexdigest()

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
            "telemetry_feature_set": telemetry_feature_set,
            "telemetry_feature_set_json": telemetry_feature_set_json,
            "telemetry_feature_set_sha256": telemetry_feature_set_sha256,
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
