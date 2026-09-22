from eigen_lang import (
    ClassicalRegister,
    ExpectationValue,
    Observable,
    Param,
    QubitRegister,
    cnot,
    hybrid_program,
    minimize,
    load_dataset,
    ry,
    rz,
)


@hybrid_program(
    compiler="eigen",
    target="simulator",
    shots=4096,
    optimization_level=3,
    seed=99,
    metadata={
        "example": "materials-pipeline",
        "domain": "materials-science",
        "pipeline_stage": "quantum_refine",
    },
)
def main():
    """A deterministic pipeline stage that consumes a prior artifact and emits a refined result."""
    features = load_dataset("qfs://stages/preprocess/features.parquet", format="parquet")

    theta = Param("theta", 0.21)
    phi = Param("phi", 0.33)

    qreg = QubitRegister(8)
    creg = ClassicalRegister(8)

    ry(0, theta=theta)
    rz(1, theta=phi)
    cnot(0, 1)
    ry(2, theta=0.19)
    cnot(2, 3)

    energy = ExpectationValue(Observable(Z=0, X=1))
    optimum = minimize(energy, [0.21, 0.33], method="COBYLA", max_iters=20)

    return {
        "features_ref": features,
        "optimized_energy": optimum.fun,
        "parameters": optimum.x,
        "qubits": qreg.size,
        "classical_bits": creg.size,
        "stage": "quantum_refine",
    }
