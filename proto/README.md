# Protobuf contracts (source of truth)

This directory contains **all** `.proto` definitions for Eigen OS.

## Packages

- **Public API** (client-facing): `eigen.api.v1`
  - `proto/eigen_api/v1/*.proto`
  - Services: `JobService`, `DeviceService`

- **Internal APIs** (kernel-facing, private network): `eigen.internal.v1`
  - `proto/eigen_internal/v1/*.proto`
  - Services: `KernelGateway`, `DriverManagerService`, `CompilationService`

## Rust generation

Rust bindings are generated at **compile time** via the `eigen-proto` crate (`src/rust/crates/eigen-proto`).

```bash
cd src/rust
cargo build -p eigen-proto
```

## Rules

- Protos in this folder are the **single source of truth**.
- Generated stubs must be derived from these files.
- Do not fork/duplicate `.proto` files across services.
