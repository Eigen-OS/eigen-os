"""Minimal Eigen-Lang -> AQO JSON compiler for MVP."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from dataclasses import dataclass

from .errors import FieldViolation

_ALLOWED_IMPORT_PREFIXES = ("eigen_lang",)
_FORBIDDEN_MODULE_ROOTS = {"os", "sys", "subprocess", "socket", "ctypes", "importlib", "requests"}
_FORBIDDEN_CALLS = {"exec", "eval", "compile", "open", "__import__"}


@dataclass(frozen=True)
class CompilationResult:
    aqo_json: bytes
    metadata: dict[str, str]

@dataclass(frozen=True)
class CompilerValidationError(Exception):
    violations: tuple[FieldViolation, ...]


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
            violations=(
                FieldViolation(
                    field="source",
                    description="source must be valid UTF-8 Python syntax",
                ),
            )
        )


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

def _reject_forbidden_imports(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_root = alias.name.split(".", 1)[0]
                if module_root in _FORBIDDEN_MODULE_ROOTS or module_root not in _ALLOWED_IMPORT_PREFIXES:
                    raise CompilerValidationError(
                        violations=(
                            FieldViolation(
                                field="source",
                                description=f"import '{alias.name}' is not allowed in Eigen-Lang MVP",
                            ),
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            module_root = module.split(".", 1)[0]
            if module_root not in _ALLOWED_IMPORT_PREFIXES:
                raise CompilerValidationError(
                    violations=(
                        FieldViolation(
                            field="source",
                            description=f"import from '{module}' is not allowed in Eigen-Lang MVP",
                        ),
                    )
                )


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None

def _reject_forbidden_calls(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name in _FORBIDDEN_CALLS:
            raise CompilerValidationError(
                violations=(
                    FieldViolation(
                        field="source",
                        description=f"call '{name}' is not allowed in Eigen-Lang MVP",
                    ),
                )
            )


def _enforce_resource_limits(tree: ast.AST) -> None:
    max_ast_nodes = _compiler_limit("EIGEN_COMPILER_MAX_AST_NODES", 50_000)
    max_nesting_depth = _compiler_limit("EIGEN_COMPILER_MAX_AST_DEPTH", 200)

    node_count = 0
    max_depth_seen = 0
    stack: list[tuple[ast.AST, int]] = [(tree, 1)]
    while stack:
        node, depth = stack.pop()
        node_count += 1
        if node_count > max_ast_nodes:
            raise CompilerValidationError(
                violations=(
                    FieldViolation(
                        field="source",
                        description=f"AST node limit exceeded ({max_ast_nodes})",
                    ),
                )
            )
        max_depth_seen = max(max_depth_seen, depth)
        if max_depth_seen > max_nesting_depth:
            raise CompilerValidationError(
                violations=(
                    FieldViolation(
                        field="source",
                        description=f"AST depth limit exceeded ({max_nesting_depth})",
                    ),
                )
            )
        for child in ast.iter_child_nodes(node):
            stack.append((child, depth + 1))


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

    """

    digest = hashlib.sha256(source).hexdigest() if source else ""
    tree = _parse_python_source(source)
    _enforce_resource_limits(tree)
    _reject_forbidden_imports(tree)
    _reject_forbidden_calls(tree)
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
