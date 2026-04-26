# Eigen OS

Eigen OS is a modular platform for **hybrid quantum-classical workloads**.
This repository contains the completed MVP baseline and the post-MVP open-source roadmap.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/Status-alpha-orange)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![Rust](https://img.shields.io/badge/Rust-1.92%2B-orange)

## Project status

> ⚠️ **Pre-alpha (architecture + contracts).**
> Breaking changes are expected until `v1.0`.

Contract-level compatibility is treated as stable only after:
- an RFC is accepted,
- reference documentation is updated,
- and conformance checks exist.

MVP baseline status:
- ✅ MVP-1 (Core Services Setup) completed.
- ✅ MVP-2 (Compilation Pipeline) completed.
- ✅ MVP-3 (Runtime Execution & Results) completed.

Next planning baseline:
- 📍 Post-MVP roadmap: [`docs/development/post-mvp-open-source-roadmap.md`](docs/development/post-mvp-open-source-roadmap.md).

### API version policy (baseline freeze)

- Public product API version is **fixed to `0.1`** for the MVP baseline.
- JobSpec `apiVersion` remains `eigen.os/v0.1`.
- Protobuf package namespace stays `...v1` (`proto/eigen/api/v1`) as a wire namespace.

## What is in scope now

- Public and internal API contracts (`proto/`).
- Job and format contracts (`docs/reference/`, `specs/`).
- Service skeletons for local E2E flow.
- Local deployment profile and CI quality gates.
- Post-MVP open-source execution plan.

## Quick navigation

- **Documentation hub:** [`docs/README.md`](docs/README.md)
- **Post-MVP roadmap:** [`docs/development/post-mvp-open-source-roadmap.md`](docs/development/post-mvp-open-source-roadmap.md)
- **Protobuf contracts:** [`proto/README.md`](proto/README.md)
- **Examples:** [`examples/README.md`](examples/README.md)
- **Specifications:** [`specs/README.md`](specs/README.md)
- **Local deployment:** [`deploy/local/README.md`](deploy/local/README.md)

## Repository layout

```text
eigen-os/
├── docs/                # Architecture, reference, tutorials, development docs
├── proto/               # Public/internal protobuf contracts (source of truth)
├── specs/               # Schema-level specs and examples
├── src/                 # Rust workspace + Python services
├── examples/            # Small runnable and integration examples
├── deploy/              # Local and container deployment assets
├── monitoring/          # Metrics/logging/tracing/dashboards
├── rfcs/                # Design proposals and contract evolution
└── scripts/             # Build/dev/test/CI helpers
```

## Getting started

### 1) Read architecture and contracts

Start with:
- [`docs/README.md`](docs/README.md)
- [`docs/architecture/overview.md`](docs/architecture/overview.md)
- [`docs/reference/README.md`](docs/reference/README.md)

### 2) Run CI-equivalent checks locally

See exact commands in:
- [`docs/development/README.md`](docs/development/README.md)

### 3) Bring up the local stack

```bash
./deploy/local/dev_env.sh up
```

Then tear it down:

```bash
./deploy/local/dev_env.sh down
```

Details:
- [`deploy/local/README.md`](deploy/local/README.md)

## Contributing

Contributions are welcome, especially around:
- contract clarity,
- API consistency,
- docs quality,
- conformance and CI automation.

Please open an issue/RFC when changing public or cross-service behavior.

## License

Licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE).
