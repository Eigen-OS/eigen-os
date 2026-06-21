# Benchmark Job — QFT Regression Example

This example demonstrates a reproducible BenchmarkJob workload for compiler and runtime regression checks in Eigen OS.

It is designed to exercise the full pipeline:

- job submission and normalization;
- compiler validation and lowering;
- optimizer integration;
- scheduling;
- execution on `sim:local`;
- persistence of results;
- observability and knowledge recording.

## What this example is for

This workload is intended for:

- compiler regression testing;
- runtime regression testing;
- reproducibility checks;
- end-to-end pipeline validation;
- benchmark-oriented smoke tests.

It is not meant to demonstrate a mathematically exact quantum Fourier transform implementation. Instead, it uses a statically expanded circuit with a stable gate pattern that is useful for consistent benchmarking across versions.

## Why this example matters

`BenchmarkJob` is useful when you want a workload that is:

- reproducible;
- stable across repeated runs;
- suitable for comparing compiler/runtime versions;
- simple enough to validate quickly;
- heavy enough to exercise the pipeline end to end.

This example also shows how Eigen handles:

- a benchmark workload kind;
- fixed seed handling;
- explicit backend targeting;
- observability capture;
- knowledge recording after execution.

## Workload contract

The example uses:

- `apiVersion: eigen.os/v1`
- `kind: QuantumJob`
- `spec.program.path: program.eigen.py`
- `spec.workload.kind: BenchmarkJob`
- `spec.workload.execution_profile: benchmark`
- `spec.workload.replayable: false`
- `spec.workload.backend_target: sim:local`
- `spec.workload.seed: 42`
- `spec.metadata.seed: 42`

## Example program

The program uses a fixed circuit shape with statically enumerated gates.

Main properties:

- 16 qubits;
- 16 classical bits;
- fixed seed `42` in both workload metadata and compiler inputs;
- fixed shots `16384`;
- no dynamic loops in the circuit body;
- static gate list for validation compatibility.

## How to run

From the example directory:

```bash
eigen submit -f job.yaml
```

Then check job progress:

```bash
eigen status <job_id>
eigen watch <job_id>
eigen results <job_id>
```

## Expected behavior

A successful run should move through the following stages:

1. `validate-enqueue`
2. `compile`
3. `optimize`
4. `schedule`
5. `execute`
6. `persist`
7. `record-knowledge-observability`
8. `finalize`

The final result should be `DONE`.

## What a successful result looks like

A successful execution will typically show:

- `compile stage completed`
- `optimizer service completed`
- `resource schedule selected`
- `execution completed`
- `results persisted to qfs`
- `knowledge and observability recorded`

The output counts are expected to be non-uniform, because the circuit prepares a structured state rather than a uniform superposition.

## Why the output distribution looks like this

The circuit applies a chain of single-qubit rotations and entangling CNOT gates.
That produces a structured measurement distribution rather than a flat one.

So the following are normal:

- one very large dominant count;
- several smaller side peaks;
- asymmetry in the bitstrings;
- non-trivial measurement support.

This is what makes the example useful as a regression benchmark.

## Stability notes

This example is intentionally written to avoid validation failures in the current compiler subset:

- no dynamic control flow in the program body;
- no runtime-generated gate lists;
- no unsupported control flow;
- fixed seed and fixed shots;
- explicit `backend_target` in the workload contract.

## Troubleshooting

### Validation failed during compile

If the job fails with a validation error, the most likely causes are:

- dynamic control flow in the program body;
- unsupported language constructs;
- missing or inconsistent workload contract fields;
- mismatch between `job.yaml` and `program.eigen.py`.

For this example, keep the gate sequence statically expanded.

### Job accepted but never reaches execute

Check:

- compiler service logs;
- optimizer service logs;
- backend target availability;
- kernel orchestration logs.

### Results look unexpected

Remember that this is a benchmark regression circuit, not a canonical QFT implementation. If you need a mathematically faithful QFT example, the circuit should be rewritten accordingly.

## Relation to other workload kinds

This example is specifically for:

- `BenchmarkJob`

It is useful as a template for:

- compiler regression baselines;
- runtime smoke tests;
- deterministic benchmark comparisons.

It is not a good template for:

- adaptive hybrid optimization loops;
- replay investigations;
- distributed orchestration scenarios;
- multi-stage pipelines.

## Implementation notes

The example demonstrates an important contract detail:

- `seed` is carried in `spec.workload.seed` and mirrored into `spec.metadata.seed` so
  the compiler and runtime can see the same deterministic benchmark context;
- `backend_target` is carried in the workload/compiler path so that the
  compiler validation can succeed consistently;
- the program itself stays deterministic and static;
- observability and knowledge recording are part of the normal execution path.

## If you modify this example

Keep these constraints intact:

- fixed `seed`;
- fixed `shots`;
- explicit `backend_target`;
- static gate listing;
- benchmark-friendly metadata.

If you change the circuit, re-run the job and verify that:

- compile still succeeds;
- optimizer still accepts the workload;
- runtime still reaches `DONE`;
- result distribution still looks reasonable for a benchmark regression test.

## Suggested metadata

Useful metadata fields for this example include:

- `domain: benchmarking`
- `benchmark: qft-depth-regression`
- `seed: 42`
- `example: qft-benchmark-regression`

These help keep the workload discoverable and reproducible.

## Summary

This example is a stable benchmark regression workload that:

- validates the compiler path;
- exercises the full runtime pipeline;
- produces reproducible behavior;
- records observability and knowledge artifacts;
- serves as a practical reference for `BenchmarkJob`.

It is intentionally simple in semantics and strong in pipeline coverage.
