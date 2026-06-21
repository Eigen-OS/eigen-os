from eigen_lang import (
    ClassicalRegister,
    QubitRegister,
    cnot,
    hybrid_program,
    ry,
    rz,
)


@hybrid_program(
    compiler="eigen",
    target="deterministic-runtime",
    shots=8192,
    optimization_level=2,
    seed=12345,
    metadata={
        "example": "forensic-replay",
        "domain": "audit",
        "source_job_id": "job-8cc4447b4a304c61",
        "trace_id": "trace-vqe-2026-06-18",
    },
)
def main():
    """A replay-oriented workload for investigation and audit of a previous run."""
    qreg = QubitRegister(2)
    creg = ClassicalRegister(2)

    # This stays deterministic so the same source bundle can be audited and
    # replayed without introducing hidden adaptive behavior.
    ry(0, theta=0.10)
    rz(1, theta=-0.20)
    cnot(0, 1)
    ry(0, theta=0.05)
    rz(1, theta=0.02)

    return {
        "qubits": qreg.size,
        "classical_bits": creg.size,
        "source_job_id": "job-8cc4447b4a304c61",
        "trace_id": "trace-vqe-2026-06-18",
        "mode": "replay",
    }
