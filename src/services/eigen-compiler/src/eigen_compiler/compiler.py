"""Deterministic Eigen-Lang -> AQO compiler core."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

from .errors import FieldViolation

_ALLOWED_IMPORT_PREFIXES = ("eigen_lang",)
_FORBIDDEN_MODULE_ROOTS = {"os", "sys", "subprocess"}
_FORBIDDEN_CALLS = {"exec", "eval", "compile"}


@dataclass(frozen=True)
class CompileRequestContext:
    request_id: str = ""
    trace_id: str = ""
    traceparent: str = ""
    deadline: str = ""
    retry_policy: str = ""
    security_context: str = ""
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
class CompilerValidationError(Exception):
    violations: tuple[FieldViolation, ...]


def _canonical_json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _normalize_options(options: dict[str, str] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in sorted((options or {}).items()):
        normalized[str(key)] = str(value)
    return normalized


def _normalize_request_context(request_context: dict[str, str] | None) -> CompileRequestContext:
    context = request_context or {}
    return CompileRequestContext(
        request_id=str(context.get("request_id", "")),
        trace_id=str(context.get("trace_id", "")),
        traceparent=str(context.get("traceparent", "")),
        deadline=str(context.get("deadline", "")),
        retry_policy=str(context.get("retry_policy", "")),
        security_context=str(context.get("security_context", "")),
        tenant_id=str(context.get("tenant_id", "")),
        project_id=str(context.get("project_id", "")),
    )


def _resolve_source_bytes(source: bytes, source_ref: str | None) -> tuple[bytes, str]:
    if source:
        return source, "source"
    if not source_ref:
        raise CompilerValidationError(
            violations=(
                FieldViolation(field="source", description="source or source_ref is required"),
            )
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
            violations=(
                FieldViolation(field="source_ref", description="source_ref escapes QFS root"),
            )
        )
    try:
        return ref_path.read_bytes(), "source_ref"
    except FileNotFoundError:
        raise CompilerValidationError(
            violations=(
                FieldViolation(field="source_ref", description=f"source_ref not found: {source_ref}"),
            )
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
            violations=(
                FieldViolation(
                    field="source",
                    description="source must be valid UTF-8 Python syntax",
                ),
            )
        )


def _reject_dynamic_control_flow(tree: ast.AST) -> tuple[FieldViolation, ...]:
    banned_nodes = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Match, ast.IfExp)
    if any(isinstance(node, banned_nodes) for node in ast.walk(tree)):
        return (
            FieldViolation(
                field="source",
                description="dynamic runtime control flow is not supported in Eigen-Lang MVP",
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
                            description=f"import '{alias.name}' is not allowed in Eigen-Lang MVP",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            module_root = module.split(".", 1)[0]
            if module_root in _FORBIDDEN_MODULE_ROOTS or module_root not in _ALLOWED_IMPORT_PREFIXES:
                violations.append(
                    FieldViolation(
                        field="source",
                        description=f"import from '{module}' is not allowed in Eigen-Lang MVP",
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
                    description=f"call '{name}' is not allowed in Eigen-Lang MVP",
                )
            )
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            module_root = node.func.value.id
            if module_root in _FORBIDDEN_MODULE_ROOTS:
                violations.append(
                    FieldViolation(
                        field="source",
                        description=f"dynamic I/O call '{module_root}.{name}' is not allowed in Eigen-Lang MVP",
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
                FieldViolation(
                    field="source",
                    description=f"AST node limit exceeded ({max_ast_nodes})",
                ),
            )
        max_depth_seen = max(max_depth_seen, depth)
        if max_depth_seen > max_nesting_depth:
            return (
                FieldViolation(
                    field="source",
                    description=f"AST depth limit exceeded ({max_nesting_depth})",
                ),
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

    operations.append({"op": "MEASURE", "q": list(range(qubit_count)), "c": list(range(qubit_count))})
    return operations, qubit_count


def _distributed_compile_config(options: dict[str, str] | None) -> DistributedCompileConfig:
    options = _normalize_options(options)
    enabled = options.get("distributed.enabled", "false").lower() == "true"
    target = options.get("distributed.target") or None

    partition_count: int | None = None
    if "distributed.partition_count" in options:
        partition_count = int(options["distributed.partition_count"])

    queue_provider = options.get("distributed.queue_provider") or None
    topology_hint = options.get("distributed.topology_hint") or None
    return DistributedCompileConfig(
        enabled=enabled,
        target=target,
        partition_count=partition_count,
        queue_provider=queue_provider,
        topology_hint=topology_hint,
    )


def compile_eigen_lang(
    source: bytes,
    *,
    source_ref: str | None = None,
    options: dict[str, str] | None = None,
    request_context: dict[str, str] | None = None,
) -> CompilationResult:
    """Compile Eigen-Lang source into a canonical AQO payload."""

    normalized_options = _normalize_options(options)
    normalized_request_context = _normalize_request_context(request_context)
    resolved_source, source_precedence = _resolve_source_bytes(source, source_ref)
    source_digest = hashlib.sha256(resolved_source).hexdigest()
    tree = _parse_python_source(resolved_source)
    violations = (
        _enforce_resource_limits(tree)
        + _reject_forbidden_imports(tree)
        + _reject_forbidden_calls(tree)
        + _reject_dynamic_control_flow(tree)
        + _validate_single_entrypoint(tree)
    )
    if violations:
        raise CompilerValidationError(violations=violations)
    params = _collect_params(tree)
    operations, qubits = _collect_operations(tree, params)
    has_minimize = any(
        isinstance(node, ast.Call) and _call_name(node.func) == "minimize" for node in ast.walk(tree)
    )
    has_expectation = any(
        isinstance(node, ast.Call) and _call_name(node.func) == "ExpectationValue"
        for node in ast.walk(tree)
    )
    distributed = _distributed_compile_config(normalized_options)

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
    if distributed.enabled:
        aqo["distributed_execution"] = {
            "version": "1.0.0",
            "target": distributed.target or "cluster",
            "partition_count": distributed.partition_count or 1,
            "hints": {
                "version": "1.0.0",
                "topology_hint": distributed.topology_hint or "data_parallel",
            },
        }
        if distributed.queue_provider:
            aqo["distributed_execution"]["queue_provider"] = distributed.queue_provider

    aqo_bytes = json.dumps(aqo, sort_keys=True, separators=(",", ":")).encode("utf-8")
    aqo_digest = hashlib.sha256(aqo_bytes).hexdigest()
    request_payload = {
        "options": normalized_options,
        "request_context": asdict(normalized_request_context),
        "source_precedence": source_precedence,
        "source_ref": source_ref or "",
        "source_sha256": source_digest,
    }
    request_digest = hashlib.sha256(_canonical_json_bytes(request_payload)).hexdigest()
    options_json = _canonical_json_bytes(normalized_options).decode("utf-8")
    request_context_json = _canonical_json_bytes(asdict(normalized_request_context)).decode("utf-8")

    metadata = {
        "compiler": "eigen-compiler",
        "compiler_contract_version": "1.0.0",
        "eigen_lang_version": "1.0",
        "aqo_version": "0.1",
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
        "tenant_id": normalized_request_context.tenant_id,
        "project_id": normalized_request_context.project_id,
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

    return CompilationResult(aqo_json=aqo_bytes, metadata=metadata)
