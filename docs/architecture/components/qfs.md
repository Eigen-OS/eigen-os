# QFS (Quantum Data Fabric) – Current State (as of 2026-05-09)

- Phase: MVP (Phase 0)

- Status: **Partially implemented** (CircuitFS + System API QFS store are implemented; several blueprint items are not yet implemented).

## Responsibility

### Implemented now

- QFS is implemented as a **simplified CircuitFS (Level 3)** in Rust (`CircuitFsLocal`) for deterministic job artifact persistence on local filesystem paths rooted at `/var/lib/eigen/circuit_fs` (override via env in kernel wiring). 
- System API also provides a **QFS blob facade** (`QFSStore`) with local in-memory and optional S3-compatible backend, retry, and failover logic for `qfs://...` references.
- Artifacts are used as a source of truth between runtime/kernel-facing flows and API result retrieval flows.

### TODO / not implemented yet

- **TODO:** `StateStore` (Level 2) remains not implemented as a production component.
- **TODO:** `LiveQubitManager` (Level 1) remains not implemented as a production component.
- **TODO:** Unified “full QFS” orchestration across all levels (L1/L2/L3) is not available.

> RFC cross-check: RFC `0007-qrtx-mvp` states that StateStore/LiveQubitManager are no-op or stubs in MVP; this remains true.

## Interfaces

### Implemented now

- Rust in-process API via `CircuitFsLocal` methods (`store_*`, `load_*`, layout/path helpers).
- Python System API storage facade via `QFSStore` (`put/get/list/delete/atomic_write`) over pluggable backends.
- Kernel integration initializes `CircuitFsLocal` using `EIGEN_QFS_ROOT` (fallback `/var/lib/eigen/circuit_fs`).

### TODO / not implemented yet

- **TODO:** Internal gRPC `QfsService` (`proto/qfs/service.proto`) is not present in repository; no standalone QFS gRPC service contract is implemented.
- **TODO:** Dedicated QFS client library over gRPC is not implemented.

## Inputs / Outputs

### Implemented now

- Inputs: source/job artifacts, compiled artifacts, results artifacts, metadata bytes.
- Outputs: persisted artifacts retrievable by deterministic paths/refs and in-memory bytes retrieval.
- Formats in active use include JSON/YAML/Parquet and optional binary payloads.

### TODO / not implemented yet

- **TODO:** A single cross-language `ArtifactHandle { hash, size, path }` contract is not standardized as an enforced interface across all entry points.

## Storage / State

### Implemented now

- Local filesystem CircuitFS layout per job (`input/`, `compiled/`, `results/`, `logs/`, `meta/`) with canonical filenames like `compiled/circuit.aqo.json`, `compiled/circuit.qasm`, `results.parquet`, `results/result.json`, `results/manifest.json`.
- System API supports optional S3-compatible backend (`EIGEN_QFS_BACKEND=s3`) with local fallback.
- Atomic write helpers exist in both Rust and Python paths.

### TODO / not implemented yet
- **TODO:** Global immutable/no-overwrite policy is not uniformly enforced across all write paths.
- **TODO:** Content-addressed deduplication is not implemented as a formal feature.
- **TODO:** Shared hot-artifact cache policy is not implemented as a documented/enforced subsystem.

## Failure Modes

### Implemented now

- Retry/failover behavior exists in `QFSStore` facade.
- Not-found and invalid job-id style errors are explicitly modeled in CircuitFS.

### TODO / not implemented yet

- **TODO:** Formal gRPC status mapping (`UNAVAILABLE`, `RESOURCE_EXHAUSTED`, `INVALID_ARGUMENT`) is not implemented because `QfsService` is absent.
- **TODO:** Distributed-storage consistency semantics (e.g., read-your-writes guarantees) are not specified in executable conformance tests.

## Observability

### Implemented now

- QFS refs are surfaced in runtime/API metadata (for example compiled AQO, results parquet, timeline refs) and used by tests.

### TODO / not implemented yet

- **TODO:** Dedicated QFS metric family documented previously (`qfs_artifact_store_total`, `qfs_artifact_retrieve_total`, `qfs_artifact_size_bytes`, `qfs_operation_duration_seconds`) is not implemented as a verified metric contract.
- **TODO:** Dedicated QFS service tracing spans/log schema are not implemented as an independently versioned contract.

## RFC / ADR reconciliation

### RFCs checked

- `rfcs/0007-qrtx-mvp.md`: MVP QFS scope and stubbed L1/L2 components align with current state.
- `rfcs/0011-eigen-lang-submission-v0.1.md`: artifact persistence intent aligns, but concrete path shape has evolved to nested directories like `compiled/` and `results/` in implementation.
- `rfcs/0017-mvp3-results-retrieval-and-cli-runtime-ux.md`: runtime results layout and stable retrieval behavior are reflected in current artifacts and tests.

### ADRs checked

- No ADR currently defines a standalone QFS service contract equivalent to the `QfsService` blueprint in this document.

### TODO / follow-up

- **TODO:** Add/approve ADR for current QFS architecture split (Rust CircuitFS + System API QFSStore facade + optional S3 backend).
- **TODO:** Add/approve ADR (or RFC amendment) for canonical artifact layout/versioning as implemented (`input/`, `compiled/`, `results/`, `meta/`) to avoid divergence from older flat examples.
