# ⚛️ Eigen OS

**Eigen OS** — contract-first platform for hybrid quantum-classical workloads.

It gives you a single flow to describe a job, submit it, track execution, and collect results across local simulators, runtime services, and backend drivers.

At the center of the repository are a few stable ideas:

- **JobSpec** — the canonical `job.yaml` contract
- **System API** — the public ingress for submission and status queries
- **Kernel / QRTX** — the authority for lifecycle, orchestration, and scheduling
- **Compiler** — deterministic Eigen-Lang parsing and lowering
- **QFS** — artifact, result, and lineage persistence
- **Driver Manager** — backend execution and normalization
- **CLI** — the main user-facing tool for working with jobs

## What Eigen OS is for

Eigen OS is meant for teams and individuals who want to run quantum or hybrid workflows without dealing directly with low-level orchestration details.

It is useful when you want to:

- submit a quantum workload in a repeatable way
- run hybrid algorithms with classical control logic around quantum steps
- execute workloads on simulator or backend targets through a stable contract
- keep results, artifacts, and lineage in one controlled flow
- replay or benchmark jobs with explicit metadata
- develop and test runtime services against versioned interfaces

## For users

If you only want to run workloads, the main path is simple:

1. create or reuse a `job.yaml`
2. install the CLI
3. submit the job
4. watch progress
5. fetch results

The most common CLI commands are:

```bash
eigen submit -f job.yaml
eigen status <job_id>
eigen watch <job_id>
eigen results <job_id>
```

A complete beginner-friendly walkthrough is available in [`docs/tutorials/first-job-eigen-lang.md`](docs/tutorials/first-job-eigen-lang.md).

### Install the CLI

From the repository root:

```bash
scripts/install-eigen-cli.sh
```

The script:

- requires `cargo`
- must be run as your normal user, not with `sudo`
- installs the CLI to `~/.local/bin` by default
- installs into your active virtual environment if `VIRTUAL_ENV` is set

If your shell does not already see the binary, add the install directory to `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

If you are using a virtual environment, the binary is placed under that environment’s `bin/` directory.

## Job types and use cases

The top-level JobSpec kind is `QuantumJob`, while the workload family is described under `spec.workload.kind`.

| Workload family | Typical use case |
|---|---|
| `QuantumJob` | A standard quantum workload, such as a circuit execution or a simple algorithm prototype on a simulator or supported backend. |
| `HybridWorkflow` | A job that mixes quantum steps with classical optimization or control logic, such as VQE-style workflows. |
| `DistributedJob` | A workload that needs bounded distributed execution or topology hints, for example partitioned execution across workers or nodes. |
| `BenchmarkJob` | A reproducible benchmark run with fixed seed, stable inputs, and comparable results across executions. |
| `PipelineJob` | A multi-stage workflow where outputs from one stage are handed off to the next stage in a deterministic chain. |
| `ReplayJob` | A run intended for deterministic replay, investigation, or audit of a previous execution path. |

## Repository structure

- `docs/` — architecture notes, reference contracts, tutorials, and fixtures
- `proto/` — public and internal gRPC contracts
- `src/rust/` — Rust CLI and kernel crates
- `src/services/` — Python services such as the System API, compiler, benchmark service, and neuro-symbolic service
- `examples/` — runnable examples and smoke-test material
- `rfcs/` — proposals and contract changes
- `scripts/` — local development and CI helpers

## Core runtime flow

Eigen OS is built around a deterministic job lifecycle:

```text
PENDING → COMPILING → QUEUED → RUNNING → DONE | ERROR | CANCELLED
```

The main flow is:

- the user submits a job through the CLI or System API
- the System API validates and normalizes the request
- the Kernel owns lifecycle and scheduling decisions
- the compiler lowers Eigen-Lang into canonical internal artifacts
- QFS persists artifacts, results, and lineage
- the Driver Manager executes against the selected backend and normalizes outputs

## For developers

If you work on the platform itself, the most relevant reference documents are:

- [`docs/architecture/overview.md`](docs/architecture/overview.md)
- [`docs/reference/jobspec.md`](docs/reference/jobspec.md)
- [`docs/tutorials/first-job-eigen-lang.md`](docs/tutorials/first-job-eigen-lang.md)
- [`src/services/system-api/README.md`](src/services/system-api/README.md)

The repository is contract-first: when public behavior changes, update the reference docs, fixtures, and tests together.

### Developer quick start

For local development, the repository is typically used with Docker Compose and the service-level test suite.

A minimal smoke path is:

```bash
./deploy/local/dev_env.sh up
bash scripts/dev/generate-protos.sh
cargo test --manifest-path src/rust/Cargo.toml --workspace
pytest src/services/system-api/tests
```

## User-facing docs worth reading first

- [`docs/tutorials/first-job-eigen-lang.md`](docs/tutorials/first-job-eigen-lang.md)
- [`docs/reference/jobspec.md`](docs/reference/jobspec.md)
- [`docs/architecture/overview.md`](docs/architecture/overview.md)

## License

Apache License 2.0. See [LICENSE](LICENSE).
