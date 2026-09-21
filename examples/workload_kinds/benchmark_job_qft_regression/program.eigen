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
    metadata={
        "example": "qft-native",
        "domain": "quantum-algorithms",
        "algorithm": "qft",
    },
)
def main(n: int = 16):
    """Canonical n-qubit Quantum Fourier Transform.

    |0...0>  ->  (1/sqrt(2^n)) * sum_x |x>

    Circuit:
      1. For each j: H(j), then controlled-phase CP(k, j, 2*pi / 2^(k-j+1))
         for k = j+1 .. n-1.
      2. Reverse qubit order with n/2 SWAPs.

    On the ideal simulator this yields a uniform distribution over
    2^n basis states; nonzero_bitstrings must approach 2^n * (1 - e^-lambda)
    with lambda = shots / 2^n.
    """
    q = QubitRegister(n)
    c = ClassicalRegister(n)

    for j in range(n):
        h(j)
        for k in range(j + 1, n):
            angle = 2.0 * pi / (2 ** (k - j + 1))
            cp(control=k, target=j, theta=angle)

    for i in range(n // 2):
        swap(i, n - 1 - i)

    return {
        "qubits": q.size,
        "classical_bits": c.size,
        "algorithm": "qft",
        "n": n,
    }
    