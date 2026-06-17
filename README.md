# Eigen OS

Eigen OS is a contract-first monorepo for hybrid quantum-classical workloads. The repository centers on a small set of real, versioned contracts and services:

- **JobSpec** for describing jobs in `job.yaml`
- **System API** as the public ingress for submitting and querying jobs
- **Kernel / QRTX** as the authority for job lifecycle and orchestration
- **Compiler** for deterministic Eigen-Lang parsing and lowering
- **QFS** for artifact and result persistence
- **Driver Manager** for backend execution and result normalization
- **Benchmark** and **knowledge / learning** services for specialized workflows and future extensions
- **CLI** for user-facing submission and inspection commands

The most important user flow today is:

1. write or reuse a `job.yaml`
2. submit it through the CLI or System API
3. monitor status
4. fetch results and artifacts

## What this repository contains

- `docs/` — architecture notes, contracts, tutorials, reference material, and fixtures
- `proto/` — public and internal gRPC contracts
- `src/rust/` — Rust CLI and kernel crates
- `src/services/` — Python services such as the System API, compiler, benchmark service, and neuro-symbolic service
- `examples/` — runnable examples and smoke tests for JobSpec and Eigen-Lang flows
- `rfcs/` — design proposals and contract changes
- `scripts/` — local development and CI helpers

## Supported job model

The canonical JobSpec documentation lives in [`docs/reference/jobspec.md`](docs/reference/jobspec.md). The current workload-family kinds are:

- `QuantumJob`
- `HybridWorkflow`
- `DistributedJob`
- `BenchmarkJob`
- `PipelineJob`
- `ReplayJob`

The top-level resource kind remains `QuantumJob`, while the workload family is expressed under `spec.workload.kind`.

## Core runtime behavior

Eigen OS is designed around deterministic, observable job execution:

- validated and normalized submission payloads
- stable job lifecycle state transitions
- artifact persistence through QFS
- trace / log / metrics propagation across service boundaries
- explicit security and authorization context in the ingress path

Typical lifecycle states are:

`PENDING → COMPILING → QUEUED → RUNNING → DONE | ERROR | CANCELLED`

## CLI quick path

The tutorial flow in [`docs/tutorials/first-job-eigen-lang.md`](docs/tutorials/first-job-eigen-lang.md) uses the following commands:

```bash
eigen submit -f job.yaml
eigen status <job_id>
eigen watch <job_id>
eigen results <job_id>
```

For a concrete example, see `examples/basic/vqe_cycle/`.

## Key documents

- [`docs/architecture/overview.md`](docs/architecture/overview.md)
- [`docs/reference/jobspec.md`](docs/reference/jobspec.md)
- [`docs/tutorials/first-job-eigen-lang.md`](docs/tutorials/first-job-eigen-lang.md)
- [`src/services/system-api/README.md`](src/services/system-api/README.md)

## Development notes

This repository is organized as a working platform, not just a specification archive. The docs, fixtures, and tests are used to keep the contracts aligned with the implementation. When changing public behavior, update the corresponding reference document, fixtures, and tests together.
