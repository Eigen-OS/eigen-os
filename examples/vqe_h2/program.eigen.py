from eigen_lang import (
    ClassicalRegister,
    ExpectationValue,
    Observable,
    Param,
    QubitRegister,
    cnot,
    hybrid_program,
    minimize,
    ry,
    rz,
)


@hybrid_program(
    target="simulator",
    shots=8192,
    optimization_level=3,
    seed=7,
    noise_model="depolarizing:0.001",
    metadata={
        "example": "h2-vqe-scientific",
        "molecule": "H2",
        "basis": "sto-3g",
        "ansatz": "two-layer-entangling",
        "optimizer": "COBYLA",
        "max_iters": 60,
    },
)


def vqe_h2():
    """Reproducible H2 VQE benchmark for the local simulator.

    TThe example stays entirely within the Eigen-Lang surface while returning
    enough structured metadata to support regression testing, comparisons
    across compiler/runtime versions, and simple scientific reporting.
    """
    theta = Param("theta", 0.10)
    phi = Param("phi", -0.20)
    lam = Param("lambda", 0.05)
    delta = Param("delta", 0.02)

    # Make the resource footprint explicit.
    qreg = QubitRegister(2)
    creg = ClassicalRegister(2)

    # Two-layer entangling ansatz gives a slightly richer optimization surface
    # than the original single-layer demo.
    ry(0, theta=theta)
    ry(1, theta=phi)
    cnot(0, 1)
    rz(0, theta=lam)
    rz(1, theta=delta)
    cnot(0, 1)
    ry(0, theta=delta)
    ry(1, theta=lam)

    # Declare the measurement objective explicitly instead of hiding it behind
    # a demo-only string contract.
    observable = Observable(Z=0, X=1)
    energy = ExpectationValue("ansatz_h2", observable=observable)

    optimum = minimize(
        energy,
        [0.10, -0.20, 0.05, 0.02],
        method="COBYLA",
        max_iters=60,
    )

    return {
        "energy": optimum.fun,
        "parameters": optimum.x,
        "method": optimum.method,
        "objective": optimum.objective,
        "observable_terms": observable.terms,
        "qubits": qreg.size,
        "classical_bits": creg.size,
        "optimizer_metadata": optimum.metadata,
    }
