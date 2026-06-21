# Distributed Job — Network Partition Example

This example demonstrates a bounded `DistributedJob` workload for Eigen OS.

It shows how the distributed workload contract carries canonical topology
through submission, normalization, compiler validation, and kernel-side
distributed metadata extraction.

## What this example is for

This workload is intended for:

- distributed compilation and scheduling validation;
- bounded topology metadata handling;
- static AST validation in the compiler;
- end-to-end integration of `spec.workload.topology`;
- reproducible telecom-style partitioned execution.

The example is not a generic dynamic distributed framework. It is a
contract-focused showcase of how Eigen represents bounded distributed execution.

## Workload contract

The example uses:

- `apiVersion: eigen.os/v1`
- `kind: QuantumJob`
- `spec.target: cluster:auto`
- `spec.program.path: program.eigen.py`
- `spec.workload.kind: DistributedJob`
- `spec.workload.execution_profile: distributed`
- `spec.workload.replayable: true`
- `spec.workload.backend_target: cluster:auto`
- `spec.workload.topology.cluster_id: cluster:auto`
- `spec.workload.topology.partition_count: 8`
- `spec.workload.topology.partition_ids: partition-0 ... partition-7`
- `spec.workload.topology.preferred_workers: worker-a ... worker-h`

The compiler-side distributed flags are passed through `spec.compiler_options`.

## Why the topology lives under `spec.workload.topology`

The kernel validation path reads the normalized workload JSON from
`jobspec_workload` and requires `spec.workload.topology` for
`DistributedJob` submissions.

If `topology` is missing, the job fails with:

```text
INVALID_ARGUMENT: spec.workload.topology is required for DistributedJob
```

That is why this example keeps the topology in the canonical workload contract
rather than in a separate legacy `distributed:` block.

## Why `cluster:auto`

`DistributedJob` is validated as a distributed backend target. In the current
contract, `cluster:auto` is the canonical distributed target used by the fixtures and kernel checks. In the local MVP, driver-manager also exposes a simulator-backed `cluster:auto` device alias so distributed submissions can exercise the full execute path end-to-end without a separate cluster.

## Example program

The program is a static, loop-free quantum circuit with:

- 16 qubits;
- explicit pairwise entanglement;
- cross-partition linking gates;
- fixed seed and fixed shots.

The static shape matters because the compiler subset used here validates the
AST strictly and rejects dynamic control flow in the circuit body.

## How to run

From this directory:

```bash
eigen submit -f job.yaml
```

Then inspect progress with:

```bash
eigen status <job_id>
eigen watch <job_id>
eigen results <job_id>
```

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

The final result should be `DONE`.

## Troubleshooting

### `spec.workload.topology is required for DistributedJob`

This means the workload contract does not expose `topology` inside

`spec.workload`. Ensure the job uses `apiVersion: eigen.os/v1` and that the
canonical topology block is present under `spec.workload`.

### Validation fails after topology is added

Check that:

- `partition_count` matches the number of `partition_ids`;
- `preferred_workers` has one entry per partition;
- each partition ID is unique;
- `distributed.enabled=true`, `distributed.target`, and `distributed.partition_count` are provided in `spec.compiler_options`.

## Domain note

This example uses a telecom/network partitioning story so contributors can see that the distributed workload family is not limited to synthetic cluster tests.

The same contract works for other bounded partitioned workloads with clear topology and replay requirements.
