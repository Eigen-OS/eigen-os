from eigen_lang import hybrid_program


@hybrid_program(target="sim", shots=1000)
def main():
    ry(0, theta=1.570796)
