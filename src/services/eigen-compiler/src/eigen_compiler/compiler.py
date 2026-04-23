"""Minimal Eigen-Lang -> AQO JSON compiler for MVP RPC scaffolding."""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass

from .errors import FieldViolation


@dataclass(frozen=True)
class CompilationResult:
    aqo_json: bytes
    metadata: dict[str, str]

@dataclass(frozen=True)
class CompilerValidationError(Exception):
    violations: tuple[FieldViolation, ...]


def _parse_python_source(source: bytes) -> ast.AST | None:
    if not source:
        return None
    try:
        return ast.parse(source.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError):
        return None


def _reject_dynamic_control_flow(tree: ast.AST) -> None:
    banned_nodes = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Match, ast.IfExp)
    if any(isinstance(node, banned_nodes) for node in ast.walk(tree)):
        raise CompilerValidationError(
            violations=(
                FieldViolation(
                    field="source",
                    description="dynamic runtime control flow is not supported in Eigen-Lang MVP",
                ),
            )
        )


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _collect_params(tree: ast.AST) -> dict[str, str]:
    params: dict[str, str] = {}
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
            params[target] = name_arg.value
    return params


def _collect_operations(tree: ast.AST, params: dict[str, str]) -> tuple[list[dict], int]:
    operations: list[dict] = []
    qubit_count = 1
    gate_ops = {"rx": "RX", "ry": "RY", "rz": "RZ"}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = _call_name(node.func)
        if name in gate_ops:
            op: dict[str, object] = {"op": gate_ops[name], "q": [0]}
            theta_expr = next((kw.value for kw in node.keywords if kw.arg == "theta"), None)
            if isinstance(theta_expr, ast.Name) and theta_expr.id in params:
                op["params"] = {"theta": params[theta_expr.id]}
            elif isinstance(theta_expr, ast.Constant) and isinstance(theta_expr.value, (int, float)):
                op["params"] = {"theta": float(theta_expr.value)}
            operations.append(op)
        elif name == "cx":
            operations.append({"op": "CX", "q": [0, 1]})
            qubit_count = max(qubit_count, 2)

    if not operations:
        operations = [{"op": "RY", "q": [0], "params": {"theta": 1.570796}}]

    operations.append({"op": "MEASURE", "q": list(range(qubit_count)), "c": list(range(qubit_count))})
    return operations, qubit_count


def compile_eigen_lang(source: bytes, *, source_ref: str | None = None) -> CompilationResult:
    """Compile source bytes into a tiny AQO v0.1 payload.

    This is an MVP stub used to prove RPC contract wiring.
    """

    digest = hashlib.sha256(source).hexdigest() if source else ""
    tree = _parse_python_source(source)

    if tree is not None:
        _reject_dynamic_control_flow(tree)
        params = _collect_params(tree)
        operations, qubits = _collect_operations(tree, params)
        has_minimize = any(
            isinstance(node, ast.Call) and _call_name(node.func) == "minimize" for node in ast.walk(tree)
        )
        has_expectation = any(
            isinstance(node, ast.Call) and _call_name(node.func) == "ExpectationValue"
            for node in ast.walk(tree)
        )
    else:
        params = {}
        operations = [
            {"op": "RY", "q": [0], "params": {"theta": 1.570796}},
            {"op": "MEASURE", "q": [0], "c": [0]},
        ]
        qubits = 1
        has_minimize = False
        has_expectation = False

    aqo = {
        "version": "0.1",
        "qubits": qubits,
        "operations": operations,
    }
    if params:
        aqo["parameters"] = [{"name": name} for _, name in sorted(params.items())]
    if has_expectation:
        aqo["expectation"] = {"kind": "ExpectationValue"}
    if has_minimize:
        aqo["hybrid_plan_marker"] = {"kind": "minimize", "expanded_by": "kernel"}

    aqo_bytes = json.dumps(aqo, separators=(",", ":"), sort_keys=True).encode("utf-8")

    metadata = {
        "compiler": "eigen-compiler",
        "aqo_version": "0.1",
        "input_bytes": str(len(source)),
        "source_sha256": digest,
    }
    if has_minimize:
        metadata["hybrid_plan_marker"] = "minimize"
    if source_ref:
        metadata["source_ref"] = source_ref

    return CompilationResult(aqo_json=aqo_bytes, metadata=metadata)
