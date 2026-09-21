# Distributed Job — Network Partition Example

This example demonstrates a bounded `DistributedJob` workload for Eigen OS.

The example is designed to make the distributed contract visible in three
places at once:

1. the JobSpec declares eight partitions and their preferred workers;
2. the quantum program uses a fixed 16-qubit topology that maps two qubits to
each partition and names the cross-partition links explicitly;
3. the compiled artifact records the distributed topology together with a
terminal measurement, so the workload can be exercised end-to-end.

The result is a small, deterministic topology-aware workload rather than a
generic distributed runtime or a physical telecom-network simulator.

## What this example demonstrates

The workload is intended to exercise:

- distributed compilation and scheduling validation;
- canonical spec.workload.topology handling;
- strict static AST validation in Eigen-Lang;
- explicit partition-aware circuit structure;
- terminal measurement and reproducible simulator execution;
- end-to-end propagation of distributed metadata through the Eigen OS pipeline.

The important idea is the mapping between the JobSpec topology and the circuit,
not the telecom story by itself.

## Topology at a glance

The eight logical partitions are deliberately mapped to adjacent qubit pairs:

partition-0  -> q0,  q1
partition-1  -> q2,  q3
partition-2  -> q4,  q5
partition-3  -> q6,  q7
partition-4  -> q8,  q9
partition-5  -> q10, q11
partition-6  -> q12, q13
partition-7  -> q14, q15

This makes the circuit phases easy to read:

LOCAL WORK
P0: q0  -- q1
P1: q2  -- q3
P2: q4  -- q5
P3: q6  -- q7
P4: q8  -- q9
P5: q10 -- q11
P6: q12 -- q13
P7: q14 -- q15

BOUNDARY TRAFFIC
P0 -- P1   via q1  -> q2
P1 -- P2   via q3  -> q4
P2 -- P3   via q5  -> q6
P3 -- P4   via q7  -> q8
P4 -- P5   via q9  -> q10
P5 -- P6   via q11 -> q12
P6 -- P7   via q13 -> q14

HEALING LINKS
P0 -- P4   via q0  <-> q8
P1 -- P5   via q2  <-> q10
P2 -- P6   via q4  <-> q12
P3 -- P7   via q6  <-> q14
P0 -- P4   via q1  <-> q9
P1 -- P5   via q3  <-> q11
P2 -- P6   via q5  <-> q13
P3 -- P7   via q7  <-> q15

The first two sections are local partition work followed by explicit boundary
traffic. The healing phase then introduces eight fixed cross-cluster links,
followed by a deterministic reconciliation sweep and final synchronization.

## Workload contract

The example uses:

- `apiVersion: eigen.os/v1`
- `kind: QuantumJob`
- `spec.target: cluster:auto`
- `spec.program.path: program.eigen.py`
- `spec.program.entrypoint: main`
- `spec.workload.kind: DistributedJob`
- `spec.workload.execution_profile: distributed`
- `spec.workload.replayable: true`
- `spec.workload.backend_target: cluster:auto`
- `spec.workload.topology.cluster_id: cluster:auto`
- `spec.workload.topology.partition_count: 8`
- `spec.workload.topology.partition_ids: partition-0 ... partition-7`
- `spec.workload.topology.preferred_workers: worker-a ... worker-h`

The compiler-side distributed flags are passed through `spec.compiler_options`.

## Why the topology lives under 

`spec.workload.topology`

The canonical distributed workload contract carries topology in
`spec.workload.topology`. The kernel validation path reads the normalized
workload object and requires that topology for `DistributedJob` submissions.

If the topology is missing, validation fails with:

`INVALID_ARGUMENT: spec.workload.topology is required for DistributedJob`

Keeping the topology under spec.workload also makes the source of truth clear:
the partition graph is part of the workload contract, while
`spec.compiler_options` contains compiler behavior flags.

## Why `cluster:auto`

`cluster:auto` is the distributed target used by the repository's current
DistributedJob contract and fixtures.

In the local MVP, `cluster:auto` is backed by the simulator path. That means
this example can exercise validation, compilation, optimization, scheduling,
execution, persistence, and observability locally without claiming that eight
physical workers were used.

The example therefore demonstrates **distributed job orchestration and explicit
topology metadata**, not physical multi-worker execution.

## Why the program is fully static

The Eigen-Lang compiler subset used by this example intentionally rejects
runtime control flow in the circuit body. The program therefore contains:

- no import math or other non-Eigen imports;
- no enumerate, zip, or dynamic iteration;
- no if, while, match, or conditional expressions;
- only fixed gate calls and fixed integer qubit indices;
- one terminal MEASURE operation covering all 16 qubits.

The static shape is important because it makes the circuit deterministic,
replayable, and easy for the compiler to inspect.

## What the circuit means

The program is a topology visualization encoded as a real quantum circuit:

### Phase 1 — local partition work

Each partition owns two qubits and performs the same local pattern of
single-qubit rotations plus one internal entangling gate.

### Phase 2 — boundary traffic

Seven adjacent partition boundaries are exercised with fixed cross-partition
CNOT links. These are explicit communication edges in the logical circuit.

### Phase 3 — healing links

Eight long-range cross-cluster CNOT pairs connect the first four partitions to
the second four partitions. These links are the example's explicit recovery
structure.

### Phase 4 — reconciliation

Every qubit receives a deterministic single-qubit reconciliation step before
final cross-cluster synchronization.

### Final synchronization and measurement

The eight long-range links are applied once more, followed by a terminal
measurement of all 16 qubits into classical bits `0..15`.

The circuit is intentionally not presented as a fault-tolerant recovery
algorithm. It is a bounded workload whose gate structure makes partitioning,
boundary traffic, and healing links easy to inspect.

## What to inspect after a successful run

A successful compile should expose the following shape in the compiled AQO:

qubits: 16
operations: 158
measurement_count: 1
terminal_measurement_present: true
distributed topology: enabled
partition_count: 8
target: cluster:auto
queue_provider: memory
topology_hint: data_parallel

The exact simulator counts are not the point of the example; the useful part is
that the compiled artifact contains both the circuit and the distributed
topology projection.

## How to run

From this directory:

eigen submit -f job.yaml

Then inspect progress with:

eigen status <job_id>
eigen watch <job_id>
eigen results <job_id>

For compiler-only debugging, run:

eigen compile --job job.yaml

## Expected behavior

A successful run should move through these stages:

1. validation
2. compile
3. optimize
4. schedule
5. execute
6. persist
7. record knowledge and observability
8. finalize

The final job state should be `DONE`.

## Troubleshooting

`spec.workload.topology is required for DistributedJob`

The normalized workload does not expose `topology` under `spec.workload`.
Check that `apiVersion: eigen.os/v1` is used and that the canonical topology
block is present under `spec.workload`.

## Validation fails after topology is added

Check that:

- `partition_count` matches the number of `partition_ids`;
- `preferred_workers` has one entry per partition;
- each partition ID is unique;
- `distributed.enabled=true` is present;
- `distributed.target` is present;
- `distributed.partition_count` matches the workload topology.

## Compilation fails with an AST validation error

Keep the program in the static Eigen-Lang subset. In particular, do not add
runtime `if`, `while`, `match`, `enumerate`, or `zip` logic to generate gates.
Unroll fixed topology operations explicitly, as this example does.

## The run uses a simulator

That is expected in the local MVP. `cluster:auto` is the distributed contract
target, while the local driver path is simulator-backed. Treat the execution
artifact as evidence of end-to-end distributed **orchestration**, not of eight
physical workers running concurrently.

## Domain note

The telecom/network story gives the topology a concrete interpretation:
partitions represent isolated network segments, boundary links represent
cross-segment traffic, and healing links represent restored cross-cluster
connectivity.

The same bounded contract can be reused for other partitioned workloads when
the topology, replay requirements, and cross-partition edges are explicit.