"""Deterministic Eigen-Lang -> AQO compiler core."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Iterator, TypeVar

from .errors import FieldViolation
from .validation import (
    backend_contract_payload,
    resolve_workload_profile,
    validate_workload_profile,
    workload_profile_payload,
)

AQO_VERSION = "1.0.0"

_SYMBOLIC_CANDIDATE_ENUMERATION_VERSION = "1.0.0"
_SYMBOLIC_CANDIDATE_BUDGET = 8
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

_ADVISORY_MODEL_FAMILY = "deterministic"
_ADVISORY_MODEL_VERSION = "compiler-advisory-v1"
_ADVISORY_SELECTION_MODE = "deterministic_legal_preference"
_ADVISORY_FALLBACK_REASON_NO_LEGAL_CANDIDATES = "no_legal_candidates"

_REPLAY_MODE_DETERMINISTIC = "deterministic"
_NEURO_MODEL_VERSION_ENV = "EIGEN_NEURO_SYMBOLIC_MODEL_VERSION"
_NEURO_POLICY_SNAPSHOT_VERSION_ENV = "EIGEN_NEURO_SYMBOLIC_POLICY_SNAPSHOT_VERSION"

_ALLOWED_IMPORT_PREFIXES = ("eigen_lang",)
_FORBIDDEN_MODULE_ROOTS = {"os", "sys", "subprocess"}
_FORBIDDEN_CALLS = {"exec", "eval", "compile"}
_ALLOWED_SANDBOX_PROFILES = {"default", "restricted", "strict"}

_AQO_ALLOWED_TOP_LEVEL_FIELDS = {
    "version",
    "qubits",
    "operations",
    "parameters",
    "metadata",
    "checksums",
    "topology",
    "annotations",
}

_AQO_ALLOWED_OPS = {
    "RX",
    "RY",
    "RZ",
    "CX",
    "CZ",
    "SWAP",
    "CCX",
    "CCZ",
    "X",
    "Y",
    "Z",
    "H",
    "S",
    "T",
    "MEASURE",
    "RESET",
}
_AQO_ROTATION_OPS = {"RX", "RY", "RZ"}
_AQO_MEASUREMENT_BASIS = {"X", "Y", "Z"}
_AQO_NON_PARAMETERIZED_OPS = {
    "CX",
    "CZ",
    "SWAP",
    "CCX",
    "CCZ",
    "X",
    "Y",
    "Z",
    "H",
    "S",
    "T",
    "RESET",
}
_AQO_ARITY = {
    "RX": 1,
    "RY": 1,
    "RZ": 1,
    "CX": 2,
    "CZ": 2,
    "SWAP": 2,
    "CCX": 3,
    "CCZ": 3,
    "X": 1,
    "Y": 1,
    "Z": 1,
    "H": 1,
    "S": 1,
    "T": 1,
    "MEASURE": 1,
    "RESET": 1,
}

T = TypeVar("T")
StageObserver = Callable[[str, float, str], None]


@dataclass(frozen=True)
class CompileRequestContext:
    request_id: str = ""
    trace_id: str = ""
    traceparent: str = ""
    deadline: str = ""
    retry_policy: str = ""
    security_context: str = ""
    sandbox_profile: str = "strict"
    tenant_id: str = ""
    project_id: str = ""


@dataclass(frozen=True)
class CompilationResult:
    aqo_json: bytes
    metadata: dict[str, str]


@dataclass(frozen=True)
class DistributedCompileConfig:
    enabled: bool
    target: str | None
    partition_count: int | None
    queue_provider: str | None
    topology_hint: str | None


@dataclass(frozen=True)
class CompilerPassRecord:
    name: str
    kind: str
    rule: str
    preconditions: tuple[str, ...]
    postconditions: tuple[str, ...]
    input: dict[str, object]
    output: dict[str, object]


@dataclass(frozen=True)
class CompilerPassPipeline:
    records: tuple[CompilerPassRecord, ...]
    aqo: dict[str, object]


@dataclass(frozen=True)
class SymbolicCandidate:
    candidate_id: str
    features: dict[str, object]
    legal: bool
    legality_reason: str


@dataclass(frozen=True)
class SymbolicCandidateSet:
    version: str
    candidate_budget: int
    candidates: tuple[SymbolicCandidate | str, ...]


@dataclass
class CompilerValidationError(Exception):
    violations: tuple[FieldViolation, ...]


def _run_stage(stage: str, observer: StageObserver | None, fn: Callable[[], T]) -> T:
    start = perf_counter()
    try:
        result = fn()
    except Exception:
        if observer is not None:
            observer(stage, perf_counter() - start, "failure")
        raise
    if observer is not None:
        observer(stage, perf_counter() - start, "success")
    return result


def _canonical_json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _canonical_json_text(payload: dict[str, object]) -> str:
    return _canonical_json_bytes(payload).decode("utf-8")


def _stable_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _stable_hash(payload: object) -> str:
    return f"sha256:{hashlib.sha256(_stable_json(payload).encode('utf-8')).hexdigest()}"


def _compiler_replay_snapshot() -> dict[str, str]:
    return {
        "model_version": os.getenv(_NEURO_MODEL_VERSION_ENV, "").strip(),
        "policy_snapshot_version": os.getenv(_NEURO_POLICY_SNAPSHOT_VERSION_ENV, "").strip(),
    }


def _compiler_replay_bundle(
    *,
    request_context: CompileRequestContext,
    workload_profile: str,
    source_precedence: str,
    source_digest: str,
    request_digest: str,
    aqo_digest: str,
    compiler_stage_order: list[str],
    handoff_stage_order: list[str],
    pass_pipeline: CompilerPassPipeline,
    symbolic_candidate_set: SymbolicCandidateSet,
    logical_graph_schema: dict[str, object],
    telemetry_feature_set: dict[str, object],
) -> tuple[dict[str, object], str]:
    snapshot = _compiler_replay_snapshot()
    symbolic_rules = []
    for record in pass_pipeline.records:
        symbolic_rules.append(
            {
                "name": record.name,
                "kind": record.kind,
                "rule": record.rule,
                "preconditions": list(record.preconditions),
                "postconditions": list(record.postconditions),
                "input_sha256": hashlib.sha256(_canonical_json_bytes(record.input)).hexdigest(),
                "output_sha256": hashlib.sha256(_canonical_json_bytes(record.output)).hexdigest(),
            }
        )
    symbolic_candidates = _symbolic_candidate_set_payload(symbolic_candidate_set)
    symbolic_candidates["candidate_ids"] = [candidate["candidate_id"] for candidate in symbolic_candidates["candidates"]]

    replay_bundle: dict[str, object] = {
        "contract_version": "1.0.0",
        "replay_mode": _REPLAY_MODE_DETERMINISTIC,
        "request": {
            "request_id": request_context.request_id,
            "trace_id": request_context.trace_id,
            "traceparent": request_context.traceparent,
            "deadline": request_context.deadline,
            "retry_policy": request_context.retry_policy,
            "sandbox_profile": request_context.sandbox_profile,
            "tenant_id": request_context.tenant_id,
            "project_id": request_context.project_id,
        },
        "source": {
            "sha256": source_digest,
            "precedence": source_precedence,
        },
        "request_digest": request_digest,
        "aqo_digest": aqo_digest,
        "workload_profile": workload_profile,
        "compiler_stage_order": compiler_stage_order,
        "handoff_stage_order": handoff_stage_order,
        "symbolic_rules": symbolic_rules,
        "model_snapshot": snapshot,
        "symbolic_candidate_set": symbolic_candidates,
        "logical_graph_schema": logical_graph_schema,
        "telemetry_feature_set": telemetry_feature_set,
        "model_recommendations": [],
    }
    replay_bundle_json = _canonical_json_text(replay_bundle)
    replay_bundle_sha256 = hashlib.sha256(replay_bundle_json.encode("utf-8")).hexdigest()
    return replay_bundle, replay_bundle_sha256


def _relabel_violations(
    violations: tuple[FieldViolation, ...],
    *,
    stage: str,
    rule: str,
    pass_name: str,
) -> tuple[FieldViolation, ...]:
    return tuple(
        FieldViolation(
            field=violation.field,
            description=violation.description,
            stage=violation.stage or stage,
            rule=violation.rule or rule,
            pass_name=violation.pass_name or pass_name,
        )
        for violation in violations
    )


def _sanitize_security_context(value: str) -> str:
    if not value:
        return ""
    sensitive_header_re = re.compile(
        r"(?i)\b(?:authorization|proxy-authorization|x-api-key|x-auth-token|x-access-token|cookie|set-cookie)\s*:\s*.+"
    )
    bearer_re = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}\b")
    redacted = sensitive_header_re.sub("[REDACTED]", value)
    redacted = bearer_re.sub("[REDACTED]", redacted)
    return redacted


def _literal_scalar(node: ast.AST) -> str | int | float | None:
    """Resolve a closed literal/arithmetical scalar expression.

    Eigen-Lang docs allow literals and limited arithmetic expressions in the
    statically analyzable subset. We keep the evaluator deliberately narrow:
    constants, unary +/- over numeric constants, and binary arithmetic over
    numeric constants only. Names, calls, attributes, subscripts, and other
    AST forms remain rejected.
    """

    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node.value, float) and isfinite(node.value):
            return float(node.value)
        return None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        operand = _literal_scalar(node.operand)
        if isinstance(operand, bool) or not isinstance(operand, (int, float)):
            return None
        value = operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(value, float) and not isfinite(value):
            return None
        return value

    if isinstance(node, ast.BinOp) and isinstance(
        node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
    ):
        left = _literal_scalar(node.left)
        right = _literal_scalar(node.right)
        if (
            isinstance(left, bool)
            or isinstance(right, bool)
            or not isinstance(left, (int, float))
            or not isinstance(right, (int, float))
        ):
            return None
        try:
            if isinstance(node.op, ast.Add):
                value = left + right
            elif isinstance(node.op, ast.Sub):
                value = left - right
            elif isinstance(node.op, ast.Mult):
                value = left * right
            elif isinstance(node.op, ast.Div):
                value = left / right
            elif isinstance(node.op, ast.FloorDiv):
                value = left // right
            elif isinstance(node.op, ast.Mod):
                value = left % right
            else:
                value = left**right
        except (OverflowError, ZeroDivisionError, ValueError, TypeError):
            return None
        if isinstance(value, float) and not isfinite(value):
            return None
        if isinstance(value, bool):
            return None
        return value
    return None


def _validate_parameters_object(parameters: object) -> tuple[FieldViolation, ...]:
    if parameters is None:
        return ()
    if not isinstance(parameters, dict):
        return (FieldViolation(field="parameters", description="parameters must be an object"),)
    violations: list[FieldViolation] = []
    for name, value in parameters.items():
        if not isinstance(name, str) or not name:
            violations.append(FieldViolation(field="parameters", description="parameter names must be strings"))
            continue
        if not isinstance(value, (int, float, str)) or (isinstance(value, float) and not isfinite(value)):
            violations.append(
                FieldViolation(
                    field=f"parameters.{name}",
                    description="parameter values must be integer, float, or string",
                )
            )
    return tuple(violations)


def _validate_optional_object(value: object, field: str) -> tuple[FieldViolation, ...]:
    if value is None:
        return ()
    if not isinstance(value, dict):
        return (FieldViolation(field=field, description=f"{field} must be an object"),)
    return ()


def _validate_aqo_payload(aqo: dict[str, object]) -> tuple[FieldViolation, ...]:
    violations: list[FieldViolation] = []

    unknown_fields = set(aqo) - _AQO_ALLOWED_TOP_LEVEL_FIELDS
    for field in sorted(unknown_fields):
        violations.append(FieldViolation(field=field, description="unknown AQO top-level field"))

    if aqo.get("version") != AQO_VERSION:
        violations.append(FieldViolation(field="version", description=f"aqo version must be {AQO_VERSION}"))

    qubits = aqo.get("qubits")
    if not isinstance(qubits, int) or qubits < 1:
        violations.append(FieldViolation(field="qubits", description="qubits must be a positive integer"))

    operations = aqo.get("operations")
    if not isinstance(operations, list) or not operations:
        violations.append(FieldViolation(field="operations", description="operations must be a non-empty array"))
        operations = []

    violations.extend(_validate_parameters_object(aqo.get("parameters")))
    violations.extend(_validate_optional_object(aqo.get("metadata"), "metadata"))
    violations.extend(_validate_optional_object(aqo.get("checksums"), "checksums"))
    violations.extend(_validate_optional_object(aqo.get("topology"), "topology"))
    violations.extend(_validate_optional_object(aqo.get("annotations"), "annotations"))

    for idx, op in enumerate(operations):
        if not isinstance(op, dict):
            violations.append(FieldViolation(field=f"operations[{idx}]", description="operation must be an object"))
            continue

        op_name = op.get("op")
        if op_name not in _AQO_ALLOWED_OPS:
            violations.append(FieldViolation(field=f"operations[{idx}].op", description="unsupported opcode"))
            continue

        q = op.get("q")
        if not isinstance(q, list) or not q or not all(isinstance(item, int) and item >= 0 for item in q):
            violations.append(FieldViolation(field=f"operations[{idx}].q", description="q must be a list of non-negative integers"))
            continue

        if any((qubits is not None and item >= qubits) for item in q):
            violations.append(FieldViolation(field=f"operations[{idx}].q", description="qubit index out of range"))

        expected_arity = _AQO_ARITY[op_name]
        if op_name == "MEASURE":
            c = op.get("c")
            if not isinstance(c, list) or len(c) != len(q) or not all(isinstance(item, int) and item >= 0 for item in c):
                violations.append(FieldViolation(field=f"operations[{idx}].c", description="MEASURE requires matching classical indices"))
            if any((qubits is not None and item >= qubits) for item in c or []):
                violations.append(FieldViolation(field=f"operations[{idx}].c", description="classical index out of range"))
            basis = op.get("basis")
            if basis is not None and basis not in _AQO_MEASUREMENT_BASIS:
                violations.append(FieldViolation(field=f"operations[{idx}].basis", description="unsupported measurement basis"))
            if "params" in op and op["params"]:
                violations.append(FieldViolation(field=f"operations[{idx}].params", description="MEASURE must not include params"))
            continue

        if len(q) != expected_arity:
            violations.append(FieldViolation(field=f"operations[{idx}].q", description=f"{op_name} has invalid arity"))

        params = op.get("params")
        if op_name in _AQO_ROTATION_OPS:
            if not isinstance(params, dict) or set(params) != {"theta"}:
                violations.append(FieldViolation(field=f"operations[{idx}].params", description=f"{op_name} requires theta parameter"))
            else:
                theta = params["theta"]
                if not isinstance(theta, (int, float, str)) or (isinstance(theta, float) and not isfinite(theta)):
                    violations.append(FieldViolation(field=f"operations[{idx}].params.theta", description="theta must be integer, float, or string"))
        else:
            if params:
                violations.append(FieldViolation(field=f"operations[{idx}].params", description=f"{op_name} must not include params"))

        if op_name in _AQO_NON_PARAMETERIZED_OPS and "c" in op and op["c"]:
            violations.append(FieldViolation(field=f"operations[{idx}].c", description=f"{op_name} must not include c"))

    return tuple(violations)


def _count_measurements(operations: list[dict]) -> int:
    return sum(1 for operation in operations if operation.get("op") == "MEASURE")


def _symbolic_candidate_features(
    *,
    candidate_kind: str,
    qubits: int,
    operations: list[dict],
    has_expectation: bool,
    has_minimize: bool,
    distributed: DistributedCompileConfig,
) -> dict[str, object]:
    return {
        "candidate_kind": candidate_kind,
        "qubits": qubits,
        "operation_count": len(operations),
        "measurement_count": _count_measurements(operations),
        "terminal_measurement_present": bool(operations and operations[-1].get("op") == "MEASURE"),
        "has_expectation": has_expectation,
        "has_minimize": has_minimize,
        "distributed_enabled": distributed.enabled,
        "distributed_target": distributed.target or "",
        "distributed_partition_count": distributed.partition_count or 0,
    }


def _symbolic_candidate_payload(candidate: SymbolicCandidate | str) -> dict[str, object]:
    if isinstance(candidate, str):
        return {
            "candidate_id": candidate,
            "features": {},
            "legal": False,
            "legality_reason": "candidate_reference",
        }
    return {
        "candidate_id": candidate.candidate_id,
        "features": candidate.features,
        "legal": candidate.legal,
        "legality_reason": candidate.legality_reason,
    }


def _symbolic_candidate_graph_encoding(candidate: SymbolicCandidate) -> dict[str, object]:
    features = candidate.features
    node_attributes = {
        "candidate_kind": str(features.get("candidate_kind", "")).strip(),
        "legal": bool(candidate.legal),
        "operation_count": int(features.get("operation_count", 0) or 0),
        "measurement_count": int(features.get("measurement_count", 0) or 0),
        "terminal_measurement_present": bool(features.get("terminal_measurement_present", False)),
        "has_expectation": bool(features.get("has_expectation", False)),
        "has_minimize": bool(features.get("has_minimize", False)),
        "distributed_enabled": bool(features.get("distributed_enabled", False)),
        "distributed_target": str(features.get("distributed_target", "")).strip(),
        "distributed_partition_count": int(features.get("distributed_partition_count", 0) or 0),
    }
    useful_signal = {
        "rewrite_ready": bool(node_attributes["legal"]) and node_attributes["operation_count"] > 0,
        "canonicalizable": node_attributes["terminal_measurement_present"]
        or node_attributes["candidate_kind"] == "terminal_measurement_normalized",
        "measurement_density": round(
            node_attributes["measurement_count"] / max(node_attributes["operation_count"], 1),
            6,
        ),
    }
    nodes = [
        {
            "id": "candidate",
            "kind": "rewrite_candidate",
            "label": candidate.candidate_id,
            "attributes": node_attributes,
        },
        {
            "id": "graph_features",
            "kind": "feature_bundle",
            "label": "graph_features",
            "attributes": useful_signal,
        },
        {
            "id": "rank_projection",
            "kind": "rank_projection",
            "label": "expected_usefulness",
            "attributes": {
                "model_family": _ADVISORY_MODEL_FAMILY,
                "model_version": _ADVISORY_MODEL_VERSION,
                "objective": "expected_usefulness",
            },
        },
    ]
    edges = [
        {
            "id": "candidate->graph_features",
            "source": "candidate",
            "target": "graph_features",
            "kind": "describes",
            "label": "describes",
            "attributes": {"role": "input_graph"},
        },
        {
            "id": "graph_features->rank_projection",
            "source": "graph_features",
            "target": "rank_projection",
            "kind": "feeds",
            "label": "feeds",
            "attributes": {"role": "rank_input"},
        },
    ]
    return {
        "schema_version": "logical-compiler-graph-v1",
        "canonical_format": "eigen.logical-graph-json",
        "graph_kind": "rewrite_candidate",
        "nodes": nodes,
        "edges": edges,
    }


def _symbolic_candidate_priority(candidate: SymbolicCandidate) -> tuple[int, int, str]:
    features = candidate.features
    candidate_kind = str(features.get("candidate_kind", "")).strip()
    kind_priority = 0 if candidate_kind == "terminal_measurement_normalized" else 1
    legality_priority = 0 if candidate.legal else 1
    return (kind_priority, legality_priority, candidate.candidate_id)


def _symbolic_candidate_confidence(candidate: SymbolicCandidate, *, rank: int) -> float:
    features = candidate.features
    graph = _symbolic_candidate_graph_encoding(candidate)
    candidate_kind = str(features.get("candidate_kind", "")).strip()
    graph_size_bonus = min((len(graph["nodes"]) + len(graph["edges"])) * 0.01, 0.05)
    confidence = 0.92 + graph_size_bonus
    if candidate_kind == "terminal_measurement_normalized":
        confidence += 0.03
    if not candidate.legal:
        confidence -= 0.12
    confidence -= min(max(rank - 1, 0) * 0.01, 0.05)
    return round(max(0.5, min(confidence, 0.99)), 6)


def _symbolic_candidate_explanation(
    candidate: SymbolicCandidate,
    *,
    rank: int,
    confidence: float,
) -> dict[str, object]:
    graph = _symbolic_candidate_graph_encoding(candidate)
    features = candidate.features
    candidate_kind = str(features.get("candidate_kind", "")).strip()
    operation_count = int(features.get("operation_count", 0) or 0)
    measurement_count = int(features.get("measurement_count", 0) or 0)
    terminal_measurement_present = bool(features.get("terminal_measurement_present", False))
    has_expectation = bool(features.get("has_expectation", False))
    has_minimize = bool(features.get("has_minimize", False))
    distributed_enabled = bool(features.get("distributed_enabled", False))
    graph_size_bonus = round(min((len(graph["nodes"]) + len(graph["edges"])) * 0.01, 0.05), 6)

    influential_features: list[dict[str, object]] = []
    if candidate_kind == "terminal_measurement_normalized":
        influential_features.append(
            {
                "name": "candidate_kind",
                "value": candidate_kind,
                "contribution": 0.40,
                "reason": "the rewrite normalizes terminal measurement structure",
            }
        )
        if not terminal_measurement_present:
            influential_features.append(
                {
                    "name": "terminal_measurement_present",
                    "value": terminal_measurement_present,
                    "contribution": 0.22,
                    "reason": "the candidate repairs a missing terminal measurement anchor",
                }
            )
    else:
        influential_features.append(
            {
                "name": "candidate_kind",
                "value": candidate_kind,
                "contribution": 0.30,
                "reason": "the candidate remains a legal rewrite option with deterministic ordering",
            }
        )
        if terminal_measurement_present:
            influential_features.append(
                {
                    "name": "terminal_measurement_present",
                    "value": terminal_measurement_present,
                    "contribution": 0.12,
                    "reason": "the candidate preserves an existing terminal measurement anchor",
                }
            )

    influential_features.append(
        {
            "name": "measurement_count",
            "value": measurement_count,
            "contribution": round(min(measurement_count * 0.03, 0.15), 6),
            "reason": "measurement activity contributes to bounded candidate context",
        }
    )
    influential_features.append(
        {
            "name": "operation_count",
            "value": operation_count,
            "contribution": round(min(operation_count * 0.01, 0.08), 6),
            "reason": "larger candidates receive a bounded size-based advisory weight",
        }
    )
    if has_expectation:
        influential_features.append(
            {
                "name": "has_expectation",
                "value": has_expectation,
                "contribution": 0.04,
                "reason": "expectation-aware rewrites remain visible in the advisory envelope",
            }
        )
    if has_minimize:
        influential_features.append(
            {
                "name": "has_minimize",
                "value": has_minimize,
                "contribution": 0.04,
                "reason": "minimize-aware rewrites remain visible in the advisory envelope",
            }
        )
    if distributed_enabled:
        influential_features.append(
            {
                "name": "distributed_enabled",
                "value": distributed_enabled,
                "contribution": 0.03,
                "reason": "distributed routing support contributes bounded advisory context",
            }
        )

    focus_subgraph = {
        "schema_version": graph["schema_version"],
        "canonical_format": graph["canonical_format"],
        "graph_kind": graph["graph_kind"],
        "node_ids": [node["id"] for node in graph["nodes"]],
        "node_labels": [node["label"] for node in graph["nodes"]],
        "edge_ids": [edge["id"] for edge in graph["edges"]],
    }

    if candidate_kind == "terminal_measurement_normalized":
        summary_clause = "it normalizes the terminal measurement shape"
    elif terminal_measurement_present:
        summary_clause = "it preserves an existing terminal measurement anchor"
    else:
        summary_clause = "it remains a legal rewrite candidate with a compact graph signature"

    summary = (
        f"Preferred because {summary_clause}; it is rank {rank} in deterministic advisory order "
        f"with confidence {confidence:.6f}; it carries {measurement_count} measurement operation(s) "
        f"across {operation_count} total operation(s); the focus subgraph covers nodes "
        f"{', '.join(focus_subgraph['node_ids'])}."
    )

    return {
        "summary": summary,
        "why_preferred": summary,
        "influential_features": influential_features,
        "influential_subgraph": focus_subgraph,
        "score_breakdown": {
            "advisory_rank": rank,
            "confidence": confidence,
            "graph_size_bonus": graph_size_bonus,
        },
    }


def _baseline_symbolic_candidate(candidates: list[SymbolicCandidate | str]) -> SymbolicCandidate | None:
    legal_candidates = [candidate for candidate in candidates if isinstance(candidate, SymbolicCandidate) and candidate.legal]
    if not legal_candidates:
        return None
    for candidate in legal_candidates:
        if candidate.candidate_id == "symbolic.keep_lowered_ir":
            return candidate
    return legal_candidates[0]


def _symbolic_candidate_set_payload(candidate_set: SymbolicCandidateSet) -> dict[str, object]:
    candidates = [_symbolic_candidate_payload(candidate) for candidate in candidate_set.candidates]
    legal_candidates = [candidate for candidate in candidate_set.candidates if isinstance(candidate, SymbolicCandidate) and candidate.legal]
    ranked_candidates = []
    ordered_candidates = sorted(legal_candidates, key=_symbolic_candidate_priority)
    for index, candidate in enumerate(ordered_candidates, start=1):
        expected_usefulness_score = round(1.0 - min((index - 1) * 0.01, 0.05), 6)
        confidence = _symbolic_candidate_confidence(candidate, rank=index)
        explanation = _symbolic_candidate_explanation(candidate, rank=index, confidence=confidence)
        ranked_candidates.append(
            {
                **_symbolic_candidate_payload(candidate),
                "rank": index,
                "expected_usefulness_score": expected_usefulness_score,
                "confidence": confidence,
                "graph_encoding": _symbolic_candidate_graph_encoding(candidate),
                "explanation": explanation,
                "why_preferred": explanation["why_preferred"],
            }
        )
    for index, item in enumerate(ranked_candidates, start=1):
        item["rank"] = index
    
    baseline_candidate = _baseline_symbolic_candidate(list(candidate_set.candidates))
    selected_candidate = ranked_candidates[0] if ranked_candidates else None
    fallback_used = False
    fallback_reason = ""
    selection_mode = _ADVISORY_SELECTION_MODE

    if not ranked_candidates:
        fallback_used = True
        fallback_reason = _ADVISORY_FALLBACK_REASON_NO_LEGAL_CANDIDATES
        selection_mode = "symbolic_baseline"
        if baseline_candidate is not None:
            baseline_explanation = _symbolic_candidate_explanation(
                baseline_candidate,
                rank=1,
                confidence=_symbolic_candidate_confidence(baseline_candidate, rank=1),
            )
            selected_candidate = {
                **_symbolic_candidate_payload(baseline_candidate),
                "rank": 1,
                "expected_usefulness_score": 0.0,
                "confidence": _symbolic_candidate_confidence(baseline_candidate, rank=1),
                "graph_encoding": _symbolic_candidate_graph_encoding(baseline_candidate),
                "explanation": baseline_explanation,
                "why_preferred": baseline_explanation["why_preferred"],
            }

    selected_candidate_id = str(selected_candidate["candidate_id"]) if selected_candidate else ""
    selected_candidate_explanation = str(selected_candidate["why_preferred"]) if selected_candidate else ""

    return {
        "version": candidate_set.version,
        "candidate_budget": candidate_set.candidate_budget,
        "candidate_count": len(candidates),
        "legal_candidate_count": len(legal_candidates),
        "ranker": {
            "model_family": _ADVISORY_MODEL_FAMILY,
            "model_version": _ADVISORY_MODEL_VERSION,
            "objective": "stable_legal_candidate_order",
            "explanation_hook": "feature_attribution",
            "selection_mode": selection_mode,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
        },
        "selected_candidate_id": selected_candidate_id,
        "selected_candidate_explanation": selected_candidate_explanation,
        "candidate_ids": [str(candidate["candidate_id"]) for candidate in candidates],
        "candidates": candidates,
        "ranked_candidates": ranked_candidates,
    }


def _logical_graph_schema_payload() -> dict[str, object]:
    """Return the canonical logical graph schema shared by training and inference.

    The schema intentionally stays bounded and declarative: it specifies the
    required node/edge fields, the allowed label taxonomies, and the
    deterministic ordering rules used when logical compiler structures are
    serialized for downstream consumers.
    """

    return {
        "contract_version": "1.0.0",
        "schema_version": "logical-compiler-graph-v1",
        "canonical_format": "eigen.logical-graph-json",
        "shared_between_training_and_inference": True,
        "graph_kinds": ["ast", "ir", "dpda_state"],
        "nodes": {
            "required_fields": ["id", "kind", "label", "attributes"],
            "optional_fields": ["metadata"],
            "attribute_contract": {
                "type": "bounded_json_object",
                "value_types": ["string", "integer", "number", "boolean", "array", "object"],
                "ordering": "deterministic",
                "unknown_fields": "allowed_but_bounded",
            },
        },
        "edges": {
            "required_fields": ["id", "source", "target", "kind", "label", "attributes"],
            "optional_fields": ["metadata"],
            "attribute_contract": {
                "type": "bounded_json_object",
                "value_types": ["string", "integer", "number", "boolean", "array", "object"],
                "ordering": "deterministic",
                "unknown_fields": "allowed_but_bounded",
            },
        },
        "labels": {
            "ast": [
                "module",
                "function",
                "async_function",
                "decorator",
                "call",
                "name",
                "constant",
                "assign",
                "argument",
                "keyword",
            ],
            "ir": [
                "program",
                "operation",
                "parameter",
                "observable",
                "measurement",
                "rewrite_candidate",
                "validation_gate",
            ],
            "dpda_state": [
                "parse",
                "normalize",
                "candidate_generation",
                "legality_check",
                "rewrite",
                "emit_aqo",
                "accept",
                "reject",
            ],
        },
        "edge_kinds": {
            "ast": ["child", "decorator_of", "argument_of", "keyword_of", "binding"],
            "ir": ["sequence", "dataflow", "control", "rewrite", "validation"],
            "dpda_state": ["transition", "accept", "reject", "fallback"],
        },
        "ordering": {
            "nodes": ["id"],
            "edges": ["id"],
            "labels": ["graph_kind", "kind", "label"],
        },
        "provenance": {
            "source": "eigen-compiler",
            "replay_safe": True,
            "training_safe": True,
            "inference_safe": True,
        },
    }


def _graph_summary_from_encoding(graph_encoding: dict[str, object] | None) -> dict[str, object]:
    graph = dict(graph_encoding or {})
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(edges, list):
        edges = []

    outgoing_counts: dict[str, int] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = str(edge.get("source", "")).strip()
        if not source:
            continue
        outgoing_counts[source] = outgoing_counts.get(source, 0) + 1

    graph_size_nodes = len(nodes)
    graph_size_edges = len(edges)
    graph_fanout_max = max(outgoing_counts.values(), default=0)
    graph_fanout_mean = round(graph_size_edges / max(graph_size_nodes, 1), 6)

    return {
        "graph_kind": str(graph.get("graph_kind", "rewrite_candidate")).strip() or "rewrite_candidate",
        "graph_size_nodes": graph_size_nodes,
        "graph_size_edges": graph_size_edges,
        "graph_size_total": graph_size_nodes + graph_size_edges,
        "graph_fanout_max": graph_fanout_max,
        "graph_fanout_mean": graph_fanout_mean,
    }


def _telemetry_feature_set_payload(
    *,
    graph_encoding: dict[str, object] | None,
    compiler_telemetry: dict[str, object] | None,
    kb_telemetry: dict[str, object] | None,
    source: str,
) -> dict[str, object]:
    graph_summary = _graph_summary_from_encoding(graph_encoding)
    compiler_telemetry = dict(compiler_telemetry or {})
    kb_telemetry = dict(kb_telemetry or {})

    stage_count = max(int(compiler_telemetry.get("stage_count", 0) or 0), 0)
    stage_success_count = max(int(compiler_telemetry.get("stage_success_count", stage_count) or stage_count), 0)
    stage_failure_count = max(int(compiler_telemetry.get("stage_failure_count", 0) or 0), 0)
    if stage_count <= 0:
        stage_count = stage_success_count + stage_failure_count
    stage_success_rate = round(
        stage_success_count / max(stage_success_count + stage_failure_count, 1),
        6,
    )
    latency_ms = float(max(int(float(compiler_telemetry.get("latency_ms", 0.0) or 0.0)), 0))
    backend = str(compiler_telemetry.get("backend", "")).strip()
    policy_state = str(compiler_telemetry.get("policy_state", "")).strip()

    past_success_count = max(int(kb_telemetry.get("past_success_count", 0) or 0), 0)
    past_failure_count = max(int(kb_telemetry.get("past_failure_count", 0) or 0), 0)
    past_success_rate = kb_telemetry.get("past_success_rate")
    if past_success_rate in (None, ""):
        past_success_rate = round(
            past_success_count / max(past_success_count + past_failure_count, 1),
            6,
        )
    else:
        past_success_rate = round(float(past_success_rate), 6)

    feature_values = {
        "graph_size_nodes": graph_summary["graph_size_nodes"],
        "graph_size_edges": graph_summary["graph_size_edges"],
        "graph_size_total": graph_summary["graph_size_total"],
        "graph_fanout_max": graph_summary["graph_fanout_max"],
        "graph_fanout_mean": graph_summary["graph_fanout_mean"],
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
    feature_digest_sha256 = _stable_hash(feature_values)

    return {
        "schema_version": _TABULAR_FEATURE_SCHEMA_VERSION,
        "source": source,
        "offline_online_parity": True,
        "feature_order": list(_TABULAR_FEATURE_ORDER),
        "feature_count": len(feature_values),
        "feature_values": feature_values,
        "feature_digest_sha256": feature_digest_sha256,
        "graph": graph_summary,
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
    }


def enumerate_symbolic_candidates(
    *,
    qubits: int,
    operations: list[dict],
    params: dict[str, dict[str, object]],
    source_digest: str,
    request_digest: str,
    has_expectation: bool,
    has_minimize: bool,
    observable_bindings: dict[str, dict[str, object]],
    expectation_annotation: dict[str, object] | None,
    distributed: DistributedCompileConfig,
) -> SymbolicCandidateSet:
    """Enumerate the bounded symbolic candidate set used for ranking."""

    lowered_ir = json.loads(json.dumps(operations, sort_keys=True, separators=(",", ":"), allow_nan=False))
    rewritten_operations = _rewrite_terminal_measurement(lowered_ir, qubits)
    candidate_variants = (
        ("symbolic.keep_lowered_ir", "keep_lowered_ir", lowered_ir),
        ("symbolic.rewrite_terminal_measurement", "terminal_measurement_normalized", rewritten_operations),
    )
    candidates: list[SymbolicCandidate] = []
    for candidate_id, candidate_kind, candidate_operations in candidate_variants:
        aqo_payload = _build_aqo_payload(
            qubits=qubits,
            operations=candidate_operations,
            params=params,
            source_digest=source_digest,
            source_ref=None,
            request_digest=request_digest,
            has_expectation=has_expectation,
            has_minimize=has_minimize,
            observable_bindings=observable_bindings,
            expectation_annotation=expectation_annotation,
            distributed=distributed,
        )
        try:
            _validate_lowering_payload(aqo_payload)
            legal = True
            legality_reason = "aqo_contract_valid"
        except CompilerValidationError as exc:
            legal = False
            legality_reason = ",".join(sorted({violation.field for violation in exc.violations})) or "aqo_contract_invalid"
        candidates.append(
            SymbolicCandidate(
                candidate_id=candidate_id,
                features=_symbolic_candidate_features(
                    candidate_kind=candidate_kind,
                    qubits=qubits,
                    operations=candidate_operations,
                    has_expectation=has_expectation,
                    has_minimize=has_minimize,
                    distributed=distributed,
                ),
                legal=legal,
                legality_reason=legality_reason,
            )
        )

    return SymbolicCandidateSet(
        version=_SYMBOLIC_CANDIDATE_ENUMERATION_VERSION,
        candidate_budget=_SYMBOLIC_CANDIDATE_BUDGET,
        candidates=tuple(candidates[:_SYMBOLIC_CANDIDATE_BUDGET]),
    )


def _encode_aqo_payload(aqo: dict[str, object]) -> bytes:
    violations = _validate_aqo_payload(aqo)
    if violations:
        raise CompilerValidationError(violations=violations)
    aqo_bytes = _canonical_json_bytes(aqo)
    if json.loads(aqo_bytes.decode("utf-8")) != aqo:
        raise CompilerValidationError(
            violations=(FieldViolation(field="operations", description="AQO canonical round-trip failed"),)
        )
    return aqo_bytes


def _normalize_options(options: dict[str, str] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in sorted((options or {}).items()):
        normalized[str(key)] = str(value)
    return normalized


def _normalize_request_context(request_context: dict[str, str] | None) -> CompileRequestContext:
    context = request_context or {}
    sandbox_profile = str(context.get("sandbox_profile", "")).strip().lower() or "strict"
    if sandbox_profile not in _ALLOWED_SANDBOX_PROFILES:
        raise CompilerValidationError(
            violations=(
                FieldViolation(
                    field="request_context.sandbox_profile",
                    description=f"sandbox profile must be one of {', '.join(sorted(_ALLOWED_SANDBOX_PROFILES))}",
                ),
            )
        )
    return CompileRequestContext(
        request_id=str(context.get("request_id", "")),
        trace_id=str(context.get("trace_id", "")),
        traceparent=str(context.get("traceparent", "")),
        deadline=str(context.get("deadline", "")),
        retry_policy=str(context.get("retry_policy", "")),
        security_context=_sanitize_security_context(str(context.get("security_context", ""))),
        sandbox_profile=sandbox_profile,
        tenant_id=str(context.get("tenant_id", "")),
        project_id=str(context.get("project_id", "")),
    )


def _resolve_source_bytes(source: bytes, source_ref: str | None) -> tuple[bytes, str]:
    if source:
        return source, "source"
    if not source_ref:
        raise CompilerValidationError(
            violations=(FieldViolation(field="source", description="source or source_ref is required"),)
        )

    normalized_ref = source_ref
    for prefix in ("qfs://", "circuitfs://"):
        if normalized_ref.startswith(prefix):
            normalized_ref = normalized_ref[len(prefix) :]
            break

    qfs_root = Path(os.getenv("EIGEN_QFS_ROOT", "/var/lib/eigen/circuit_fs")).resolve()
    ref_path = (qfs_root / normalized_ref.lstrip("/")).resolve()
    if qfs_root != ref_path and qfs_root not in ref_path.parents:
        raise CompilerValidationError(
            violations=(FieldViolation(field="source_ref", description="source_ref escapes QFS root"),)
        )
    try:
        return ref_path.read_bytes(), "source_ref"
    except FileNotFoundError:
        raise CompilerValidationError(
            violations=(FieldViolation(field="source_ref", description=f"source_ref not found: {source_ref}"),)
        )


def _compiler_limit(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, value)


def _parse_python_source(source: bytes) -> ast.AST:
    try:
        return ast.parse(source.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError):
        raise CompilerValidationError(
            violations=(FieldViolation(field="source", description="source must be valid UTF-8 Python syntax"),)
        )


def _reject_dynamic_control_flow(tree: ast.AST) -> tuple[FieldViolation, ...]:
    banned_nodes = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Match, ast.IfExp)
    if any(isinstance(node, banned_nodes) for node in ast.walk(tree)):
        return (
            FieldViolation(
                field="source",
                description="dynamic runtime control flow is not supported in Eigen-Lang",
            ),
        )
    return ()


def _reject_forbidden_imports(tree: ast.AST) -> tuple[FieldViolation, ...]:
    violations: list[FieldViolation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_root = alias.name.split(".", 1)[0]
                if module_root in _FORBIDDEN_MODULE_ROOTS or module_root not in _ALLOWED_IMPORT_PREFIXES:
                    violations.append(
                        FieldViolation(
                            field="source",
                            description=f"import '{alias.name}' is not allowed in Eigen-Lang",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            module_root = module.split(".", 1)[0]
            if module_root in _FORBIDDEN_MODULE_ROOTS or module_root not in _ALLOWED_IMPORT_PREFIXES:
                violations.append(
                    FieldViolation(
                        field="source",
                        description=f"import from '{module}' is not allowed in Eigen-Lang",
                    )
                )
    return tuple(violations)


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _reject_forbidden_calls(tree: ast.AST) -> tuple[FieldViolation, ...]:
    violations: list[FieldViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name in _FORBIDDEN_CALLS:
            violations.append(
                FieldViolation(
                    field="source",
                    description=f"call '{name}' is not allowed in Eigen-Lang",
                )
            )
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            module_root = node.func.value.id
            if module_root in _FORBIDDEN_MODULE_ROOTS:
                violations.append(
                    FieldViolation(
                        field="source",
                        description=f"dynamic I/O call '{module_root}.{name}' is not allowed in Eigen-Lang",
                    )
                )
    return tuple(violations)


def _enforce_resource_limits(tree: ast.AST) -> tuple[FieldViolation, ...]:
    max_ast_nodes = _compiler_limit("EIGEN_COMPILER_MAX_AST_NODES", 50_000)
    max_nesting_depth = _compiler_limit("EIGEN_COMPILER_MAX_AST_DEPTH", 200)

    node_count = 0
    max_depth_seen = 0
    stack: list[tuple[ast.AST, int]] = [(tree, 1)]
    while stack:
        node, depth = stack.pop()
        node_count += 1
        if node_count > max_ast_nodes:
            return (
                FieldViolation(field="source", description=f"AST node limit exceeded ({max_ast_nodes})"),
            )
        max_depth_seen = max(max_depth_seen, depth)
        if max_depth_seen > max_nesting_depth:
            return (
                FieldViolation(field="source", description=f"AST depth limit exceeded ({max_nesting_depth})"),
            )
        for child in ast.iter_child_nodes(node):
            stack.append((child, depth + 1))
    return ()


def _decorator_name(decorator: ast.AST) -> str | None:
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Call):
        return _call_name(decorator.func)
    return None


def _validate_single_entrypoint(tree: ast.AST) -> tuple[FieldViolation, ...]:
    entrypoints = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(_decorator_name(decorator) == "hybrid_program" for decorator in node.decorator_list)
    ]
    if len(entrypoints) == 1:
        return ()
    if len(entrypoints) == 0:
        return (FieldViolation(field="source", description="exactly one @hybrid_program entrypoint is required"),)
    return (
        FieldViolation(
            field="source",
            description=f"exactly one @hybrid_program entrypoint is required, found {len(entrypoints)}",
        ),
    )


def _collect_params(tree: ast.AST) -> tuple[dict[str, dict[str, object]], tuple[FieldViolation, ...]]:
    params: dict[str, dict[str, object]] = {}
    violations: list[FieldViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        target = node.targets[0].id
        if not isinstance(node.value, ast.Call) or _call_name(node.value.func) != "Param":
            continue
        if not node.value.args:
            continue
        name_arg = node.value.args[0]
        if isinstance(name_arg, ast.Constant) and isinstance(name_arg.value, str):
            default_value: str | int | float = name_arg.value
            if len(node.value.args) > 1:
                explicit_default = _literal_scalar(node.value.args[1])
                if explicit_default is None:
                    violations.append(
                        FieldViolation(
                            field="source",
                            description="Param default must be a literal integer, float, or string",
                        )
                    )
                    continue
                default_value = explicit_default
            params[target] = {"name": name_arg.value, "default": default_value}
    return params, tuple(violations)


def _literal_jsonish(node: ast.AST) -> object | None:
    scalar = _literal_scalar(node)
    if scalar is not None:
        return scalar
    if isinstance(node, ast.List):
        values = []
        for item in node.elts:
            value = _literal_jsonish(item)
            if value is None:
                return None
            values.append(value)
        return values
    if isinstance(node, ast.Tuple):
        values = []
        for item in node.elts:
            value = _literal_jsonish(item)
            if value is None:
                return None
            values.append(value)
        return values
    if isinstance(node, ast.Dict):
        result: dict[str, object] = {}
        for key_node, value_node in zip(node.keys, node.values, strict=True):
            key_value = _literal_jsonish(key_node)
            if not isinstance(key_value, str):
                return None
            value = _literal_jsonish(value_node)
            if value is None:
                return None
            result[key_value] = value
        return result
    return None


def _resolve_observable_terms(node: ast.AST) -> dict[str, object] | None:
    if not isinstance(node, ast.Call) or _call_name(node.func) != "Observable":
        return None
    terms: dict[str, object] = {}
    for keyword in node.keywords:
        if keyword.arg is None:
            return None
        value = _literal_jsonish(keyword.value)
        if value is None:
            return None
        terms[keyword.arg] = value
    return terms or None


def _collect_observable_bindings(tree: ast.AST) -> tuple[dict[str, dict[str, object]], tuple[FieldViolation, ...]]:
    bindings: dict[str, dict[str, object]] = {}
    violations: list[FieldViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        target = node.targets[0].id
        terms = _resolve_observable_terms(node.value)
        if terms is None:
            continue
        bindings[target] = terms
    return bindings, tuple(violations)


def _collect_expectation_annotation(
    tree: ast.AST,
    observable_bindings: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node.func) != "ExpectationValue":
            continue
        observable_expr = next((keyword.value for keyword in node.keywords if keyword.arg == "observable"), None)
        if observable_expr is None:
            continue
        if isinstance(observable_expr, ast.Name) and observable_expr.id in observable_bindings:
            return {
                "kind": "ExpectationValue",
                "observable_name": observable_expr.id,
            }
        terms = _resolve_observable_terms(observable_expr)
        if terms is not None:
            return {
                "kind": "ExpectationValue",
                "observable_terms": terms,
            }
    return None


def _resolve_int_expr(expr: ast.AST, *, context: str) -> int:
    value = _literal_scalar(expr)
    if isinstance(value, int):
        return value
    raise CompilerValidationError(
        violations=(FieldViolation(field="source", description=f"{context} must be a literal integer"),)
    )


def _resolve_theta_expr(expr: ast.AST, params: dict[str, dict[str, object]]) -> int | float | str:
    if isinstance(expr, ast.Name) and expr.id in params:
        return params[expr.id]["name"]  # symbolic parameter name
    scalar = _literal_scalar(expr)
    if isinstance(scalar, (int, float, str)):
        return scalar
    raise CompilerValidationError(
        violations=(FieldViolation(field="source", description="theta must be a literal or Param reference"),)
    )


def _extract_qubits_from_args(args: list[ast.AST], *, arity: int, name: str) -> list[int]:
    if len(args) != arity:
        raise CompilerValidationError(
            violations=(FieldViolation(field="source", description=f"{name} expects {arity} qubit argument(s)"),)
        )
    return [_resolve_int_expr(arg, context=f"{name} qubit index") for arg in args]


def _collect_operations(tree: ast.AST, params: dict[str, dict[str, object]]) -> tuple[list[dict], int]:
    operations: list[dict] = []
    qubit_count = 1

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = _call_name(node.func)
        if name is None:
            continue

        lowered: dict[str, object] | None = None
        positional_qubits = [arg for arg in node.args]
        if name in {"rx", "ry", "rz"}:
            q = _extract_qubits_from_args(positional_qubits[:1], arity=1, name=name.upper())
            theta_expr = next((kw.value for kw in node.keywords if kw.arg == "theta"), None)
            if theta_expr is None and len(node.args) >= 2:
                theta_expr = node.args[1]
            if theta_expr is None:
                raise CompilerValidationError(
                    violations=(FieldViolation(field="source", description=f"{name.upper()} requires theta"),)
                )
            lowered = {"op": name.upper(), "q": q, "params": {"theta": _resolve_theta_expr(theta_expr, params)}}
        elif name in {"x", "y", "z", "h", "s", "t", "reset"}:
            q = _extract_qubits_from_args(positional_qubits[:1], arity=1, name=name.upper())
            lowered = {"op": name.upper(), "q": q}
        elif name in {"cx", "cnot", "cz", "swap"}:
            q = _extract_qubits_from_args(positional_qubits[:2], arity=2, name=("CX" if name == "cnot" else name.upper()))
            lowered = {"op": "CX" if name == "cnot" else name.upper(), "q": q}
        elif name in {"ccx", "ccz"}:
            q = _extract_qubits_from_args(positional_qubits[:3], arity=3, name=name.upper())
            lowered = {"op": name.upper(), "q": q}
        elif name == "measure":
            q = [_resolve_int_expr(arg, context="MEASURE qubit index") for arg in positional_qubits]
            if not q:
                raise CompilerValidationError(
                    violations=(FieldViolation(field="source", description="MEASURE requires at least one qubit"),)
                )
            c_args = [kw.value for kw in node.keywords if kw.arg == "c"]
            if c_args:
                c_expr = c_args[0]
                if not isinstance(c_expr, (ast.List, ast.Tuple)):
                    raise CompilerValidationError(
                        violations=(FieldViolation(field="source", description="MEASURE c must be a literal list"),)
                    )
                c = [_resolve_int_expr(item, context="MEASURE classical index") for item in c_expr.elts]
            else:
                c = list(range(len(q)))
            basis_args = [kw.value for kw in node.keywords if kw.arg == "basis"]
            basis = None
            if basis_args:
                basis = _literal_scalar(basis_args[0])
                if basis not in _AQO_MEASUREMENT_BASIS:
                    raise CompilerValidationError(
                        violations=(FieldViolation(field="source", description="unsupported measurement basis"),)
                    )
            lowered = {"op": "MEASURE", "q": q, "c": c}
            if basis is not None:
                lowered["basis"] = basis
        elif name == "measure_all":
            q = list(range(qubit_count))
            lowered = {"op": "MEASURE", "q": q, "c": list(range(qubit_count))}
        else:
            continue

        if lowered["q"]:
            qubit_count = max(qubit_count, max(lowered["q"]) + 1)
        if lowered.get("c"):
            qubit_count = max(qubit_count, max(lowered["c"]) + 1)
        operations.append(lowered)

    return operations, qubit_count


def _distributed_compile_config(options: dict[str, str] | None) -> DistributedCompileConfig:
    opts = _normalize_options(options)
    enabled = opts.get("distributed.enabled", "false").lower() == "true"
    target = opts.get("distributed.target") or None

    partition_count: int | None = None
    if "distributed.partition_count" in opts:
        raw = opts["distributed.partition_count"]
        try:
            partition_count = int(raw)
        except ValueError:
            raise CompilerValidationError(
                violations=(
                    FieldViolation(
                        field="options.distributed.partition_count",
                        description="distributed.partition_count must be an integer",
                    ),
                )
            )
        if partition_count < 1:
            raise CompilerValidationError(
                violations=(
                    FieldViolation(
                        field="options.distributed.partition_count",
                        description="distributed.partition_count must be greater than zero",
                    ),
                )
            )

    queue_provider = opts.get("distributed.queue_provider") or None
    topology_hint = opts.get("distributed.topology_hint") or None
    return DistributedCompileConfig(
        enabled=enabled,
        target=target,
        partition_count=partition_count,
        queue_provider=queue_provider,
        topology_hint=topology_hint,
    )


def _rewrite_terminal_measurement(operations: list[dict], qubits: int) -> list[dict]:
    rewritten = json.loads(json.dumps(operations, sort_keys=True, separators=(",", ":"), allow_nan=False))
    if not rewritten or rewritten[-1].get("op") != "MEASURE":
        rewritten.append({"op": "MEASURE", "q": list(range(qubits)), "c": list(range(qubits))})
    return rewritten


def _validate_lowering_payload(aqo: dict[str, object]) -> dict[str, object]:
    violations = _validate_aqo_payload(aqo)
    if violations:
        raise CompilerValidationError(violations=violations)
    return aqo


def _build_compiler_pass_pipeline(
    *,
    qubits: int,
    operations: list[dict],
    params: dict[str, dict[str, object]],
    source_digest: str,
    source_precedence: str,
    request_digest: str,
    has_expectation: bool,
    has_minimize: bool,
    observable_bindings: dict[str, dict[str, object]],
    expectation_annotation: dict[str, object] | None,
    distributed: DistributedCompileConfig,
) -> CompilerPassPipeline:
    lowered_ir = {"qubits": qubits, "operations": json.loads(json.dumps(operations, sort_keys=True, separators=(",", ":"), allow_nan=False))}
    rewritten_operations = _rewrite_terminal_measurement(lowered_ir["operations"], qubits)
    rewritten_ir = {"qubits": qubits, "operations": rewritten_operations}

    aqo_payload = _build_aqo_payload(
        qubits=qubits,
        operations=rewritten_operations,
        params=params,
        source_digest=source_digest,
        source_ref=None,
        request_digest=request_digest,
        has_expectation=has_expectation,
        has_minimize=has_minimize,
        observable_bindings=observable_bindings,
        expectation_annotation=expectation_annotation,
        distributed=distributed,
    )
    validated_aqo = _validate_lowering_payload(aqo_payload)

    records = (
        CompilerPassRecord(
            name="lower_to_ir",
            kind="lowering",
            rule="compiler.source.lower_to_ir",
            preconditions=("ast_validated", "single_entrypoint_validated"),
            postconditions=("ir_extracted",),
            input={"source_sha256": source_digest, "source_precedence": source_precedence},
            output=lowered_ir,
        ),
        CompilerPassRecord(
            name="rewrite_ir",
            kind="rewrite",
            rule="compiler.rewrite.terminal_measurement",
            preconditions=("ir_extracted",),
            postconditions=("terminal_measurement_normalized",),
            input=lowered_ir,
            output=rewritten_ir,
        ),
        CompilerPassRecord(
            name="validate_lowering",
            kind="validation",
            rule="compiler.aqo.validate",
            preconditions=("ir_rewritten",),
            postconditions=("aqo_contract_valid",),
            input=rewritten_ir,
            output={"status": "valid", "aqo_version": AQO_VERSION},
        ),
        CompilerPassRecord(
            name="canonicalize_aqo",
            kind="lowering",
            rule="compiler.aqo.canonicalize",
            preconditions=("aqo_contract_valid",),
            postconditions=("canonical_json_ready",),
            input=validated_aqo,
            output={"operation_count": len(rewritten_operations), "qubit_count": qubits},
        ),
    )
    return CompilerPassPipeline(records=records, aqo=validated_aqo)


def _build_aqo_payload(
    *,
    qubits: int,
    operations: list[dict],
    params: dict[str, dict[str, object]],
    source_digest: str,
    source_ref: str | None,
    request_digest: str,
    has_expectation: bool,
    has_minimize: bool,
    observable_bindings: dict[str, dict[str, object]],
    expectation_annotation: dict[str, object] | None,
    distributed: DistributedCompileConfig,
) -> dict[str, object]:
    aqo: dict[str, object] = {
        "version": AQO_VERSION,
        "qubits": qubits,
        "operations": operations,
    }

    if params:
        aqo["parameters"] = {
            param["name"]: param["default"] for _, param in sorted(params.items(), key=lambda item: item[1]["name"])
        }

    metadata: dict[str, object] = {
        "compiler": "eigen-compiler",
        "compiler_contract_version": "1.0.0",
        "eigen_lang_version": "1.0",
        "source_sha256": source_digest,
        "request_sha256": request_digest,
    }

    if metadata:
        aqo["metadata"] = metadata

    checksums: dict[str, object] = {
        "source_sha256": source_digest,
        "request_sha256": request_digest,
    }
    aqo["checksums"] = checksums

    annotations: dict[str, object] = {}
    if observable_bindings:
        annotations["observables"] = observable_bindings
    if has_expectation:
        annotations["expectation"] = expectation_annotation or {"kind": "ExpectationValue"}
    if has_minimize:
        annotations["hybrid_plan_marker"] = {"kind": "minimize", "expanded_by": "kernel"}
    if annotations:
        aqo["annotations"] = annotations

    if distributed.enabled:
        aqo["topology"] = {
            "version": "1.0.0",
            "enabled": True,
            "target": distributed.target or "cluster",
            "partition_count": distributed.partition_count or 1,
            "queue_provider": distributed.queue_provider or "",
            "topology_hint": distributed.topology_hint or "data_parallel",
        }

    return aqo


def compile_eigen_lang(
    source: bytes,
    *,
    source_ref: str | None = None,
    options: dict[str, str] | None = None,
    observer: StageObserver | None = None,
    request_context: dict[str, str] | None = None,
) -> CompilationResult:
    """Compile source bytes into a canonical AQO v1.0 payload."""

    normalized_options = _normalize_options(options)
    normalized_request_context = _normalize_request_context(request_context)
    resolved_source, source_precedence = _resolve_source_bytes(source, source_ref)
    source_digest = hashlib.sha256(resolved_source).hexdigest()
    compile_started = perf_counter()
    
    def _parse_stage() -> ast.AST:
        try:
            return _parse_python_source(resolved_source)
        except CompilerValidationError as exc:
            raise CompilerValidationError(
                violations=_relabel_violations(
                    exc.violations, stage="parse", rule="compiler.source.parse", pass_name="parse"
                )
            ) from None

    tree = _run_stage("parse", observer, _parse_stage)

    def _validate_tree() -> None:
        try:
            violations = (
                _enforce_resource_limits(tree)
                + _reject_forbidden_imports(tree)
                + _reject_forbidden_calls(tree)
                + _reject_dynamic_control_flow(tree)
                + _validate_single_entrypoint(tree)
            )
            if violations:
                raise CompilerValidationError(violations=violations)
        except CompilerValidationError as exc:
            raise CompilerValidationError(
                violations=_relabel_violations(
                    exc.violations,
                    stage="validate_ast",
                    rule="compiler.source.validate_ast",
                    pass_name="validate_ast",
                )
            ) from None

    _run_stage("validate_ast", observer, _validate_tree)

    def _annotate_tree() -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]], dict[str, object] | None]:
        try:
            params, param_violations = _collect_params(tree)
            if param_violations:
                raise CompilerValidationError(violations=param_violations)
            observable_bindings, observable_violations = _collect_observable_bindings(tree)
            if observable_violations:
                raise CompilerValidationError(violations=observable_violations)
            expectation_annotation = _collect_expectation_annotation(tree, observable_bindings)
            return params, observable_bindings, expectation_annotation
        except CompilerValidationError as exc:
            raise CompilerValidationError(
                violations=_relabel_violations(
                    exc.violations,
                    stage="annotate",
                    rule="compiler.source.annotate",
                    pass_name="annotate",
                )
            ) from None

    params, observable_bindings, expectation_annotation = _run_stage("annotate", observer, _annotate_tree)
    
    def _lower_to_ir() -> tuple[list[dict], int]:
        try:
            return _collect_operations(tree, params)
        except CompilerValidationError as exc:
            raise CompilerValidationError(
                violations=_relabel_violations(
                    exc.violations,
                    stage="lower_to_ir",
                    rule="compiler.source.lower_to_ir",
                    pass_name="lower_to_ir",
                )
            ) from None

    operations, qubits = _run_stage("lower_to_ir", observer, _lower_to_ir)
    has_minimize = _run_stage(
        "eigen_dpda",
        observer,
        lambda: any(isinstance(node, ast.Call) and _call_name(node.func) == "minimize" for node in ast.walk(tree)),
    )
    has_expectation = _run_stage(
        "eigen_dpda",
        observer,
        lambda: any(
            isinstance(node, ast.Call) and _call_name(node.func) == "ExpectationValue" for node in ast.walk(tree)
        ),
    )
    distributed = _distributed_compile_config(options)
    
    def _resolve_and_validate_profile() -> object:
        try:
            workload_profile, selection_violations = resolve_workload_profile(
                normalized_options,
                has_expectation=has_expectation,
                has_minimize=has_minimize,
            )
            if selection_violations:
                raise CompilerValidationError(violations=selection_violations)
            
            profile_violations = validate_workload_profile(
                workload_profile,
                normalized_options,
                source_ref_present=source_ref is not None,
                has_expectation=has_expectation,
                has_minimize=has_minimize,
            )
            if profile_violations:
                raise CompilerValidationError(violations=profile_violations)
            return workload_profile
        except CompilerValidationError as exc:
            raise CompilerValidationError(
                violations=_relabel_violations(
                    exc.violations,
                    stage="eigen_dpda",
                    rule="compiler.profile.validation",
                    pass_name="eigen_dpda",
                )
            ) from None

    workload_profile = _run_stage("eigen_dpda", observer, _resolve_and_validate_profile)

    workload_profile_json = _canonical_json_text(workload_profile_payload(workload_profile))
    backend_contract = backend_contract_payload(workload_profile, normalized_options)
    backend_contract_json = _canonical_json_text(backend_contract)
    
    request_digest_payload = {
        "options": normalized_options,
        "request_context": asdict(normalized_request_context),
        "source_sha256": source_digest,
        "advisory_snapshot": _compiler_replay_snapshot(),
    }
    aqo_request_digest = hashlib.sha256(_canonical_json_bytes(request_digest_payload)).hexdigest()

    request_payload = {
        "options": normalized_options,
        "request_context": asdict(normalized_request_context),
        "source_precedence": source_precedence,
        "workload_profile": workload_profile.kind,
        "workload_profile_json": workload_profile_json,
        "source_ref": source_ref or "",
        "source_sha256": source_digest,
        "advisory_snapshot": _compiler_replay_snapshot(),
    }
    request_digest = hashlib.sha256(_canonical_json_bytes(request_payload)).hexdigest()
    options_json = _canonical_json_bytes(normalized_options).decode("utf-8")
    request_context_json = _canonical_json_bytes(asdict(normalized_request_context)).decode("utf-8")

    symbolic_candidate_set = enumerate_symbolic_candidates(
        qubits=qubits,
        operations=operations,
        params=params,
        source_digest=source_digest,
        request_digest=aqo_request_digest,
        has_expectation=has_expectation,
        has_minimize=has_minimize,
        observable_bindings=observable_bindings,
        expectation_annotation=expectation_annotation,
        distributed=distributed,
    )
    symbolic_candidate_set_payload = _symbolic_candidate_set_payload(symbolic_candidate_set)
    symbolic_candidate_set_json = _canonical_json_text(symbolic_candidate_set_payload)
    symbolic_candidate_set_sha256 = hashlib.sha256(symbolic_candidate_set_json.encode("utf-8")).hexdigest()
    logical_graph_schema_payload = _logical_graph_schema_payload()
    logical_graph_schema_json = _canonical_json_text(logical_graph_schema_payload)
    logical_graph_schema_sha256 = hashlib.sha256(logical_graph_schema_json.encode("utf-8")).hexdigest()
    
    def _build_pass_pipeline() -> CompilerPassPipeline:
        try:
            return _build_compiler_pass_pipeline(
                qubits=qubits,
                operations=operations,
                params=params,
                source_digest=source_digest,
                source_precedence=source_precedence,
                request_digest=aqo_request_digest,
                has_expectation=has_expectation,
                has_minimize=has_minimize,
                observable_bindings=observable_bindings,
                expectation_annotation=expectation_annotation,
                distributed=distributed,
            )
        except CompilerValidationError as exc:
            raise CompilerValidationError(
                violations=_relabel_violations(
                    exc.violations,
                    stage="eigen_dpda",
                    rule="compiler.pass_pipeline.build",
                    pass_name="canonicalize_aqo",
                )
            ) from None

    pass_pipeline = _run_stage("eigen_dpda", observer, _build_pass_pipeline)

    aqo = pass_pipeline.aqo

    def _canonicalize_aqo() -> bytes:
        try:
            return _canonical_json_bytes(aqo)
        except CompilerValidationError as exc:
            raise CompilerValidationError(
                violations=_relabel_violations(
                    exc.violations,
                    stage="canonicalize_aqo",
                    rule="compiler.aqo.canonicalize",
                    pass_name="canonicalize_aqo",
                )
            ) from None
    aqo_bytes = _run_stage("canonicalize_aqo", observer, _canonicalize_aqo)
    aqo_digest = hashlib.sha256(aqo_bytes).hexdigest()

    compiler_stage_order = [
        "parse",
        "validate_ast",
        "annotate",
        "lower_to_ir",
        "eigen_dpda",
        "canonicalize_aqo",
        "emit",
    ]
    handoff_stage_order = [
        "parse",
        "semantic_validation",
        "annotate",
        "lower_to_ir",
        "lowering_validation",
        "eigen_dpda",
        "canonicalize_aqo",
        "emit",
    ]

    ranked_candidates = symbolic_candidate_set_payload.get("ranked_candidates", [])
    telemetry_graph_encoding = ranked_candidates[0]["graph_encoding"] if ranked_candidates and isinstance(ranked_candidates[0], dict) else (
        symbolic_candidate_set_payload["candidates"][0].get("graph_encoding") if symbolic_candidate_set_payload.get("candidates") else {}
    )
    telemetry_feature_set_payload = _telemetry_feature_set_payload(
        graph_encoding=telemetry_graph_encoding if isinstance(telemetry_graph_encoding, dict) else {},
        compiler_telemetry={
            "stage_count": len(compiler_stage_order),
            "stage_success_count": len(compiler_stage_order),
            "stage_failure_count": 0,
            "latency_ms": round((perf_counter() - compile_started) * 1000.0, 6),
            "backend": backend_contract.get("declared_backend_target", "") or backend_contract.get("backend_target_class", ""),
            "policy_state": workload_profile.kind,
        },
        kb_telemetry={
            "past_success_count": len(ranked_candidates),
            "past_failure_count": max(int(symbolic_candidate_set_payload.get("candidate_count", 0) or 0) - len(ranked_candidates), 0),
            "past_success_rate": round(
                len(ranked_candidates) / max(int(symbolic_candidate_set_payload.get("candidate_count", 0) or 0), 1),
                6,
            ),
        },
        source="compiler_and_kb_telemetry",
    )
    telemetry_feature_set_json = _canonical_json_text(telemetry_feature_set_payload)
    telemetry_feature_set_sha256 = hashlib.sha256(telemetry_feature_set_json.encode("utf-8")).hexdigest()

    replay_bundle, replay_bundle_sha256 = _compiler_replay_bundle(
        request_context=normalized_request_context,
        workload_profile=workload_profile.kind,
        source_precedence=source_precedence,
        source_digest=source_digest,
        request_digest=request_digest,
        aqo_digest=aqo_digest,
        compiler_stage_order=compiler_stage_order,
        handoff_stage_order=handoff_stage_order,
        pass_pipeline=pass_pipeline,
        symbolic_candidate_set=symbolic_candidate_set,
        logical_graph_schema=logical_graph_schema_payload,
        telemetry_feature_set=telemetry_feature_set_payload,
    )

    decision_lineage = {
        "contract_version": "1.0.0",
        "compiler_contract_version": "1.0.0",
        "optimizer_contract_version": "1.0.0",
        "source_precedence": source_precedence,
        "stage_order": handoff_stage_order,
        "request_id": normalized_request_context.request_id,
        "trace_id": normalized_request_context.trace_id,
        "traceparent": normalized_request_context.traceparent,
        "workload_profile": workload_profile.kind,
        "source_sha256": source_digest,
        "aqo_sha256": aqo_digest,
        "request_sha256": request_digest,"replay_mode": _REPLAY_MODE_DETERMINISTIC,
        "replay_bundle_sha256": replay_bundle_sha256,
        "model_snapshot": replay_bundle["model_snapshot"],
    }
    observability = {
        "contract_version": "1.0.0",
        "trace_fields": ["request_id", "trace_id", "traceparent"],
        "metric_fields": ["rpc", "stage", "outcome", "elapsed_ms"],
        "metric_bounds": {
            "labels_bounded": True,
            "request_ids_in_metrics": False,
            "trace_ids_in_metrics": False,
            "tenant_ids_in_metrics": False,
            "project_ids_in_metrics": False,
        },
        "lineage_sha256": request_digest,
    }
    explainability = {
        "contract_version": "1.0.0",
        "decision": "compiler_to_optimizer_handoff",
        "trace_fields": ["request_id", "trace_id", "traceparent"],
        "lineage": decision_lineage,
        "bounded_fields": [
            "request_id",
            "trace_id",
            "traceparent",
            "source_sha256",
            "aqo_sha256",
            "request_sha256",
            "replay_bundle_sha256",
        ],
    }
    compiler_diagnostics = {
        "contract_version": "1.0.0",
        "stage_order": compiler_stage_order,
        "workload_profile": workload_profile.kind,
        "backend_contract": backend_contract,
        "decision_lineage": {
            **decision_lineage,
            "stage_order": compiler_stage_order,
        },
        "replay": replay_bundle,
        "observability": observability,
        "explainability": {
            **explainability,
            "lineage": {
                **decision_lineage,
                "stage_order": compiler_stage_order,
            },
        },
        "symbolic_candidate_set": symbolic_candidate_set_payload,
        "logical_graph_schema": logical_graph_schema_payload,
        "telemetry_feature_set": telemetry_feature_set_payload,
    }

    metadata = {
        "compiler": "eigen-compiler",
        "compiler_contract_version": "1.0.0",
        "eigen_lang_version": "1.0",
        "aqo_version": AQO_VERSION,
        "input_bytes": str(len(source)),
        "source_sha256": source_digest,
        "aqo_sha256": aqo_digest,
        "request_sha256": request_digest,
        "source_precedence": source_precedence,
        "options_json": options_json,
        "options_sha256": hashlib.sha256(options_json.encode("utf-8")).hexdigest(),
        "request_context_json": request_context_json,
        "request_id": normalized_request_context.request_id,
        "trace_id": normalized_request_context.trace_id,
        "traceparent": normalized_request_context.traceparent,
        "deadline": normalized_request_context.deadline,
        "retry_policy": normalized_request_context.retry_policy,
        "security_context": normalized_request_context.security_context,
        "sandbox_profile": normalized_request_context.sandbox_profile,
        "tenant_id": normalized_request_context.tenant_id,
        "project_id": normalized_request_context.project_id,
        "compiler_pass_pipeline_version": "1.0.0",
        "compiler_passes_json": _canonical_json_text(
            {
                "version": "1.0.0",
                "passes": [
                    {
                        "name": record.name,
                        "kind": record.kind,
                        "rule": record.rule,
                        "preconditions": list(record.preconditions),
                        "postconditions": list(record.postconditions),
                        "input": record.input,
                        "output": record.output,
                    }
                    for record in pass_pipeline.records
                ],
            }
        ),
        "compiler_replay_json": _canonical_json_text(replay_bundle),
        "compiler_replay_sha256": replay_bundle_sha256,
        "workload_profile": workload_profile.kind,
        "workload_profile_json": workload_profile_json,
        "backend_contract_version": "1.0.0",
        "backend_contract_json": backend_contract_json,
        "compiler_diagnostics_json": _canonical_json_text(compiler_diagnostics),
        "symbolic_candidate_set_json": symbolic_candidate_set_json,
        "symbolic_candidate_set_sha256": symbolic_candidate_set_sha256,
        "logical_graph_schema_json": logical_graph_schema_json,
        "logical_graph_schema_sha256": logical_graph_schema_sha256,
        "telemetry_feature_set_json": telemetry_feature_set_json,
        "telemetry_feature_set_sha256": telemetry_feature_set_sha256,
    }
    if has_minimize:
        metadata["hybrid_plan_marker"] = "minimize"
    if source_ref:
        metadata["source_ref"] = source_ref
    metadata["distributed.execution_metadata_version"] = "1.0.0"
    metadata["distributed.topology_hints_version"] = "1.0.0"
    metadata["distributed.enabled"] = "true" if distributed.enabled else "false"
    if distributed.enabled:
        metadata["distributed.target"] = distributed.target or "cluster"
        metadata["distributed.partition_count"] = str(distributed.partition_count or 1)
        metadata["distributed.topology_hint"] = distributed.topology_hint or "data_parallel"
        if distributed.queue_provider:
            metadata["distributed.queue_provider"] = distributed.queue_provider

    metadata["decision_lineage_json"] = _canonical_json_text(decision_lineage)
    metadata["observability_json"] = _canonical_json_text(observability)
    metadata["explainability_json"] = _canonical_json_text(explainability)

    return _run_stage("emit", observer, lambda: CompilationResult(aqo_json=aqo_bytes, metadata=metadata))


@contextmanager
def stage_observer_logger(logger, request_context: CompileRequestContext) -> Iterator[StageObserver]:
    def _observer(stage: str, elapsed_seconds: float, outcome: str) -> None:
        logger.info(
            "compiler_stage",
            extra={
                "stage": stage,
                "elapsed_ms": round(elapsed_seconds * 1000.0, 3),
                "outcome": outcome,
                "request_id": request_context.request_id,
                "trace_id": request_context.trace_id,
                "traceparent": request_context.traceparent,
                "sandbox_profile": request_context.sandbox_profile,
            },
        )

    yield _observer
