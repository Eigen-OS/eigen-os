# Protobuf contracts

This directory contains **all** `.proto` contracts for Eigen OS.
These files are the canonical source for generated client/server stubs.

## Packages

### Public API (`eigen.api.v1`, product version `0.1`)
- Path: `proto/eigen/api/v1/*.proto`
- Services: `JobService`, `DeviceService`

### Internal API (`eigen.internal.v1`, product version `0.1`)
- Path: `proto/eigen/internal/v1/*.proto`
- Services: `KernelGateway`, `DriverManagerService`, `CompilationService`

> Note: `v1` in package/path is a protobuf namespace. MVP contract version is fixed at **`0.1`**.

## Rust code generation

Rust bindings are generated at compile time by crate `src/rust/crates/eigen-proto`.

```bash
cd src/rust
cargo build -p eigen-proto
```

## Rules

- Keep `.proto` files in this folder as the single source of truth.
- Do not duplicate/fork proto contracts across services.
- Regenerate language bindings from these definitions only.
