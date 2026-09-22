# Workload kinds showcase

This directory demonstrates the six workload-family kinds supported by JobSpec.

The examples intentionally cover different domains:

- **QuantumJob** — quantum materials / state preparation
- **HybridWorkflow** — quantum chemistry VQE loop
- **DistributedJob** — telecom/network partitioned execution
- **BenchmarkJob** — reproducible benchmark / regression run
- **PipelineJob** — scientific multi-stage artifact handoff
- **ReplayJob** — deterministic audit and replay

The examples mirror the current repository contract:

- `apiVersion: eigen.os/v1` for the canonical JobSpec surface,
- `kind: QuantumJob` as the public compatibility anchor,
- `spec.program.path`, `spec.program.source`, or `spec.program.uri` as the
  allowed program source forms,
- `spec.workload.kind` to select the workload family explicitly.

For benchmark workloads, the example passes the fixed seed through
`spec.compiler_options` so the compiler receives the benchmark-specific
validation input, while `spec.metadata` keeps the human-readable seed label.

The distributed example shows the canonical `spec.workload.topology` envelope used by the kernel for bounded partitioned execution.

The `PipelineJob` and `ReplayJob` examples show the lineage-oriented fields used for deterministic replay and audit flows.

The results surface is shared across all examples: `eigen results` prints a human-readable `summary` block from any runtime-published `result.summary.*` metadata, then the normalized `counts` and raw `metadata`.
