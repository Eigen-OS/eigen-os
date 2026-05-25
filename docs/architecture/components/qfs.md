# QFS (Quantum Data Fabric)

- **Phase:** MVP (Phase 0) → Phase-1 evolution baseline
- **Status snapshot date:** 2026-05-25
- **Implementation status:** Partially implemented

---

# Responsibility

QFS (Quantum Data Fabric) is the persistent artifact, execution-state, and runtime data-management subsystem of Eigen OS.

QFS provides deterministic storage, retrieval, lineage tracking, replay support, and artifact lifecycle management for compiler, runtime, optimization, and execution workflows.

The long-term QFS architecture is divided into three logical levels:

| Level | Component | Responsibility |
|---|---|---|
| L1 | LiveQubitManager | Live qubit/feed-forward runtime state |
| L2 | StateStore | Distributed runtime/session/state coordination |
| L3 | CircuitFS | Persistent immutable artifact storage |

Current implementation includes a partially implemented Level-3 storage layer and System API QFS facade functionality.

---

# Responsibility Scope

## Implemented now

### CircuitFS (Level 3)

- QFS is implemented as a simplified Level-3 `CircuitFS` subsystem in Rust via `CircuitFsLocal`.
- Deterministic job artifact persistence exists on local filesystem storage.
- Default storage root:
  - `/var/lib/eigen/circuit_fs`
- Configurable through:
  - `EIGEN_QFS_ROOT`

### System API QFS facade

System API implements a `QFSStore` abstraction supporting:

- local in-memory storage,
- optional S3-compatible storage backend,
- retry behavior,
- failover logic,
- `qfs://...` artifact references.

### Runtime artifact persistence

Artifacts currently persisted include:

- source payloads,
- compiled AQO artifacts,
- execution results,
- metadata blobs,
- runtime logs,
- manifests,
- parquet exports.

### Runtime integration

QFS artifacts are actively used as the source of truth between:

- System API,
- Eigen Kernel,
- Compiler runtime,
- Result retrieval flows,
- CLI/runtime integration tests.

---

## Required target responsibility

The final QFS subsystem SHALL provide:

- Unified persistent artifact management across all runtime stages.
- Immutable deterministic artifact storage.
- Cross-service artifact lineage tracking.
- Deterministic replay support.
- Distributed execution-state coordination.
- Runtime adaptive-state persistence.
- Feed-forward/live-qubit state lifecycle management.
- Optimizer and neuro-symbolic artifact persistence.
- Replay/audit evidence preservation.
- Multi-backend storage abstraction.
- Cross-cluster artifact consistency guarantees.

---

# Architecture Position

QFS is a foundational runtime infrastructure subsystem.

It integrates with:

- `system-api`
- `eigen-kernel`
- `eigen-compiler`
- `driver-manager`
- future `hwe`
- future `gnn-optimizer`
- future `knowledge-base`
- future `neuro-symbolic-core`

QFS is mandatory infrastructure for:

- deterministic replay,
- runtime artifact persistence,
- adaptive-runtime auditability,
- optimizer trace preservation,
- execution lineage reconstruction,
- distributed runtime coordination,
- rollback verification,
- release-readiness evidence.

---

# QFS Levels

# Level 1 — LiveQubitManager

## Implemented now

- Not implemented.
- No production runtime component currently exists.

---

## Required target responsibility

The Level-1 subsystem SHALL manage:

- live qubit handles,
- feed-forward execution state,
- runtime adaptive qubit coordination,
- low-latency runtime synchronization,
- transient hardware execution state.

### Required future capabilities

- live-qubit session tracking,
- feed-forward synchronization,
- hardware-state mutation tracking,
- transient runtime consistency guarantees,
- adaptive runtime state propagation.

---

# Level 2 — StateStore

## Implemented now

- Not implemented as a production subsystem.
- MVP contracts still treat Level-2 behavior as stub/no-op functionality.

---

## Required target responsibility

The Level-2 subsystem SHALL provide:

- distributed runtime coordination,
- execution-state persistence,
- adaptive-runtime state management,
- scheduler coordination state,
- replay correlation state,
- optimizer and neuro-symbolic state persistence.

### Required future capabilities

- distributed consistency model,
- runtime leases/locks,
- replay lineage indexes,
- topology snapshots,
- adaptive-runtime state coordination.

---

# Level 3 — CircuitFS

## Implemented now

### Rust implementation

Implemented through:

- `CircuitFsLocal`

Capabilities include:

- deterministic filesystem artifact persistence,
- canonical runtime layout,
- artifact loading/retrieval,
- atomic writes,
- metadata persistence.

### Current artifact layout

Current canonical layout includes:

```text
input/
compiled/
results/
logs/
meta/
```

### Canonical artifacts

Examples include:

```text
compiled/circuit.aqo.json
compiled/circuit.qasm
results/result.json
results/results.parquet
results/manifest.json
```

#### System API integration

System API `QFSStore` supports:

- local backend,
- optional S3-compatible backend,
- retry/failover behavior,
- artifact reference resolution.

---

## Required target responsibility

CircuitFS SHALL evolve into:

- immutable artifact storage,
- content-addressed artifact persistence,
- cross-region replication support,
- distributed artifact consistency,
- deterministic artifact lineage tracking,
- replay-safe artifact retrieval.

---

## Interfaces

### 1. Runtime APIs

#### Implemented now

**Rust APIs**

`CircuitFsLocal` methods include:

- `store_*`
- `load_*`
- layout/path helpers

**Python APIs**

QFSStore supports:

- `put`
- `get`
- `list`
- `delete`
- `atomic_write`

#### Runtime wiring

Kernel initializes QFS through:

- `EIGEN_QFS_ROOT`
- fallback `/var/lib/eigen/circuit_fs`

---

#### Required target runtime APIs

QFS SHALL expose:

- stable artifact handles,
- immutable retrieval APIs,
- replay-safe artifact resolution,
- deterministic lineage APIs,
- adaptive-runtime artifact APIs.

---

### 2. gRPC Interfaces

#### Implemented now

- No standalone `QfsService` gRPC service currently exists.
- No protobuf service contract is implemented for QFS runtime access.

---

#### Required target gRPC API

The future centralized QFS subsystem SHALL expose:

`QfsService`

**Required methods**

- `StoreArtifact`
- `LoadArtifact`
- `DeleteArtifact`
- `ListArtifacts`
- `ResolveReference`
- `PinArtifact`
- `CreateSnapshot`
- `ReplayBundle`
- `HealthCheck`

---

#### Required artifact contract

**Canonical ArtifactHandle**

```text
ArtifactHandle {
  hash,
  size,
  path,
  format,
  lineage,
  version
}
```

**Required metadata**

- deterministic digest,
- replay lineage ID,
- creation timestamp,
- producing component,
- runtime environment,
- compatibility version.

---

## Inputs / Outputs

### Inputs

#### Implemented now

Current inputs include:

- source artifacts,
- compiled artifacts,
- execution results,
- metadata payloads,
- JSON/YAML/Parquet artifacts,
- optional binary payloads.

---

#### Required target inputs

**Runtime artifacts**

- AQO IR,
- compiler AST snapshots,
- optimizer traces,
- neuro-symbolic decisions,
- hardware telemetry snapshots,
- replay bundles.

**Adaptive-runtime artifacts**

- HWE decisions,
- GNN optimizer outputs,
- routing plans,
- fallback activation traces,
- deterministic replay metadata.

---

### Outputs

#### Implemented now

Current outputs include:

- persisted artifacts,
- deterministic filesystem references,
- in-memory blob retrieval,
- stable runtime retrieval behavior.

---

#### Required target outputs

**Persistent artifacts**

- immutable runtime artifacts,
- replay bundles,
- optimizer audit traces,
- topology snapshots,
- neuro-symbolic explainability payloads.

**Replay artifacts**

- deterministic execution traces,
- runtime lineage metadata,
- backend mapping history,
- adaptive-runtime decisions.

---

## Storage / State

### Internal State

#### Implemented now

**Existing runtime state**

- Local filesystem persistence.
- In-memory storage backends.
- Retry/failover metadata.
- Artifact path indexing.

---

#### Required target internal state

**Artifact indexing**

- content-addressed indexes,
- lineage graphs,
- replay correlation indexes,
- topology snapshot indexes.

**Runtime coordination state**

- adaptive-runtime coordination state,
- distributed runtime leases,
- replay validation indexes.

---

### External Storage

#### Implemented now

**Local filesystem backend**

Default:

```text
/var/lib/eigen/circuit_fs
```

**Optional S3 backend**

Configured through:

```text
EIGEN_QFS_BACKEND=s3
```

---

#### Required target storage

**Artifact storage**

- immutable object storage,
- distributed filesystem support,
- multi-region replication,
- content-addressed storage.

**Replay/audit storage**

- deterministic replay traces,
- optimizer decision history,
- neuro-symbolic artifacts,
- hardware adaptation lineage.

---

## Caching

### Implemented now

- No dedicated shared caching subsystem is implemented.

---

### Required target caches

- hot artifact cache,
- replay artifact cache,
- topology snapshot cache,
- optimizer artifact cache,
- adaptive-runtime telemetry cache.

---

## Failure Modes

### Implemented now

#### Existing failure handling

- Retry/failover behavior exists in `QFSStore`.
- Invalid job identifiers are explicitly modeled.
- Missing artifact behavior is handled in runtime flows.

---

### Required target failure taxonomy

#### Storage failures

- backend unavailable,
- object corruption,
- replication lag,
- consistency violation.

#### Runtime failures

- replay mismatch,
- lineage inconsistency,
- artifact version conflict,
- cache corruption.

#### Distributed consistency failures

- partial replication,
- stale reads,
- split-brain coordination state,
- replay divergence.

---

### Recovery and fallback requirements

The QFS subsystem SHALL support:

- bounded retries,
- deterministic recovery,
- immutable rollback snapshots,
- replay-safe restoration,
- artifact integrity verification,
- degraded-mode local persistence.

---

## Observability

### Implemented now

- QFS references are surfaced in runtime/API metadata.
- Runtime tests validate artifact retrieval behavior.

---

### Required target observability

#### Metrics

Required metrics include:

- `qfs_artifact_store_total`
- `qfs_artifact_retrieve_total`
- `qfs_artifact_size_bytes`
- `qfs_operation_duration_seconds`
- `qfs_replay_bundle_total`
- `qfs_replication_lag_seconds`

#### Logs

Required logging includes:

- artifact lineage logging,
- replay reconstruction logging,
- optimizer artifact logging,
- neuro-symbolic artifact logging.

#### Traces

Required tracing includes:

- artifact lifecycle tracing,
- replay correlation tracing,
- adaptive-runtime lineage tracing.

---

## Security and Compliance

### Required target controls

#### Artifact security

- immutable artifact enforcement,
- signed artifact manifests,
- encrypted storage backends,
- RBAC for artifact access,
- provenance validation.

#### Compliance requirements

- deterministic replay evidence,
- retention/versioning policy,
- immutable audit trail,
- export provenance tracking.

---

## ADR / RFC Follow-up Requirements

### Required future governance work

- Add ADR for current QFS architecture split:
    - Rust `CircuitFsLocal`
    - System API `QFSStore`
    - optional S3 backend

- Add ADR/RFC amendment for canonical artifact layout:
    - `input/`
    - `compiled/`
    - `results/`
    - `logs/`
    - `meta/`

- Define deterministic replay artifact contract.
- Define distributed consistency guarantees and conformance tests.
- Define optimizer/neuro-symbolic artifact persistence standards.
