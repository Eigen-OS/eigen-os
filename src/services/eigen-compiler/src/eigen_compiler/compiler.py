"""AST-only Eigen-Lang -> AQO JSON compiler for MVP RPC scaffolding."""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class CompilationResult:
    aqo_json: bytes
    metadata: dict[str, str]


@dataclass(frozen=True)
class CompilerViolation:
    field: str
    description: str


class CompilationValidationError(ValueError):
    def __init__(self, violations: list[CompilerViolation]):
        super().__init__("compilation validation failed")
        self.violations = violations


MAX_SOURCE_BYTES = 256 * 1024
MAX_AST_NODES = 50_000
MAX_AST_DEPTH = 200
MAX_LITERAL_CONTAINER_SIZE = 2048

_ALLOWED_MODULES = ("eigen_lang",)
_FORBIDDEN_CALLS = {
    "exec",
    "eval",
    "compile",
    "open",
    "input",
    "__import__",
    "system",
    "popen",
}
_ALLOWED_AST_NODES = {
    ast.Module,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Return,
    ast.Import,
    ast.ImportFrom,
    ast.Assign,
    ast.AnnAssign,
    ast.Expr,
    ast.Name,
    ast.Constant,
    ast.Call,
    ast.Dict,
    ast.List,
    ast.Tuple,
    ast.BinOp,
    ast.UnaryOp,
    ast.Load,
    ast.Store,
    ast.keyword,
    ast.Subscript,
    ast.Attribute,
    ast.alias,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
}


class _EntrypointCompiler:
    def __init__(self, *, source: bytes, source_ref: str | None):
        self._source = source
        self._source_ref = source_ref
        self._violations: list[CompilerViolation] = []
        self._qregs: dict[str, int] = {}
        self._cregs: dict[str, int] = {}
        self._operations: list[dict[str, object]] = []

    def compile(self) -> CompilationResult:
        if len(self._source) > MAX_SOURCE_BYTES:
            self._error("source", f"source exceeds max bytes ({MAX_SOURCE_BYTES})")
            raise CompilationValidationError(self._violations)

        try:
            source_text = self._source.decode("utf-8")
        except UnicodeDecodeError:
            self._error("source", "source must be valid UTF-8")
            raise CompilationValidationError(self._violations)

        try:
            tree = ast.parse(source_text)
        except SyntaxError as exc:
            lineno = exc.lineno or 1
            self._error("source", f"syntax error at line {lineno}: {exc.msg}")
            raise CompilationValidationError(self._violations)

        self._check_tree_limits(tree)
        self._validate_node_allowlist(tree)
        entrypoint = self._find_entrypoint(tree)
        if entrypoint is None:
            self._raise_if_any_violations()
            self._error("entrypoint", "exactly one @hybrid_program entrypoint is required")
            raise CompilationValidationError(self._violations)

        self._compile_entrypoint(entrypoint)
        self._raise_if_any_violations()

        qubits = max(self._qregs.values()) if self._qregs else 0
        aqo = {
            "version": "0.1",
            "qubits": qubits,
            "operations": self._operations,
        }
        aqo_bytes = json.dumps(aqo, separators=(",", ":"), sort_keys=True).encode("utf-8")

        digest = hashlib.sha256(self._source).hexdigest() if self._source else ""
        metadata = {
            "compiler": "eigen-compiler",
            "aqo_version": "0.1",
            "input_bytes": str(len(self._source)),
            "source_sha256": digest,
        }
        if self._source_ref:
            metadata["source_ref"] = self._source_ref

        return CompilationResult(aqo_json=aqo_bytes, metadata=metadata)

    def _compile_entrypoint(self, fn: ast.FunctionDef) -> None:
        for stmt in fn.body:
            if isinstance(stmt, ast.Assign):
                self._handle_assign(stmt)
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                self._handle_operation_call(stmt.value)
            elif isinstance(stmt, ast.Return):
                continue
            else:
                self._error("source", f"unsupported statement in entrypoint: {type(stmt).__name__}")

    def _handle_assign(self, stmt: ast.Assign) -> None:
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            self._error("source", "only simple assignment targets are allowed")
            return

        target = stmt.targets[0].id
        if not isinstance(stmt.value, ast.Call):
            self._error("source", "assignment value must be a constructor call")
            return

        call_name = self._symbol(self._call_name(stmt.value.func))
        if call_name == "QubitRegister":
            size = self._extract_positive_int(stmt.value, "QubitRegister")
            if size is not None:
                self._qregs[target] = size
            return
        if call_name == "ClassicalRegister":
            size = self._extract_positive_int(stmt.value, "ClassicalRegister")
            if size is not None:
                self._cregs[target] = size
            return

        self._error("source", f"unsupported constructor assignment: {call_name}")

    def _handle_operation_call(self, call: ast.Call) -> None:
        call_name = self._symbol(self._call_name(call.func))
        if call_name in _FORBIDDEN_CALLS:
            self._error("source", f"forbidden call: {call_name}")
            return

        if call_name in {"RX", "RY", "RZ"}:
            if len(call.args) != 2:
                self._error("source", f"{call_name} expects 2 positional args")
                return
            theta = self._extract_numeric(call.args[0], field="source")
            q_index = self._extract_qubit_index(call.args[1])
            if theta is None or q_index is None:
                return
            self._operations.append({"op": call_name, "q": [q_index], "params": {"theta": theta}})
            return

        if call_name == "CX":
            if len(call.args) != 2:
                self._error("source", "CX expects 2 positional args")
                return
            q0 = self._extract_qubit_index(call.args[0])
            q1 = self._extract_qubit_index(call.args[1])
            if q0 is None or q1 is None:
                return
            self._operations.append({"op": "CX", "q": [q0, q1]})
            return

        if call_name == "MEASURE":
            if len(call.args) != 2:
                self._error("source", "MEASURE expects 2 positional args")
                return
            q_idx = self._extract_qubit_index(call.args[0])
            c_idx = self._extract_classical_index(call.args[1])
            if q_idx is None or c_idx is None:
                return
            self._operations.append({"op": "MEASURE", "q": [q_idx], "c": [c_idx]})
            return

        self._error("source", f"unsupported operation: {call_name}")

    def _extract_numeric(self, node: ast.AST, *, field: str) -> float | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            inner = self._extract_numeric(node.operand, field=field)
            if inner is None:
                return None
            return inner if isinstance(node.op, ast.UAdd) else -inner
        self._error(field, "rotation theta must be numeric literal")
        return None

    def _extract_positive_int(self, call: ast.Call, ctor_name: str) -> int | None:
        if len(call.args) != 1:
            self._error("source", f"{ctor_name} expects exactly one positional argument")
            return None
        arg = call.args[0]
        if not isinstance(arg, ast.Constant) or not isinstance(arg.value, int):
            self._error("source", f"{ctor_name} size must be integer literal")
            return None
        if arg.value <= 0:
            self._error("source", f"{ctor_name} size must be > 0")
            return None
        return int(arg.value)

    def _extract_qubit_index(self, node: ast.AST) -> int | None:
        return self._extract_register_index(node, self._qregs, "qubit")

    def _extract_classical_index(self, node: ast.AST) -> int | None:
        return self._extract_register_index(node, self._cregs, "classical")

    def _extract_register_index(
        self,
        node: ast.AST,
        registers: dict[str, int],
        register_kind: str,
    ) -> int | None:
        if not isinstance(node, ast.Subscript) or not isinstance(node.value, ast.Name):
            self._error("source", f"{register_kind} operand must be register[index]")
            return None

        reg_name = node.value.id
        size = registers.get(reg_name)
        if size is None:
            self._error("source", f"unknown {register_kind} register '{reg_name}'")
            return None

        index_node = node.slice
        if not isinstance(index_node, ast.Constant) or not isinstance(index_node.value, int):
            self._error("source", f"{register_kind} index must be integer literal")
            return None

        index = int(index_node.value)
        if index < 0 or index >= size:
            self._error("source", f"{register_kind} index {index} out of bounds for '{reg_name}'")
            return None
        return index

    def _find_entrypoint(self, tree: ast.Module) -> ast.FunctionDef | None:
        entrypoints: list[ast.FunctionDef] = []
        for stmt in tree.body:
            if isinstance(stmt, ast.FunctionDef) and any(
                self._is_hybrid_program_decorator(d) for d in stmt.decorator_list
            ):
                entrypoints.append(stmt)

        if len(entrypoints) != 1:
            self._error("entrypoint", "exactly one @hybrid_program entrypoint is required")
            return None
        return entrypoints[0]

    @staticmethod
    def _is_hybrid_program_decorator(decorator: ast.expr) -> bool:
        if isinstance(decorator, ast.Name):
            return decorator.id == "hybrid_program"
        if isinstance(decorator, ast.Call):
            return _EntrypointCompiler._is_hybrid_program_decorator(decorator.func)
        if isinstance(decorator, ast.Attribute):
            return decorator.attr == "hybrid_program"
        return False

    def _check_tree_limits(self, tree: ast.AST) -> None:
        node_count = 0
        max_depth = 0
        stack: list[tuple[ast.AST, int]] = [(tree, 1)]
        while stack:
            node, depth = stack.pop()
            node_count += 1
            max_depth = max(max_depth, depth)
            for child in ast.iter_child_nodes(node):
                stack.append((child, depth + 1))

        if node_count > MAX_AST_NODES:
            self._error("source", f"AST nodes exceed limit ({MAX_AST_NODES})")
        if max_depth > MAX_AST_DEPTH:
            self._error("source", f"AST depth exceeds limit ({MAX_AST_DEPTH})")

    def _validate_node_allowlist(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if type(node) not in _ALLOWED_AST_NODES:
                self._error("source", f"forbidden AST node: {type(node).__name__}")
                continue

            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if not module.startswith(_ALLOWED_MODULES):
                    self._error("source", "imports are restricted to eigen_lang")

            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not alias.name.startswith(_ALLOWED_MODULES):
                        self._error("source", "imports are restricted to eigen_lang")

            if isinstance(node, ast.Call):
                call_name = self._symbol(self._call_name(node.func))
                if call_name in _FORBIDDEN_CALLS:
                    self._error("source", f"forbidden call: {call_name}")

            if isinstance(node, (ast.List, ast.Tuple, ast.Dict)):
                size = len(node.keys) if isinstance(node, ast.Dict) else len(node.elts)
                if size > MAX_LITERAL_CONTAINER_SIZE:
                    self._error("source", f"literal container exceeds limit ({MAX_LITERAL_CONTAINER_SIZE})")


    @staticmethod
    def _symbol(name: str) -> str:
        return name.rsplit(".", 1)[-1]

    @staticmethod
    def _call_name(func: ast.AST) -> str:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            left = _EntrypointCompiler._call_name(func.value)
            return f"{left}.{func.attr}" if left else func.attr
        return "<unknown>"

    def _error(self, field: str, description: str) -> None:
        self._violations.append(CompilerViolation(field=field, description=description))

    def _raise_if_any_violations(self) -> None:
        if self._violations:
            raise CompilationValidationError(self._violations)
        

def compile_eigen_lang(source: bytes, *, source_ref: str | None = None) -> CompilationResult:
    """Compile source bytes into AQO v0.1 payload using AST-only parsing."""

    compiler = _EntrypointCompiler(source=source, source_ref=source_ref)
    return compiler.compile()

