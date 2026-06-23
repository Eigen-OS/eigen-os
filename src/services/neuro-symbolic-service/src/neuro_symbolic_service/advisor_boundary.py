"""Boundary wrapper for the neuro-symbolic advisor RPC."""

from __future__ import annotations

import hashlib
import json
 
from .grpc_impl import NeuroSymbolicService as _BaseNeuroSymbolicService, _redact_feature_vector
from .observability import append_security_audit_event, record_suggestion_outcome


_DECISION_OUTCOME = {
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
    feature_digest_sha256 = hashlib.sha256(json.dumps(feature_values, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()

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
        request_context = getattr(request, "context", None)
        feature_vector = getattr(request, "feature_vector", b"") or b""
        payload = _feature_vector_payload(feature_vector)
        schema_version = str(getattr(request_context, "feature_schema_version", "")).strip()
        telemetry_feature_set = _tabular_feature_set(payload, response=response, feature_schema_version=schema_version)
        telemetry_feature_set_json = json.dumps(telemetry_feature_set, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
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
                "telemetry_feature_set_json": telemetry_feature_set_json,
                "telemetry_feature_set_sha256": hashlib.sha256(telemetry_feature_set_json.encode("utf-8")).hexdigest(),
                "immutable": True,
            }
        )
        return response
