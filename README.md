# Eigen OS

Eigen OS is a **platform for running hybrid quantum-classical workloads**: from job submission and quantum program compilation to execution and result retrieval.

In short, this repository is a distributed system scaffold where:
- you describe a workload using a JobSpec,
- services validate and compile it,
- the runtime executes it via a driver/simulator,
- and the API returns status, logs, and results in a predictable format.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/Status-alpha-orange)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![Rust](https://img.shields.io/badge/Rust-1.92%2B-orange)

## What this product is

## Who it is for
- Teams that need a **transparent backend platform** for quantum experiments.
- Platform engineers evolving APIs, contracts, and runtime behavior through an RFC-driven process.
- Integrators who need stable formats, gRPC contracts, and a local E2E development path.

### What it does today
- Delivers the MVP baseline in three parts:
  - ✅ MVP-1: core services and contracts.
  - ✅ MVP-2: compilation pipeline.
  - ✅ MVP-3: execution and results retrieval.
- ✅ Phase-1: production runtime hardening.
- ✅ Phase-2: orchestration layer (scheduler/device-aware routing/multi-device/batch contracts).
- Provides public and internal protobuf APIs (`proto/`).
- Includes services (compiler, system-api, driver-manager), local deployment assets, examples, observability, and CI scripts.

### What it does not guarantee yet
- The project is **pre-alpha**: breaking changes can happen before `v1.0`.
- Contract stability is considered real only when all of the following exist:
  1. an accepted RFC,
  2. updated reference documentation,
  3. conformance checks.

## How it works (5 steps)

1. A client submits a JobSpec through the API.
2. `system-api` validates the request and manages the job lifecycle.
3. `eigen-compiler` converts the program into executable artifacts (AQO and related outputs).
4. `driver-manager` selects a driver (for example, a simulator) and launches execution.
5. Kernel/runtime updates status, and the client reads progress and final results.

Useful references:
- Architecture overview: [`docs/architecture/overview.md`](docs/architecture/overview.md)
- Contract map: [`docs/architecture/contract-map.md`](docs/architecture/contract-map.md)
- JobSpec format: [`docs/reference/jobspec.md`](docs/reference/jobspec.md)

## Quick start

### 1) Read the key docs
- [`docs/README.md`](docs/README.md)
- [`docs/reference/README.md`](docs/reference/README.md)
- [`examples/README.md`](examples/README.md)

### 2) Start the local environment

```bash
./deploy/local/dev_env.sh up
```

Stop it:

```bash
./deploy/local/dev_env.sh down
```

Details: [`deploy/local/README.md`](deploy/local/README.md)

### 3) Run CI-equivalent checks
Commands and flows are documented in [`docs/development/README.md`](docs/development/README.md).

## Repository layout

```text
eigen-os/
├── docs/                # Architecture, reference, tutorials, development docs
├── proto/               # gRPC/Protobuf contracts (source of truth)
├── specs/               # Format specifications and examples
├── src/                 # Rust workspace and Python services
├── examples/            # Workload and integration examples
├── deploy/              # Local and Docker deployment
├── monitoring/          # Metrics, logs, tracing, dashboards
├── rfcs/                # RFCs and architecture evolution
└── scripts/             # Build, test, and CI helpers
```

## API versioning (current baseline)

- Product release line after Phase-2 closure: **`0.3.0`**.
- Product API for the MVP baseline is fixed to **`0.1`**.
- `JobSpec.apiVersion`: `eigen.os/v0.1`.
- Protobuf namespace: `proto/eigen/api/v1` (wire namespace).

Phase-2 release closure artifacts:
- [`docs/development/phase-2-release-readiness-checklist.md`](docs/development/phase-2-release-readiness-checklist.md)
- [`docs/development/phase-2-compatibility-report.md`](docs/development/phase-2-compatibility-report.md)
- [`docs/development/phase-2-migration-notes.md`](docs/development/phase-2-migration-notes.md)

## Where to go next

- Post-MVP roadmap: [`docs/development/post-mvp-open-source-roadmap.md`](docs/development/post-mvp-open-source-roadmap.md)
- ADR index: [`docs/adr/README.md`](docs/adr/README.md)
- RFC directory: [`rfcs/`](rfcs)

## Contributing

If you change public contracts or cross-service behavior, open an issue/RFC first.

- Contribution process: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security policy: [`SECURITY.md`](SECURITY.md)
- Code of conduct: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)

## License

Licensed under **Apache License 2.0** — see [`LICENSE`](LICENSE).
