from __future__ import annotations

from eigen_lang import (
    ClassicalRegister,
    ExpectationValue,
    Observable,
    Param,
    QubitRegister,
    cnot,
    cx,
    hybrid_program,
    load_dataset,
    minimize,
)
from eigen_lang.optimizers import minimize as minimize_from_submodule


def test_eigen_lang_public_surface_and_aliases():
    assert cnot(0, 1).op == "CX"
    assert cx(0, 1).op == "CX"
    assert minimize_from_submodule is minimize

    param = Param("theta", 0.5)
    assert param.name == "theta"
    assert param.default == 0.5

    obs = Observable(Z=0, X=1)
    assert obs.terms == {"Z": 0, "X": 1}

    cost = ExpectationValue("ansatz", observable=obs)
    assert cost.observable == obs
    assert cost.args == ("ansatz",)

    qreg = QubitRegister(4)
    creg = ClassicalRegister(4)
    assert qreg.size == 4
    assert creg.size == 4

    dataset = load_dataset("qfs://datasets/demo.parquet", format="parquet")
    assert dataset.source.startswith("qfs://")
    assert dataset.format == "parquet"

    @hybrid_program(target="sim", shots=1024)
    def main():
        return 1

    assert getattr(main, "__eigen_lang_entrypoint__", False) is True
    assert main.__eigen_lang_program__.target == "sim"
    assert main.__eigen_lang_program__.shots == 1024
