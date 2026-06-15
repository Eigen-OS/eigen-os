from eigen_lang import ExpectationValue, Param, hybrid_program, minimize, cnot, ry, rz


@hybrid_program(target="simulator", shots=4096, optimization_level=3)
def vqe_h2():
    """Beautiful H2 VQE demo for the local simulator.

    The example keeps the circuit compact, uses only Eigen-Lang primitives,
    and leaves the molecular Hamiltonian lookup to the simulator/backend layer.
    """
    theta = Param("theta", 0.10)
    phi = Param("phi", -0.20)
    lam = Param("lambda", 0.05)

    # Compact 2-qubit ansatz with a clear entangling core.
    ry(0, theta=theta)
    ry(1, theta=phi)
    cnot(0, 1)
    rz(1, theta=lam)
    cnot(0, 1)

    # Backend-side observable/hamiltonian labels keep the source declarative.
    energy = ExpectationValue("ansatz_h2", "H2_sto-3g")

    # COBYLA is a good default for this small demonstration circuit.
    result = minimize(energy, [0.10, -0.20, 0.05], method="COBYLA")
    return result.fun
