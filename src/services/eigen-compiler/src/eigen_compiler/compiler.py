"""Deterministic Eigen-Lang -> AQO compiler core."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from math import isfinite
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from time import perf_counter
from typing import Callable, Iterator, TypeVar
from pathlib import Path

from .errors import FieldViolation

AQO_VERSION = "1.0.0"

_ALLOWED_IMPORT_PREFIXES = ("eigen_lang",)
_FORBIDDEN_MODULE_ROOTS = {"os", "sys", "subprocess"}
_FORBIDDEN_CALLS = {"exec", "eval", "compile"}
T = TypeVar("T")

StageObserver = Callable[[str, float, str], None]
_AQO_ALLOWED_TOP_LEVEL_FIELDS = {"version", "qubits", "operations", "parameters", "metadata", "checksums", "topology", "annotations"}
_AQO_ALLOWED_OPS = {"RX", "RY", "RZ", "CX", "CZ", "SWAP", "CCX", "CCZ", "X", "Y", "Z", "H", "S", "T", "MEASURE", "RESET"}
_AQO_ROTATION_OPS = {"RX", "RY", "RZ"}
_AQO_MEASUREMENT_BASIS = {"X", "Y", "Z"}
_AQO_NON_PARAMETERIZED_OPS = {"CX", "CZ", "SWAP", "CCX", "CCZ", "X", "Y", "Z", "H", "S", "T", "RESET"}
_AQO_ARITY = {"RX": 1, "RY": 1, "RZ": 1, "CX": 2, "CZ": 2, "SWAP": 2, "CCX": 3, "CCZ": 3, "X": 1, "Y": 1, "Z": 1, "H": 1, "S": 1, "T": 1, "MEASURE": 1, "RESET": 1}


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


def _literal_scalar(node: ast.AST) -> str | int | float | None:
    if not isinstance(node, ast.Constant):
        return None
    if isinstance(node.value, (str, int)):
        return node.value
    if isinstance(node.value, float) and isfinite(node.value):
        return float(node.value)
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
        if op_name in {"MEASURE"}:
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
            if len(q) < 1:
                violations.append(FieldViolation(field=f"operations[{idx}].q", description="MEASURE requires at least one qubit"))
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


def _collect_operations(tree: ast.AST, params: dict[str, dict[str, object]]) -> tuple[list[dict], int]:
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
                op["params"] = {"theta": params[theta_expr.id]["name"]}
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
    observer: StageObserver | None = None,
    request_context: dict[str, str] | None = None,
) -> CompilationResult:
    """Compile source bytes into a canonical AQO v1.0 payload."""

    normalized_options = _normalize_options(options)
    normalized_request_context = _normalize_request_context(request_context)
    resolved_source, source_precedence = _resolve_source_bytes(source, source_ref)
    source_digest = hashlib.sha256(resolved_source).hexdigest()
    tree = _run_stage("parse", observer, lambda: _parse_python_source(source))

    def _validate_tree() -> None:
        violations = (
            _enforce_resource_limits(tree)
            + _reject_forbidden_imports(tree)
            + _reject_forbidden_calls(tree)
            + _reject_dynamic_control_flow(tree)
            + _validate_single_entrypoint(tree)
        )
        if violations:
            raise CompilerValidationError(violations=violations)

    _run_stage("validate_ast", observer, _validate_tree)

    def _annotate_tree() -> dict[str, str]:
        params = _collect_params(tree)
        return params

    params = _run_stage("annotate", observer, _annotate_tree)
    operations, qubits = _run_stage("lower_to_ir", observer, lambda: _collect_operations(tree, params))
    has_minimize = _run_stage(
        "eigen_dpda",
        observer,
        lambda: any(isinstance(node, ast.Call) and _call_name(node.func) == "minimize" for node in ast.walk(tree)),
    )
    has_expectation = _run_stage(
        "eigen_dpda",
        observer,
        lambda: any(
            isinstance(node, ast.Call) and _call_name(node.func) == "ExpectationValue"
            for node in ast.walk(tree)
        ),
    )
    distributed = _distributed_compile_config(options)

    aqo = _run_stage(
        "eigen_dpda",
        observer,
        lambda: {
            "version": "AQO_VERSION",
            "qubits": qubits,
            "operations": operations,
        },
    )
    if params:
        aqo["parameters"] = {
            param["name"]: param["default"] for _, param in sorted(params.items(), key=lambda item: item[1]["name"])
        }
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

    aqo_bytes = _run_stage(
        "canonicalize_aqo",
        observer,
        lambda: json.dumps(aqo, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    )
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
        "compiler_contract_version": "1.0.0",
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
