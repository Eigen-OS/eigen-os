from eigen_lang import Param, ExpectationValue, hybrid_program, minimize, cnot, ry


@hybrid_program(target="sim", shots=1024)
def main():
    """Minimal 2-qubit VQE ansatz for local simulator runs."""
    theta = Param("theta")

    # Ansatz: prepare an entangled trial state controlled by one parameter.
    ry(0, theta=theta)
    cnot(0, 1)

    # Cost is measured against a 2-qubit observable declared in the backend context.
    # For a toy setup, this can represent terms similar to Z0 + Z1 + 0.5 * X0X1.
    energy = ExpectationValue("ansatz", "hamiltonian_2q")

    # Start near zero and let the classical optimizer descend.
    minimize(energy, [0.05])
