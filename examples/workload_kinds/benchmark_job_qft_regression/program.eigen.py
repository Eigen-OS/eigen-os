from eigen_lang import (
    ClassicalRegister,
    QubitRegister,
    cp,
    h,
    hybrid_program,
    pi,
    swap,
)


@hybrid_program(
    compiler="eigen",
    target="simulator",
    shots=16384,
    optimization_level=1,
    seed=42,
)
def main(n: int = 16):
    """Canonical n-qubit Quantum Fourier Transform.

    |0...0> -> (1/sqrt(2^n)) * sum_x |x>

    Uniform distribution over 2^n basis states is the only assertion
    that matters for regression: nonzero_bitstrings >> n and no
    dominant_bitstring with count greater than a few units.
    """
    q = QubitRegister(n)
    c = ClassicalRegister(n)

    for j in range(n):
        h(j)
        for k in range(j + 1, n):
            cp(control=k, target=j, theta=2 * pi / (2 ** (k - j + 1)))

    for i in range(n // 2):
        swap(i, n - 1 - i)

    return {"qubits": q.size, "classical_bits": c.size}
    