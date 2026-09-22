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
    compiler="eigen",
    target="simulator",
    shots=8192,
    optimization_level=3,
    seed=7,
    noise_model="depolarizing:0.001",
    metadata={
        "example": "hybrid-vqe-chemistry",
        "domain": "quantum-chemistry",
        "molecule": "H2",
        "basis": "sto-3g",
        "optimizer": "COBYLA",
        "max_iters": 60,
    },
)
def main():
    """A chemistry-style hybrid workflow with a classical optimization loop."""
    theta = Param("theta", 0.10)
    phi = Param("phi", -0.20)
    lam = Param("lambda", 0.05)
    delta = Param("delta", 0.02)

    qreg = QubitRegister(2)
    creg = ClassicalRegister(2)

    ry(0, theta=theta)
    ry(1, theta=phi)
    cnot(0, 1)
    rz(0, theta=lam)
    rz(1, theta=delta)
    cnot(0, 1)
    ry(0, theta=delta)
    ry(1, theta=lam)

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
