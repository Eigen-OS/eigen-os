"""Request and compiler rule validation for eigen-compiler."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from .errors import FieldViolation

_SUPPORTED_LANGUAGES = {"eigen-lang"}
_SUPPORTED_DISTRIBUTED_TARGETS = {"cluster"}
_SUPPORTED_QUEUE_PROVIDERS = {"memory", "redis", "sqs"}
_SUPPORTED_TOPOLOGY_HINTS = {"data_parallel", "pipeline"}

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

RULE_VERSION = "1.0.0"
REQUEST_CONTEXT_FIELDS = (
    "request_id",
    "trace_id",
    "traceparent",
    "deadline",
    "retry_policy",
    "security_context",
    "tenant_id",
    "project_id",
)


@dataclass(frozen=True)
class RuleSpec:
    name: str
    category: str
    description: str
    evaluator: Callable[[object], tuple[FieldViolation, ...]]


@dataclass(frozen=True)
class RuleResult:
    name: str
    category: str
    accepted: bool
    description: str
    violations: tuple[FieldViolation, ...]


@dataclass(frozen=True)
class RuleCatalog:
    name: str
    version: str
    rules: tuple[RuleSpec, ...]

    def evaluate(self, context: object, *, categories: Iterable[str] | None = None) -> tuple[RuleResult, ...]:
        allowed_categories = set(categories) if categories is not None else None
        results: list[RuleResult] = []
        for rule in self.rules:
            if allowed_categories is not None and rule.category not in allowed_categories:
                continue
            violations = tuple(rule.evaluator(context))
            results.append(
                RuleResult(
                    name=rule.name,
                    category=rule.category,
                    accepted=not violations,
                    description=rule.description,
                    violations=violations,
                )
            )
        return tuple(results)

    def violations(self, context: object, *, categories: Iterable[str] | None = None) -> tuple[FieldViolation, ...]:
        collected: list[FieldViolation] = []
        for result in self.evaluate(context, categories=categories):
            collected.extend(result.violations)
        return tuple(collected)


@dataclass(frozen=True)
class RequestRuleContext:
    request: object


@dataclass(frozen=True)
class CompilerRuleContext:
    source: bytes
    tree: ast.AST | None
    options: dict[str, str]
    request_context: dict[str, str]
    source_ref: str | None = None
    source_precedence: str = "source"
    source_digest: str = ""
    params: dict[str, dict[str, object]] | None = None
    operations: list[dict[str, object]] | None = None
    qubits: int | None = None


def _rule_violation(rule: str, *, field: str, description: str, location: str | None = None) -> FieldViolation:
    return FieldViolation(field=location or field, description=description, rule=rule, location=location or field)


def _max_source_bytes() -> int:
    raw = os.getenv("EIGEN_COMPILER_MAX_SOURCE_BYTES", "262144")
    try:
        value = int(raw)
    except ValueError:
        return 262_144
    return max(1, value)


def _parse_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return None


def _validate_source_inputs(req) -> list[FieldViolation]:
    violations: list[FieldViolation] = []
    source_present = bool(req.source)
    source_ref_present = bool(req.source_ref)

    if not source_present and not source_ref_present:
        violations.append(
            _rule_violation(
                "request.syntax.input_present",
                field="input",
                description="input or source_ref is required",
                location="input",
            )
        )
        return violations

    if source_ref_present:
        normalized = req.source_ref
        for prefix in ("qfs://", "circuitfs://"):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
                break
        ref_path = Path(normalized)
        if any(part == ".." for part in ref_path.parts):
            violations.append(
                _rule_violation(
                    "policy.source_ref.path_safety",
                    field="source_ref",
                    description="source_ref must not contain path traversal segments",
                    location="source_ref",
                )
            )

    if source_ref_present and not req.source_ref:
        violations.append(
            _rule_violation(
                "request.syntax.source_ref_non_empty",
                field="source_ref",
                description="source_ref must be non-empty",
                location="source_ref",
            )
        )
    return violations


def _validate_distributed_options(options: dict[str, str]) -> list[FieldViolation]:
    violations: list[FieldViolation] = []
    enabled_raw = options.get("distributed.enabled", "false")
    enabled = _parse_bool(enabled_raw)
    if enabled is None:
        violations.append(
            _rule_violation(
                "policy.distributed.enabled_boolean",
                field="options.distributed.enabled",
                description="distributed.enabled must be a boolean",
                location="options.distributed.enabled",
            )
        )
        return violations

    target = options.get("distributed.target")
    if target and target not in _SUPPORTED_DISTRIBUTED_TARGETS:
        violations.append(
            _rule_violation(
                "policy.distributed.target_supported",
                field="options.distributed.target",
                description="unsupported distributed target, expected cluster",
                location="options.distributed.target",
            )
        )

    partition_count_raw = options.get("distributed.partition_count")
    partition_count: int | None = None
    if partition_count_raw:
        try:
            partition_count = int(partition_count_raw)
        except ValueError:
            violations.append(
                _rule_violation(
                    "policy.distributed.partition_count_integer",
                    field="options.distributed.partition_count",
                    description="distributed.partition_count must be an integer",
                    location="options.distributed.partition_count",
                )
            )
        else:
            if partition_count < 1:
                violations.append(
                    _rule_violation(
                        "policy.distributed.partition_count_positive",
                        field="options.distributed.partition_count",
                        description="distributed.partition_count must be >= 1",
                        location="options.distributed.partition_count",
                    )
                )

    queue_provider = options.get("distributed.queue_provider")
    if queue_provider and queue_provider not in _SUPPORTED_QUEUE_PROVIDERS:
        violations.append(
            _rule_violation(
                "policy.distributed.queue_provider_supported",
                field="options.distributed.queue_provider",
                description="unsupported queue provider, expected one of: memory, redis, sqs",
                location="options.distributed.queue_provider",
            )
        )

    topology_hint = options.get("distributed.topology_hint")
    if topology_hint and topology_hint not in _SUPPORTED_TOPOLOGY_HINTS:
        violations.append(
            _rule_violation(
                "policy.distributed.topology_hint_supported",
                field="options.distributed.topology_hint",
                description="unsupported topology hint, expected one of: data_parallel, pipeline",
                location="options.distributed.topology_hint",
            )
        )

    if not enabled:
        for key in (
            "distributed.target",
            "distributed.partition_count",
            "distributed.queue_provider",
            "distributed.topology_hint",
        ):
            if key in options:
                violations.append(
                    _rule_violation(
                        f"policy.{key}.requires_enabled",
                        field=f"options.{key}",
                        description=f"{key} requires distributed.enabled=true",
                        location=f"options.{key}",
                    )
                )
    elif target is None:
        violations.append(
            _rule_violation(
                "policy.distributed.target_required",
                field="options.distributed.target",
                description="distributed.target is required when distributed.enabled=true",
                location="options.distributed.target",
            )
        )

    return violations


def build_request_rule_catalog() -> RuleCatalog:
    return RuleCatalog(
        name="compile_request_rules",
        version=RULE_VERSION,
        rules=(
            RuleSpec(
                name="request.syntax.language_supported",
                category="syntax",
                description="language must be eigen-lang",
                evaluator=lambda ctx: _validate_request_language(ctx),
            ),
            RuleSpec(
                name="request.syntax.input_present",
                category="syntax",
                description="source or source_ref is required",
                evaluator=lambda ctx: _validate_source_inputs(ctx.request),
            ),
            RuleSpec(
                name="request.policy.source_ref_path_safety",
                category="policy",
                description="source_ref must stay within the request boundary",
                evaluator=lambda ctx: _validate_request_source_ref(ctx),
            ),
            RuleSpec(
                name="request.policy.request_metadata_required",
                category="policy",
                description="request metadata must include trace and tenant scope when provided",
                evaluator=lambda ctx: _validate_request_metadata(ctx),
            ),
            RuleSpec(
                name="request.policy.source_size_limit",
                category="policy",
                description="source size must stay within the configured limit",
                evaluator=lambda ctx: _validate_request_source_size(ctx),
            ),
            RuleSpec(
                name="request.policy.distributed_options",
                category="policy",
                description="distributed options must satisfy the request contract",
                evaluator=lambda ctx: _validate_request_options(ctx),
            ),
        ),
    )


@dataclass(frozen=True)
class _RequestValidationContext:
    request: object


def _validate_request_language(ctx: _RequestValidationContext) -> tuple[FieldViolation, ...]:
    req = ctx.request
    if not getattr(req, "language", ""):
        return (_rule_violation("request.syntax.language_present", field="language", description="field is required", location="language"),)
    if req.language not in _SUPPORTED_LANGUAGES:
        return (
            _rule_violation(
                "request.syntax.language_supported",
                field="language",
                description="unsupported language, expected eigen-lang",
                location="language",
            ),
        )
    return ()


def _validate_request_source_ref(ctx: _RequestValidationContext) -> tuple[FieldViolation, ...]:
    req = ctx.request
    if not getattr(req, "source_ref", ""):
        return ()
    normalized = req.source_ref
    for prefix in ("qfs://", "circuitfs://"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    ref_path = Path(normalized)
    if any(part == ".." for part in ref_path.parts):
        return (
            _rule_violation(
                "policy.source_ref.path_safety",
                field="source_ref",
                description="source_ref must not contain path traversal segments",
                location="source_ref",
            ),
        )
    return ()


def _validate_request_metadata(ctx: _RequestValidationContext) -> tuple[FieldViolation, ...]:
    req = ctx.request
    if not getattr(req, "HasField", None) or not req.HasField("request_metadata"):
        return ()
    md = req.request_metadata
    required = {
        "request_metadata.request_id": md.request_id,
        "request_metadata.trace_id": md.trace_id,
        "request_metadata.traceparent": md.traceparent,
        "request_metadata.deadline": md.deadline,
        "request_metadata.retry_policy": md.retry_policy,
        "request_metadata.security_context": md.security_context,
        "request_metadata.tenant_id": md.tenant_id,
        "request_metadata.project_id": md.project_id,
    }
    violations: list[FieldViolation] = []
    for field, value in required.items():
        if not value:
            violations.append(
                _rule_violation(
                    "policy.request_metadata.required_fields",
                    field=field,
                    description="field is required",
                    location=field,
                )
            )
    return tuple(violations)


def _validate_request_source_size(ctx: _RequestValidationContext) -> tuple[FieldViolation, ...]:
    req = ctx.request
    source_limit = _max_source_bytes()
    if getattr(req, "source", b"") and len(req.source) > source_limit:
        return (
            _rule_violation(
                "policy.source_size.limit",
                field="source",
                description=f"source exceeds max allowed size ({source_limit} bytes)",
                location="source",
            ),
        )
    return ()


def _validate_request_options(ctx: _RequestValidationContext) -> tuple[FieldViolation, ...]:
    req = ctx.request
    return tuple(_validate_distributed_options(getattr(req, "options", {})))


@dataclass(frozen=True)
class _CompilerSemanticContext:
    tree: ast.AST
    source: bytes
    request_context: dict[str, str]
    options: dict[str, str]
    params: dict[str, dict[str, object]] | None = None
    operations: list[dict[str, object]] | None = None
    qubits: int | None = None
    source_ref: str | None = None
    source_precedence: str = "source"
    source_digest: str = ""


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _literal_scalar(node: ast.AST) -> str | int | float | None:
    if not isinstance(node, ast.Constant):
        return None
    if isinstance(node.value, (str, int)):
        return node.value
    if isinstance(node.value, float) and node.value == node.value and node.value not in {float("inf"), float("-inf")}:
        return float(node.value)
    return None


def _compiler_node_limit(ctx: _CompilerSemanticContext) -> tuple[FieldViolation, ...]:
    max_ast_nodes = int(os.getenv("EIGEN_COMPILER_MAX_AST_NODES", "50000") or "50000")
    node_count = 0
    stack: list[ast.AST] = [ctx.tree]
    while stack:
        node = stack.pop()
        node_count += 1
        if node_count > max_ast_nodes:
            return (
                _rule_violation(
                    "syntax.ast.node_limit",
                    field="source",
                    description=f"AST node limit exceeded ({max_ast_nodes})",
                    location="source",
                ),
            )
        for child in ast.iter_child_nodes(node):
            stack.append(child)
    return ()


def _compiler_depth_limit(ctx: _CompilerSemanticContext) -> tuple[FieldViolation, ...]:
    max_ast_depth = int(os.getenv("EIGEN_COMPILER_MAX_AST_DEPTH", "200") or "200")
    max_depth_seen = 0
    stack: list[tuple[ast.AST, int]] = [(ctx.tree, 1)]
    while stack:
        node, depth = stack.pop()
        max_depth_seen = max(max_depth_seen, depth)
        if max_depth_seen > max_ast_depth:
            return (
                _rule_violation(
                    "syntax.ast.depth_limit",
                    field="source",
                    description=f"AST depth limit exceeded ({max_ast_depth})",
                    location="source",
                ),
            )
        for child in ast.iter_child_nodes(node):
            stack.append((child, depth + 1))
    return ()


def _compiler_entrypoint_rule(ctx: _CompilerSemanticContext) -> tuple[FieldViolation, ...]:
    entrypoints = [
        node
        for node in ast.walk(ctx.tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(_decorator_name(decorator) == "hybrid_program" for decorator in node.decorator_list)
    ]
    if len(entrypoints) == 1:
        return ()
    if len(entrypoints) == 0:
        return (
            _rule_violation(
                "syntax.entrypoint.single",
                field="source",
                description="exactly one @hybrid_program entrypoint is required",
                location="source",
            ),
        )
    return (
        _rule_violation(
            "syntax.entrypoint.single",
            field="source",
            description=f"exactly one @hybrid_program entrypoint is required, found {len(entrypoints)}",
            location="source",
        ),
    )


def _decorator_name(decorator: ast.AST) -> str | None:
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Call):
        return _call_name(decorator.func)
    return None


def _compiler_forbidden_imports(ctx: _CompilerSemanticContext) -> tuple[FieldViolation, ...]:
    violations: list[FieldViolation] = []
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_root = alias.name.split(".", 1)[0]
                if module_root in {"os", "sys", "subprocess"} or module_root not in {"eigen_lang"}:
                    violations.append(
                        _rule_violation(
                            "policy.import.allowed",
                            field="source",
                            description=f"import '{alias.name}' is not allowed in Eigen-Lang",
                            location="source",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            module_root = module.split(".", 1)[0]
            if module_root in {"os", "sys", "subprocess"} or module_root not in {"eigen_lang"}:
                violations.append(
                    _rule_violation(
                        "policy.import.allowed",
                        field="source",
                        description=f"import from '{module}' is not allowed in Eigen-Lang",
                        location="source",
                    )
                )
    return tuple(violations)


def _compiler_forbidden_calls(ctx: _CompilerSemanticContext) -> tuple[FieldViolation, ...]:
    violations: list[FieldViolation] = []
    for node in ast.walk(ctx.tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name in {"exec", "eval", "compile"}:
            violations.append(
                _rule_violation(
                    "policy.call.allowed",
                    field="source",
                    description=f"call '{name}' is not allowed in Eigen-Lang",
                    location="source",
                )
            )
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            module_root = node.func.value.id
            if module_root in {"os", "sys", "subprocess"}:
                violations.append(
                    _rule_violation(
                        "policy.dynamic_io.forbidden",
                        field="source",
                        description=f"dynamic I/O call '{module_root}.{name}' is not allowed in Eigen-Lang",
                        location="source",
                    )
                )
    return tuple(violations)


def _compiler_dynamic_control_flow(ctx: _CompilerSemanticContext) -> tuple[FieldViolation, ...]:
    banned_nodes = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Match, ast.IfExp)
    if any(isinstance(node, banned_nodes) for node in ast.walk(ctx.tree)):
        return (
            _rule_violation(
                "syntax.control_flow.static",
                field="source",
                description="dynamic runtime control flow is not supported in Eigen-Lang",
                location="source",
            ),
        )
    return ()


def _compiler_param_defaults(ctx: _CompilerSemanticContext) -> tuple[FieldViolation, ...]:
    violations: list[FieldViolation] = []
    for node in ast.walk(ctx.tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if not isinstance(node.value, ast.Call) or _call_name(node.value.func) != "Param":
            continue
        if not node.value.args:
            continue
        name_arg = node.value.args[0]
        if not isinstance(name_arg, ast.Constant) or not isinstance(name_arg.value, str):
            continue
        if len(node.value.args) > 1:
            explicit_default = _literal_scalar(node.value.args[1])
            if explicit_default is None:
                violations.append(
                    _rule_violation(
                        "semantic.param.default.literal",
                        field="source",
                        description="Param default must be a literal integer, float, or string",
                        location="source",
                    )
                )
    return tuple(violations)


def _compiler_lowering_rules(ctx: _CompilerSemanticContext) -> tuple[FieldViolation, ...]:
    violations: list[FieldViolation] = []
    if ctx.operations is None:
        return ()

    qubits = ctx.qubits
    for idx, op in enumerate(ctx.operations):
        if not isinstance(op, dict):
            violations.append(_rule_violation("lowering.operation.object", field=f"operations[{idx}]", description="operation must be an object", location=f"operations[{idx}]"))
            continue
        op_name = op.get("op")
        if op_name not in _AQO_ALLOWED_OPS:
            violations.append(_rule_violation("lowering.opcode.supported", field=f"operations[{idx}].op", description="unsupported opcode", location=f"operations[{idx}].op"))
            continue
        q = op.get("q")
        if not isinstance(q, list) or not q or not all(isinstance(item, int) and item >= 0 for item in q):
            violations.append(_rule_violation("lowering.qubit_indices.valid", field=f"operations[{idx}].q", description="q must be a list of non-negative integers", location=f"operations[{idx}].q"))
            continue
        if any((qubits is not None and item >= qubits) for item in q):
            violations.append(_rule_violation("lowering.qubit_indices.in_range", field=f"operations[{idx}].q", description="qubit index out of range", location=f"operations[{idx}].q"))
        expected_arity = _AQO_ARITY[op_name]
        if op_name == "MEASURE":
            c = op.get("c")
            if not isinstance(c, list) or len(c) != len(q) or not all(isinstance(item, int) and item >= 0 for item in c):
                violations.append(_rule_violation("lowering.measure.classical_shape", field=f"operations[{idx}].c", description="MEASURE requires matching classical indices", location=f"operations[{idx}].c"))
            if any((qubits is not None and item >= qubits) for item in c or []):
                violations.append(_rule_violation("lowering.measure.classical_range", field=f"operations[{idx}].c", description="classical index out of range", location=f"operations[{idx}].c"))
            basis = op.get("basis")
            if basis is not None and basis not in _AQO_MEASUREMENT_BASIS:
                violations.append(_rule_violation("lowering.measure.basis_supported", field=f"operations[{idx}].basis", description="unsupported measurement basis", location=f"operations[{idx}].basis"))
            if "params" in op and op["params"]:
                violations.append(_rule_violation("lowering.measure.no_params", field=f"operations[{idx}].params", description="MEASURE must not include params", location=f"operations[{idx}].params"))
            continue
        if len(q) != expected_arity:
            violations.append(_rule_violation("lowering.operation.arity", field=f"operations[{idx}].q", description=f"{op_name} has invalid arity", location=f"operations[{idx}].q"))
        params = op.get("params")
        if op_name in _AQO_ROTATION_OPS:
            if not isinstance(params, dict) or set(params) != {"theta"}:
                violations.append(_rule_violation("lowering.rotation.theta_required", field=f"operations[{idx}].params", description=f"{op_name} requires theta parameter", location=f"operations[{idx}].params"))
            else:
                theta = params["theta"]
                if not isinstance(theta, (int, float, str)) or (isinstance(theta, float) and theta != theta):
                    violations.append(_rule_violation("lowering.rotation.theta_scalar", field=f"operations[{idx}].params.theta", description="theta must be integer, float, or string", location=f"operations[{idx}].params.theta"))
        else:
            if params:
                violations.append(_rule_violation("lowering.operation.no_params", field=f"operations[{idx}].params", description=f"{op_name} must not include params", location=f"operations[{idx}].params"))
        if op_name in _AQO_NON_PARAMETERIZED_OPS and "c" in op and op["c"]:
            violations.append(_rule_violation("lowering.operation.no_classical_register", field=f"operations[{idx}].c", description=f"{op_name} must not include c", location=f"operations[{idx}].c"))
    return tuple(violations)


def build_compiler_rule_catalog() -> RuleCatalog:
    return RuleCatalog(
        name="compiler_rule_catalog",
        version=RULE_VERSION,
        rules=(
            RuleSpec("syntax.ast.node_limit", "syntax", "AST node count must remain bounded", lambda ctx: _compiler_node_limit(ctx)),
            RuleSpec("syntax.ast.depth_limit", "syntax", "AST nesting depth must remain bounded", lambda ctx: _compiler_depth_limit(ctx)),
            RuleSpec("syntax.entrypoint.single", "syntax", "exactly one @hybrid_program entrypoint is required", lambda ctx: _compiler_entrypoint_rule(ctx)),
            RuleSpec("policy.import.allowed", "policy", "imports must remain inside the Eigen-Lang allowlist", lambda ctx: _compiler_forbidden_imports(ctx)),
            RuleSpec("policy.call.allowed", "policy", "forbidden runtime calls must be rejected", lambda ctx: _compiler_forbidden_calls(ctx)),
            RuleSpec("syntax.control_flow.static", "syntax", "runtime control flow is not allowed in Eigen-Lang", lambda ctx: _compiler_dynamic_control_flow(ctx)),
            RuleSpec("semantic.param.default.literal", "semantic", "Param defaults must be literal scalars", lambda ctx: _compiler_param_defaults(ctx)),
            RuleSpec("lowering.operation.arity", "lowering", "lowering must preserve opcode arity", lambda ctx: _compiler_lowering_rules(ctx)),
            RuleSpec("lowering.measure.classical_shape", "lowering", "measurement lowering must produce matching classical indices", lambda ctx: _compiler_lowering_rules(ctx)),
            RuleSpec("lowering.rotation.theta_required", "lowering", "rotation lowering must include theta", lambda ctx: _compiler_lowering_rules(ctx)),
        ),
    )


def evaluate_compiler_rules(
    *,
    source: bytes,
    tree: ast.AST,
    options: dict[str, str],
    request_context: dict[str, str],
    params: dict[str, dict[str, object]] | None = None,
    operations: list[dict[str, object]] | None = None,
    qubits: int | None = None,
    source_ref: str | None = None,
    source_precedence: str = "source",
    source_digest: str = "",
    categories: Iterable[str] | None = None,
) -> tuple[RuleResult, ...]:
    ctx = _CompilerSemanticContext(
        tree=tree,
        source=source,
        options=options,
        request_context=request_context,
        params=params,
        operations=operations,
        qubits=qubits,
        source_ref=source_ref,
        source_precedence=source_precedence,
        source_digest=source_digest,
    )
    return build_compiler_rule_catalog().evaluate(ctx, categories=categories)


def validate_compile_circuit(req) -> list[FieldViolation]:
    ctx = _RequestValidationContext(request=req)
    return list(build_request_rule_catalog().violations(ctx))


def validate_compile_job(req) -> list[FieldViolation]:
    violations: list[FieldViolation] = []

    if not req.job_id:
        violations.append(
            _rule_violation(
                "request.syntax.job_id_present",
                field="job_id",
                description="field is required",
                location="job_id",
            )
        )

    violations.extend(validate_compile_circuit(req))
    return violations
