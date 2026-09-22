"""QFT compiler compatibility helpers.

The public compiler imports this module when lowering Eigen-Lang programs.  The
helpers deliberately evaluate only a closed AST subset: literals, ``pi``,
integer arithmetic, and bounded ``range`` calls.  They never execute source.
"""
from __future__ import annotations

import ast
import math
from typing import Any


def static_value(node: ast.AST, env: dict[str, Any] | None = None) -> Any:
    env = env or {}
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return math.pi if node.id == "pi" else env.get(node.id)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = static_value(node.operand, env)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value if isinstance(node.op, ast.UAdd) else -value
        return None
    if isinstance(node, ast.BinOp):
        left, right = static_value(node.left, env), static_value(node.right, env)
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            return None
        try:
            if isinstance(node.op, ast.Add): return left + right
            if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node.op, ast.Mult): return left * right
            if isinstance(node.op, ast.Div): return left / right
            if isinstance(node.op, ast.FloorDiv): return left // right
            if isinstance(node.op, ast.Pow): return left ** right
            if isinstance(node.op, ast.Mod): return left % right
        except (TypeError, ValueError, ZeroDivisionError, OverflowError):
            return None
    return None


def static_range(node: ast.AST, env: dict[str, Any] | None = None) -> list[int] | None:
    env = env or {}
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "range":
        return None
    values = [static_value(arg, env) for arg in node.args]
    if not 1 <= len(values) <= 3 or not all(isinstance(value, int) for value in values):
        return None
    try:
        return list(range(*values))
    except (TypeError, ValueError):
        return None


def resolve_static_expr(node: ast.AST, env: dict[str, Any] | None = None) -> Any:
    """Resolve literal arithmetic / pi expressions without evaluation of code."""
    env = env or {}
    value = static_value(node, env)
    if value is not None:
        return value
    if isinstance(node, ast.Name):
        if node.id == "pi":
            return math.pi
        return env.get(node.id)
    return None


def expand_static_for_loops(tree: ast.AST, env: dict[str, Any] | None = None) -> list[ast.stmt]:
    env = env or {}
    out: list[ast.stmt] = []
    for stmt in tree.body:
        if isinstance(stmt, ast.For):
            target = stmt.target
            if not isinstance(target, ast.Name):
                raise ValueError("for-loop target must be a simple name")
            rng = static_range(stmt.iter, env)
            if rng is None:
                raise ValueError("for-loop must be over a statically bounded range()")
            for idx in rng:
                next_env = dict(env)
                next_env[target.id] = idx
                out.extend(expand_static_for_loops(ast.Module(body=stmt.body, type_ignores=[]), next_env))
        else:
            out.append(stmt)
    return out
