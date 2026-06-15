from eigen_lang import (
    ClassicalRegister,
    ExpectationValue,
    Observable,
    Param,
    QubitRegister,
    hybrid_program,
    load_dataset,
    minimize,
    rx,
    ry,
    rz,
    cx,
)


@hybrid_program(
    compiler="eigen",
    target="simulator",
    shots=4096,
    optimization_level=3,
    seed=7,
    noise_model="depolarizing:0.001",
    metadata={
        "example": "eigen-lang-showcase",
        "molecule": "H2",
        "basis": "sto-3g",
        "optimizer": "COBYLA",
        "max_iters": 40,
    },
)
def main():
    """Broad Eigen-Lang showcase for the local simulator."""
    theta = Param("theta", 0.10)
    phi = Param("phi", 0.20)
    lam = Param("lambda", 0.05)

    # Declarative data / register surfaces from the reference docs.
    qreg = QubitRegister(4)
    creg = ClassicalRegister(4)
    dataset = load_dataset("qfs://datasets/h2/reference.parquet", format="parquet")

    # Fully supported circuit core that compiles to deterministic AQO.
    rx(0, theta=theta)
    ry(1, theta=phi)
    cx(0, 1)
    rz(1, theta=lam)
    cx(0, 1)

    hamiltonian = Observable(Z=0, X=1)
    energy = ExpectationValue(hamiltonian)

    result = minimize(energy, [0.10, 0.20, 0.05], method="COBYLA")
    return {
        "energy": result.fun,
        "dataset_ref": dataset,
        "qubits": qreg,
        "classical_bits": creg,
        "observable": hamiltonian,
    }
