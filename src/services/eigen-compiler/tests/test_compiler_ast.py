from __future__ import annotations

import hashlib
import json

import pytest

from eigen_compiler.compiler import CompilationValidationError, compile_eigen_lang


def _compile_json(source: str) -> dict:
    result = compile_eigen_lang(source.encode("utf-8"))
    return json.loads(result.aqo_json)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            """
from eigen_lang import hybrid_program, QubitRegister, ClassicalRegister, RY, MEASURE

@hybrid_program

def main():
    q = QubitRegister(1)
    c = ClassicalRegister(1)
    RY(1.570796, q[0])
    MEASURE(q[0], c[0])
""",
            {
                "version": "0.1",
                "qubits": 1,
                "operations": [
                    {"op": "RY", "q": [0], "params": {"theta": 1.570796}},
                    {"op": "MEASURE", "q": [0], "c": [0]},
                ],
            },
        ),
        (
            """
from eigen_lang import hybrid_program, QubitRegister, ClassicalRegister, RX, RY, RZ, MEASURE

@hybrid_program()
def main():
    q = QubitRegister(1)
    c = ClassicalRegister(1)
    RX(0.1, q[0])
    RY(0.2, q[0])
    RZ(0.3, q[0])
    MEASURE(q[0], c[0])
""",
            {
                "version": "0.1",
                "qubits": 1,
                "operations": [
                    {"op": "RX", "q": [0], "params": {"theta": 0.1}},
                    {"op": "RY", "q": [0], "params": {"theta": 0.2}},
                    {"op": "RZ", "q": [0], "params": {"theta": 0.3}},
                    {"op": "MEASURE", "q": [0], "c": [0]},
                ],
            },
        ),
        (
            """
from eigen_lang import hybrid_program, QubitRegister, ClassicalRegister, CX, MEASURE

@hybrid_program(target='sim')
def main():
    q = QubitRegister(2)
    c = ClassicalRegister(2)
    CX(q[0], q[1])
    MEASURE(q[0], c[0])
    MEASURE(q[1], c[1])
""",
            {
                "version": "0.1",
                "qubits": 2,
                "operations": [
                    {"op": "CX", "q": [0, 1]},
                    {"op": "MEASURE", "q": [0], "c": [0]},
                    {"op": "MEASURE", "q": [1], "c": [1]},
                ],
            },
        ),
        (
            """
from eigen_lang import hybrid_program, QubitRegister, ClassicalRegister, RX, CX, MEASURE

@hybrid_program
def main():
    q = QubitRegister(3)
    c = ClassicalRegister(3)
    RX(-1.25, q[2])
    CX(q[2], q[1])
    MEASURE(q[2], c[2])
""",
            {
                "version": "0.1",
                "qubits": 3,
                "operations": [
                    {"op": "RX", "q": [2], "params": {"theta": -1.25}},
                    {"op": "CX", "q": [2, 1]},
                    {"op": "MEASURE", "q": [2], "c": [2]},
                ],
            },
        ),
        (
            """
from eigen_lang import hybrid_program, QubitRegister, ClassicalRegister
import eigen_lang as el

@el.hybrid_program
def main():
    q = QubitRegister(1)
    c = ClassicalRegister(1)
    el.RZ(3.14159, q[0])
    el.MEASURE(q[0], c[0])
""",
            {
                "version": "0.1",
                "qubits": 1,
                "operations": [
                    {"op": "RZ", "q": [0], "params": {"theta": 3.14159}},
                    {"op": "MEASURE", "q": [0], "c": [0]},
                ],
            },
        ),
    ],
)
def test_golden_programs_to_aqo(source: str, expected: dict) -> None:
    assert _compile_json(source) == expected


def test_stable_serialization_and_metadata_hash() -> None:
    source = b"""
from eigen_lang import hybrid_program, QubitRegister, ClassicalRegister, RX, MEASURE

@hybrid_program
def main():
    q = QubitRegister(1)
    c = ClassicalRegister(1)
    RX(1.0, q[0])
    MEASURE(q[0], c[0])
"""

    r1 = compile_eigen_lang(source)
    r2 = compile_eigen_lang(source)

    assert r1.aqo_json == r2.aqo_json
    assert r1.metadata["source_sha256"] == hashlib.sha256(source).hexdigest()


def test_rejects_forbidden_constructs() -> None:
    source = b"""
from eigen_lang import hybrid_program, QubitRegister, ClassicalRegister

@hybrid_program
def main():
    q = QubitRegister(1)
    c = ClassicalRegister(1)
    eval('1+1')
"""

    with pytest.raises(CompilationValidationError) as exc:
        compile_eigen_lang(source)

    assert any(v.field == "source" for v in exc.value.violations)


def test_requires_exactly_one_entrypoint() -> None:
    source = b"""
from eigen_lang import hybrid_program

@hybrid_program
def main1():
    return None

@hybrid_program
def main2():
    return None
"""

    with pytest.raises(CompilationValidationError) as exc:
        compile_eigen_lang(source)

    assert any(v.field == "entrypoint" for v in exc.value.violations)
