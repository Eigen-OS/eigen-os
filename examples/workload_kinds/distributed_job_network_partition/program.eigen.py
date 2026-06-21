from eigen_lang import (
    ClassicalRegister,
    QubitRegister,
    cnot,
    hybrid_program,
    rx,
    ry,
    rz,
)


@hybrid_program(
    compiler="eigen",
    target="simulator",
    shots=2048,
    optimization_level=2,
    seed=19,
    metadata={
        "example": "distributed-network-partition",
        "domain": "telecom-network",
        "scenario": "split-brain-recovery",
        "partition_strategy": "isolate-heal",
        "cluster_id": "cluster:auto",
        "partitions": 8,
    },
)
def main():
    """A distributed workload that models split-brain isolation and recovery."""

    qreg = QubitRegister(16)
    creg = ClassicalRegister(16)

    # Phase 1: local work inside each partition.
    rx(0, theta=1.5707963267948966)
    ry(1, theta=1.5707963267948966)
    cnot(0, 1)
    rz(0, theta=0.00)
    rz(1, theta=-0.00)
    rx(1, theta=1.0471975511965976)
    ry(0, theta=0.7853981633974483)

    rx(2, theta=1.5707963267948966)
    ry(3, theta=1.5707963267948966)
    cnot(2, 3)
    rz(2, theta=0.17)
    rz(3, theta=-0.085)
    rx(3, theta=1.0471975511965976)
    ry(2, theta=0.7853981633974483)

    rx(4, theta=1.5707963267948966)
    ry(5, theta=1.5707963267948966)
    cnot(4, 5)
    rz(4, theta=0.31)
    rz(5, theta=-0.155)
    rx(5, theta=1.0471975511965976)
    ry(4, theta=0.7853981633974483)

    rx(6, theta=1.5707963267948966)
    ry(7, theta=1.5707963267948966)
    cnot(6, 7)
    rz(6, theta=0.49)
    rz(7, theta=-0.245)
    rx(7, theta=1.0471975511965976)
    ry(6, theta=0.7853981633974483)

    rx(8, theta=1.5707963267948966)
    ry(9, theta=1.5707963267948966)
    cnot(8, 9)
    rz(8, theta=0.67)
    rz(9, theta=-0.335)
    rx(9, theta=1.0471975511965976)
    ry(8, theta=0.7853981633974483)

    rx(10, theta=1.5707963267948966)
    ry(11, theta=1.5707963267948966)
    cnot(10, 11)
    rz(10, theta=0.83)
    rz(11, theta=-0.415)
    rx(11, theta=1.0471975511965976)
    ry(10, theta=0.7853981633974483)

    rx(12, theta=1.5707963267948966)
    ry(13, theta=1.5707963267948966)
    cnot(12, 13)
    rz(12, theta=1.01)
    rz(13, theta=-0.505)
    rx(13, theta=1.0471975511965976)
    ry(12, theta=0.7853981633974483)

    rx(14, theta=1.5707963267948966)
    ry(15, theta=1.5707963267948966)
    cnot(14, 15)
    rz(14, theta=1.19)
    rz(15, theta=-0.595)
    rx(15, theta=1.0471975511965976)
    ry(14, theta=0.7853981633974483)

    # Phase 2: degraded connectivity during partition.
    cnot(1, 2)
    rz(1, theta=0.117)
    ry(2, theta=0.2)

    cnot(3, 4)
    rz(3, theta=0.131)
    ry(4, theta=0.21)

    cnot(5, 6)
    rz(5, theta=0.145)
    ry(6, theta=0.22)

    cnot(7, 8)
    rz(7, theta=0.159)
    ry(8, theta=0.225)

    cnot(9, 10)
    rz(9, theta=0.173)
    ry(10, theta=0.24)

    cnot(11, 12)
    rz(11, theta=0.187)
    ry(12, theta=0.25)

    cnot(13, 14)
    rz(13, theta=0.201)
    ry(14, theta=0.26)

    # Phase 3: heal partition boundaries.
    cnot(0, 8)
    ry(0, theta=1.5707963267948966)
    rz(8, theta=0.22)
    cnot(8, 0)
    rx(8, theta=1.0471975511965976)

    cnot(2, 10)
    ry(2, theta=1.5707963267948966)
    rz(10, theta=0.24)
    cnot(10, 2)
    rx(10, theta=1.0471975511965976)

    cnot(4, 12)
    ry(4, theta=1.5707963267948966)
    rz(12, theta=0.26)
    cnot(12, 4)
    rx(12, theta=1.0471975511965976)

    cnot(6, 14)
    ry(6, theta=1.5707963267948966)
    rz(14, theta=0.28)
    cnot(14, 6)
    rx(14, theta=1.0471975511965976)

    cnot(1, 9)
    ry(1, theta=1.5707963267948966)
    rz(9, theta=0.23)
    cnot(9, 1)
    rx(9, theta=1.0471975511965976)

    cnot(3, 11)
    ry(3, theta=1.5707963267948966)
    rz(11, theta=0.25)
    cnot(11, 3)
    rx(11, theta=1.0471975511965976)

    cnot(5, 13)
    ry(5, theta=1.5707963267948966)
    rz(13, theta=0.27)
    cnot(13, 5)
    rx(13, theta=1.0471975511965976)

    cnot(7, 15)
    ry(7, theta=1.5707963267948966)
    rz(15, theta=0.29)
    cnot(15, 7)
    rx(15, theta=1.0471975511965976)

    # Phase 4: global reconciliation sweep.
    rz(0, theta=-0.315)
    rx(0, theta=1.5707963267948966)

    rz(1, theta=-0.105)
    ry(1, theta=1.0471975511965976)

    rz(2, theta=0.105)
    rx(2, theta=1.5707963267948966)

    rz(3, theta=0.315)
    ry(3, theta=1.0471975511965976)

    rz(4, theta=-0.315)
    rx(4, theta=1.5707963267948966)

    rz(5, theta=-0.105)
    ry(5, theta=1.0471975511965976)

    rz(6, theta=0.105)
    rx(6, theta=1.5707963267948966)

    rz(7, theta=0.315)
    ry(7, theta=1.0471975511965976)

    rz(8, theta=-0.315)
    rx(8, theta=1.5707963267948966)

    rz(9, theta=-0.105)
    ry(9, theta=1.0471975511965976)

    rz(10, theta=0.105)
    rx(10, theta=1.5707963267948966)

    rz(11, theta=0.315)
    ry(11, theta=1.0471975511965976)

    rz(12, theta=-0.315)
    rx(12, theta=1.5707963267948966)

    rz(13, theta=-0.105)
    ry(13, theta=1.0471975511965976)

    rz(14, theta=0.105)
    rx(14, theta=1.5707963267948966)

    rz(15, theta=0.315)
    ry(15, theta=1.0471975511965976)

    # Final cross-cluster synchronization.
    cnot(0, 8)
    cnot(2, 10)
    cnot(4, 12)
    cnot(6, 14)
    cnot(1, 9)
    cnot(3, 11)
    cnot(5, 13)
    cnot(7, 15)

    return {
        "qubits": qreg.size,
        "classical_bits": creg.size,
        "domain": "telecom-network",
        "scenario": "split-brain-recovery",
        "partitions": 8,
        "cluster_id": "cluster:auto",
        "recovery_edges": 7,
        "healing_edges": 8,
    }
