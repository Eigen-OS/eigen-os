from eigen_lang import (
    ClassicalRegister,
    QubitRegister,
    cnot,
    hybrid_program,
    measure,
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
        "scenario": "partition-boundary-healing",
        "partition_strategy": "isolate-heal",
        "cluster_id": "cluster:auto",
        "partitions": 8,
        "partition_layout": "2-qubits-per-partition",
        "execution_mode": "simulator-backed",
    },
)
def main():
    """A bounded partition-aware workload with explicit healing links."""

    qreg = QubitRegister(16)
    creg = ClassicalRegister(16)

    # ==================================================================
    # Topology map
    # ==================================================================
    # partition-0 -> q0, q1
    # partition-1 -> q2, q3
    # partition-2 -> q4, q5
    # partition-3 -> q6, q7
    # partition-4 -> q8, q9
    # partition-5 -> q10, q11
    # partition-6 -> q12, q13
    # partition-7 -> q14, q15
    #
    # The circuit mirrors that topology explicitly. No runtime loops or
    # dynamic gate generation are used because the compiler validates a
    # strict static Eigen-Lang AST subset.

    # ==================================================================
    # Phase 1: local work inside each partition.
    # ==================================================================
    # P0: q0 <-> q1
    rx(0, theta=1.5707963267948966)
    ry(1, theta=1.5707963267948966)
    cnot(0, 1)
    rz(0, theta=0.00)
    rz(1, theta=-0.00)
    rx(1, theta=1.0471975511965976)
    ry(0, theta=0.7853981633974483)

    # P1: q2 <-> q3
    rx(2, theta=1.5707963267948966)
    ry(3, theta=1.5707963267948966)
    cnot(2, 3)
    rz(2, theta=0.17)
    rz(3, theta=-0.085)
    rx(3, theta=1.0471975511965976)
    ry(2, theta=0.7853981633974483)

    # P2: q4 <-> q5
    rx(4, theta=1.5707963267948966)
    ry(5, theta=1.5707963267948966)
    cnot(4, 5)
    rz(4, theta=0.31)
    rz(5, theta=-0.155)
    rx(5, theta=1.0471975511965976)
    ry(4, theta=0.7853981633974483)

    # P3: q6 <-> q7
    rx(6, theta=1.5707963267948966)
    ry(7, theta=1.5707963267948966)
    cnot(6, 7)
    rz(6, theta=0.49)
    rz(7, theta=-0.245)
    rx(7, theta=1.0471975511965976)
    ry(6, theta=0.7853981633974483)

    # P4: q8 <-> q9
    rx(8, theta=1.5707963267948966)
    ry(9, theta=1.5707963267948966)
    cnot(8, 9)
    rz(8, theta=0.67)
    rz(9, theta=-0.335)
    rx(9, theta=1.0471975511965976)
    ry(8, theta=0.7853981633974483)

    # P5: q10 <-> q11
    rx(10, theta=1.5707963267948966)
    ry(11, theta=1.5707963267948966)
    cnot(10, 11)
    rz(10, theta=0.83)
    rz(11, theta=-0.415)
    rx(11, theta=1.0471975511965976)
    ry(10, theta=0.7853981633974483)

    # P6: q12 <-> q13
    rx(12, theta=1.5707963267948966)
    ry(13, theta=1.5707963267948966)
    cnot(12, 13)
    rz(12, theta=1.01)
    rz(13, theta=-0.505)
    rx(13, theta=1.0471975511965976)
    ry(12, theta=0.7853981633974483)

    # P7: q14 <-> q15
    rx(14, theta=1.5707963267948966)
    ry(15, theta=1.5707963267948966)
    cnot(14, 15)
    rz(14, theta=1.19)
    rz(15, theta=-0.595)
    rx(15, theta=1.0471975511965976)
    ry(14, theta=0.7853981633974483)

    # ==================================================================
    # Phase 2: explicit traffic across adjacent partition boundaries.
    # ==================================================================
    # P0 -> P1
    cnot(1, 2)
    rz(1, theta=0.117)
    ry(2, theta=0.2)

    # P1 -> P2
    cnot(3, 4)
    rz(3, theta=0.131)
    ry(4, theta=0.21)

    # P2 -> P3
    cnot(5, 6)
    rz(5, theta=0.145)
    ry(6, theta=0.22)

    # P3 -> P4
    cnot(7, 8)
    rz(7, theta=0.159)
    ry(8, theta=0.225)

    # P4 -> P5
    cnot(9, 10)
    rz(9, theta=0.173)
    ry(10, theta=0.24)

    # P5 -> P6
    cnot(11, 12)
    rz(11, theta=0.187)
    ry(12, theta=0.25)

    # P6 -> P7
    cnot(13, 14)
    rz(13, theta=0.201)
    ry(14, theta=0.26)

    # ==================================================================
    # Phase 3: restore long-range connectivity with explicit healing links.
    # ==================================================================
    # P0 <-> P4, first qubit lane
    cnot(0, 8)
    ry(0, theta=1.5707963267948966)
    rz(8, theta=0.22)
    cnot(8, 0)
    rx(8, theta=1.0471975511965976)

    # P1 <-> P5, first qubit lane
    cnot(2, 10)
    ry(2, theta=1.5707963267948966)
    rz(10, theta=0.24)
    cnot(10, 2)
    rx(10, theta=1.0471975511965976)

    # P2 <-> P6, first qubit lane
    cnot(4, 12)
    ry(4, theta=1.5707963267948966)
    rz(12, theta=0.26)
    cnot(12, 4)
    rx(12, theta=1.0471975511965976)

    # P3 <-> P7, first qubit lane
    cnot(6, 14)
    ry(6, theta=1.5707963267948966)
    rz(14, theta=0.28)
    cnot(14, 6)
    rx(14, theta=1.0471975511965976)

    # P0 <-> P4, second qubit lane
    cnot(1, 9)
    ry(1, theta=1.5707963267948966)
    rz(9, theta=0.23)
    cnot(9, 1)
    rx(9, theta=1.0471975511965976)

    # P1 <-> P5, second qubit lane
    cnot(3, 11)
    ry(3, theta=1.5707963267948966)
    rz(11, theta=0.25)
    cnot(11, 3)
    rx(11, theta=1.0471975511965976)

    # P2 <-> P6, second qubit lane
    cnot(5, 13)
    ry(5, theta=1.5707963267948966)
    rz(13, theta=0.27)
    cnot(13, 5)
    rx(13, theta=1.0471975511965976)

    # P3 <-> P7, second qubit lane
    cnot(7, 15)
    ry(7, theta=1.5707963267948966)
    rz(15, theta=0.29)
    cnot(15, 7)
    rx(15, theta=1.0471975511965976)

    # ==================================================================
    # Phase 4: deterministic reconciliation on every qubit.
    # ==================================================================
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

    # ==================================================================
    # Final synchronization across the healed links.
    # ==================================================================
    cnot(0, 8)
    cnot(2, 10)
    cnot(4, 12)
    cnot(6, 14)
    cnot(1, 9)
    cnot(3, 11)
    cnot(5, 13)
    cnot(7, 15)

    # ==================================================================
    # Terminal measurement: all 16 qubits -> classical bits 0..15.
    # ==================================================================
    measure(
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        c=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
    )

    return {
        "qubits": qreg.size,
        "classical_bits": creg.size,
        "domain": "telecom-network",
        "scenario": "partition-boundary-healing",
        "partitions": 8,
        "partition_size": 2,
        "cluster_id": "cluster:auto",
        "partition_layout": "partition-0:q0,q1; partition-1:q2,q3; partition-2:q4,q5; partition-3:q6,q7; partition-4:q8,q9; partition-5:q10,q11; partition-6:q12,q13; partition-7:q14,q15",
        "boundary_edges": 7,
        "healing_edges": 8,
        "execution_mode": "simulator-backed",
    }
