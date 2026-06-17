"""Declarative Eigen-Lang runtime surface.

This package provides the stable import surface used by Eigen-Lang source files.
The compiler parses source text statically; these helpers are intentionally
lightweight and side-effect free so examples and interactive tooling can import
and compose them safely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

__all__ = [
    "ClassicalRegister",
    "DatasetRef",
    "ExpectationValue",
    "Observable",
    "Operation",
    "OptimizationResult",
    "Param",
    "ProgramMetadata",
    "QubitRegister",
    "cx",
    "cnot",
    "h",
    "hybrid_program",
    "load_dataset",
    "measure",
    "minimize",
    "reset",
    "rx",
    "ry",
    "rz",
    "s",
    "swap",
    "t",
    "x",
    "y",
    "z",
]


@dataclass(frozen=True)
class ProgramMetadata:
    """Metadata attached by the @hybrid_program decorator."""

    compiler: str | None = None
    target: str | None = None
    shots: int | None = None
    optimization_level: int | None = None
    seed: int | None = None
    noise_model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Param:
    name: str
    default: Any | None = None

    def __iter__(self):
        yield self.name
        yield self.default


@dataclass(frozen=True)
class Observable:
    terms: dict[str, Any] = field(default_factory=dict)

    def __init__(self, **terms: Any):
        object.__setattr__(self, "terms", dict(terms))


@dataclass(frozen=True)
class ExpectationValue:
    observable: Any | None = None
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)

    def __init__(self, *args: Any, **kwargs: Any):
        observable = kwargs.pop("observable", None)
        object.__setattr__(self, "observable", observable)
        object.__setattr__(self, "args", tuple(args))
        object.__setattr__(self, "kwargs", dict(kwargs))


@dataclass(frozen=True)
class QubitRegister:
    size: int


@dataclass(frozen=True)
class ClassicalRegister:
    size: int


@dataclass(frozen=True)
class DatasetRef:
    source: str
    format: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Operation:
    op: str
    q: tuple[int, ...]
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OptimizationResult:
    fun: float = 0.0
    x: tuple[Any, ...] = field(default_factory=tuple)
    method: str = "COBYLA"
    objective: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def hybrid_program(
    _func: Callable[..., Any] | None = None,
    *,
    compiler: str | None = None,
    target: str | None = None,
    shots: int | None = None,
    optimization_level: int | None = None,
    seed: int | None = None,
    noise_model: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    **extra: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]] | Callable[..., Any]:
    """Mark a function as an Eigen-Lang entrypoint.

    The decorator is intentionally non-invasive: it attaches descriptive
    metadata and returns the original function unchanged.
    """

    def _decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        program_metadata = ProgramMetadata(
            compiler=compiler,
            target=target,
            shots=shots,
            optimization_level=optimization_level,
            seed=seed,
            noise_model=noise_model,
            metadata={**dict(metadata or {}), **dict(extra)},
        )
        setattr(func, "__eigen_lang_program__", program_metadata)
        setattr(func, "__eigen_lang_entrypoint__", True)
        return func

    if callable(_func):
        return _decorate(_func)
    return _decorate


def _gate(name: str, qubits: Sequence[int], **params: Any) -> Operation:
    return Operation(op=name, q=tuple(int(q) for q in qubits), params=dict(params))


def rx(qubit: int, theta: Any = None, **params: Any) -> Operation:
    if theta is not None and "theta" not in params:
        params["theta"] = theta
    return _gate("RX", (qubit,), **params)


def ry(qubit: int, theta: Any = None, **params: Any) -> Operation:
    if theta is not None and "theta" not in params:
        params["theta"] = theta
    return _gate("RY", (qubit,), **params)


def rz(qubit: int, theta: Any = None, **params: Any) -> Operation:
    if theta is not None and "theta" not in params:
        params["theta"] = theta
    return _gate("RZ", (qubit,), **params)


def x(qubit: int) -> Operation:
    return _gate("X", (qubit,))


def y(qubit: int) -> Operation:
    return _gate("Y", (qubit,))


def z(qubit: int) -> Operation:
    return _gate("Z", (qubit,))


def h(qubit: int) -> Operation:
    return _gate("H", (qubit,))


def s(qubit: int) -> Operation:
    return _gate("S", (qubit,))


def t(qubit: int) -> Operation:
    return _gate("T", (qubit,))


def cx(control: int, target: int) -> Operation:
    return _gate("CX", (control, target))


def cnot(control: int, target: int) -> Operation:
    return cx(control, target)


def swap(a: int, b: int) -> Operation:
    return _gate("SWAP", (a, b))


def measure(*qubits: int, basis: str = "Z", c: Sequence[int] | None = None) -> Operation:
    params: dict[str, Any] = {"basis": basis}
    if c is not None:
        params["c"] = tuple(int(idx) for idx in c)
    return _gate("MEASURE", qubits, **params)


def reset(qubit: int) -> Operation:
    return _gate("RESET", (qubit,))


def load_dataset(source: str, *, format: str | None = None, **metadata: Any) -> DatasetRef:
    return DatasetRef(source=source, format=format, metadata=dict(metadata))


def minimize(
    objective: Any,
    initial_params: Sequence[Any],
    *,
    method: str = "COBYLA",
    **metadata: Any,
) -> OptimizationResult:
    return OptimizationResult(
        fun=0.0,
        x=tuple(initial_params),
        method=method,
        objective=objective,
        metadata=dict(metadata),
    )
