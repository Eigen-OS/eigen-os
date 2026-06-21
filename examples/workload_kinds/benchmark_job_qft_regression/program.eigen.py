from eigen_lang import (
    ClassicalRegister,
    QubitRegister,
    cnot,
    hybrid_program,
    rx,
    rz,
)


@hybrid_program(
    compiler="eigen",
    target="simulator",
    shots=16384,
    optimization_level=1,
    seed=42,
    metadata={
        "example": "qft-benchmark-regression",
        "domain": "benchmarking",
        "benchmark": "qft-depth-regression",
        "seed": 42,
    },
)
def main():
    """A reproducible benchmark workload for compiler/runtime regression checks."""
    qreg = QubitRegister(16)
    creg = ClassicalRegister(16)

    rx(0, theta=0.13)
    rz(0, theta=0.07)
    rx(1, theta=0.13)
    rz(1, theta=0.07)
    rx(2, theta=0.13)
    rz(2, theta=0.07)
    rx(3, theta=0.13)
    rz(3, theta=0.07)
    rx(4, theta=0.13)
    rz(4, theta=0.07)
    rx(5, theta=0.13)
    rz(5, theta=0.07)
    rx(6, theta=0.13)
    rz(6, theta=0.07)
    rx(7, theta=0.13)
    rz(7, theta=0.07)
    rx(8, theta=0.13)
    rz(8, theta=0.07)
    rx(9, theta=0.13)
    rz(9, theta=0.07)
    rx(10, theta=0.13)
    rz(10, theta=0.07)
    rx(11, theta=0.13)
    rz(11, theta=0.07)
    rx(12, theta=0.13)
    rz(12, theta=0.07)
    rx(13, theta=0.13)
    rz(13, theta=0.07)
    rx(14, theta=0.13)
    rz(14, theta=0.07)
    rx(15, theta=0.13)
    rz(15, theta=0.07)

    cnot(0, 1)
    cnot(1, 2)
    cnot(2, 3)
    cnot(3, 4)
    cnot(4, 5)
    cnot(5, 6)
    cnot(6, 7)
    cnot(7, 8)
    cnot(8, 9)
    cnot(9, 10)
    cnot(10, 11)
    cnot(11, 12)
    cnot(12, 13)
    cnot(13, 14)
    cnot(14, 15)

    return {
        "qubits": qreg.size,
        "classical_bits": creg.size,
        "benchmark": "qft-depth-regression",
        "seed": 42,
    }
