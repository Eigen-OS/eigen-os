from eigen_lang import (
    ClassicalRegister,
    QubitRegister,
    cnot,
    hybrid_program,
    rx,
    ry,
    rz,
)


@hybrid_program(
    compiler="eigen",
    target="simulator",
    shots=4096,
    optimization_level=2,
    seed=11,
    metadata={
        "example": "materials-state-preparation",
        "domain": "materials-science",
        "ansatz": "entangling-state-prep",
    },
)
def main():
    """A small state-preparation workload for materials / chemistry style demos.

    The program stays inside the deterministic circuit surface and is suitable
    for simulator runs, compile-time validation, and regression testing.
    """
    qreg = QubitRegister(6)
    creg = ClassicalRegister(6)

    # A layered preparation pattern gives the compiler enough structure to
    # demonstrate normalization, lowering, and AQO emission.
    rx(0, theta=0.31)
    ry(1, theta=0.17)
    cnot(0, 1)

    rz(2, theta=0.44)
    rx(3, theta=0.29)
    cnot(2, 3)

    ry(4, theta=0.12)
    rz(5, theta=0.21)
    cnot(4, 5)

    return {
        "qubits": qreg.size,
        "classical_bits": creg.size,
        "domain": "materials-science",
        "workload": "state-preparation",
    }
