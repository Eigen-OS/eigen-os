from eigen_lang import Param, ExpectationValue, hybrid_program, minimize


@hybrid_program(target="sim", shots=1000)
def vqe_program():
    theta = Param("theta")
    ry(0, theta=theta)
    cost = ExpectationValue("ansatz", "observable")
    minimize(cost, [0.1])
