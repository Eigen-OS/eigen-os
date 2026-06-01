# Eigen OS

Eigen OS is an open platform for deterministic hybrid quantum-classical execution: from JobSpec submission and compilation to distributed runtime execution and result retrieval.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/Status-alpha-orange)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![Rust](https://img.shields.io/badge/Rust-1.92%2B-orange)

## What this product is

## TL;DR

- You submit workloads in a stable **JobSpec** format.
- `system-api` validates lifecycle and contracts.
- `eigen-compiler` produces deterministic execution artifacts.
- `resource-manager` and runtime coordinate scheduling/queue/worker execution.
- You get status, logs, topology metadata, and results via stable APIs.

## Project status (as of 2026-04-28)

Completed milestones:

- ✅ MVP-1: Core services and contracts
- ✅ MVP-2: Compilation pipeline
- ✅ MVP-3: Execution and results retrieval
- ✅ Phase-1: Production runtime hardening
- ✅ Phase-2: Orchestration layer
- ✅ Phase-3: Benchmarking platform
- ✅ Phase-4: Intelligent runtime contracts
- ✅ Phase-5: Distributed execution contracts and closure package

Current implementation baseline remains pre-`1.0.0`; Product `1.0.0` is tracked as a contract-alignment target in [`docs/development/product-1.0-contract-alignment-plan.md`](docs/development/product-1.0-contract-alignment-plan.md), with Wave 0 inventory and manifest artifacts under [`docs/development/product-1.0-contract-inventory.md`](docs/development/product-1.0-contract-inventory.md) and [`contracts/product-1.0/manifest.json`](contracts/product-1.0/manifest.json).

## Who this repository is for

- Platform teams building transparent orchestration for quantum workloads.
- Engineers who need contract-driven APIs, conformance tests, and reproducible behavior.
- Contributors evolving architecture through RFC/ADR governance.

## What is guaranteed vs. not guaranteed

### Guaranteed in current baseline

- Contract-first evolution (RFC + ADR + compatibility docs).
- Deterministic behavior for core lifecycle/dispatch/benchmark/distributed execution contracts.
- Explicit version markers in public and internal contract artifacts.

### Not guaranteed yet

- The project is still pre-`1.0.0`; breaking changes are possible between minor releases.
- Production SLAs are not declared in this repository.

## Quick start

### 1) Read core docs (recommended order)

1. [`docs/README.md`](docs/README.md)
2. [`docs/architecture/overview.md`](docs/architecture/overview.md)
3. [`docs/reference/README.md`](docs/reference/README.md)
4. [`docs/development/README.md`](docs/development/README.md)

### 2) Start local environment

```bash
./deploy/local/dev_env.sh up
```

Stop:

```bash
./deploy/local/dev_env.sh down
```

More details: [`deploy/local/README.md`](deploy/local/README.md)

### 3) Run CI-equivalent checks locally

See: [`docs/development/README.md`](docs/development/README.md)

## Where to find Phase-5 closure artifacts

- ADR index: [`docs/adr/README.md`](docs/adr/README.md)
- Phase-5 RFC/ADR coverage: [`docs/development/phase-5-rfc-adr-gap-analysis.md`](docs/development/phase-5-rfc-adr-gap-analysis.md)
- Phase-5 readiness checklist: [`docs/development/phase-5-release-readiness-checklist.md`](docs/development/phase-5-release-readiness-checklist.md)
- Phase-5 compatibility report: [`docs/development/phase-5-compatibility-report.md`](docs/development/phase-5-compatibility-report.md)

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
├── rfcs/                # RFC proposals and decision history
└── scripts/             # Build, test, and CI helpers
```

## Contributing

If you change public contracts or cross-service behavior, open an issue/RFC first.

- Contribution process: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security policy: [`SECURITY.md`](SECURITY.md)
- Code of conduct: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)

## License

Licensed under **Apache License 2.0** — see [`LICENSE`](LICENSE).
