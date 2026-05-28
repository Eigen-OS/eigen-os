# QFS (Quantum Data Fabric)

- **Document status:** Normative architecture + storage contract (MVP → Phase-1 baseline)
- **Phase:** MVP (Phase 0) → Phase-1 evolution baseline
- **Snapshot date:** 2026-05-25
- **Contract version:** `1.0.0`
- **Implementation status:** Partially implemented (Level-3 baseline + API facade)

QFS (Quantum Data Fabric) is the persistent artifact, execution-state, and runtime data-management subsystem of Eigen OS.

QFS provides deterministic storage, retrieval, lineage tracking, replay support, and artifact lifecycle management for compiler, runtime, optimization, and execution workflows.

The long-term QFS architecture is divided into three logical levels:

| **Level** | **Component** | **Responsibility** |
|---|---|---|
| L1 | `LiveQubitManager` | Live qubit / feed-forward runtime state |
| L2 | `StateStore` | Distributed runtime/session/state coordination |
| L3 | `CircuitFS` | Persistent artifact storage + job-scoped layout |

Current implementation includes a partially implemented **Level-3** storage layer and a **System API QFS facade** used by runtime flows.

---

## 1. Contract Versioning

### 1.1 Contract marker

All components exporting QFS metrics MUST emit:

```text
eigen_qfs_contract_info{version="1.0.0"} 1
```

---

### 1.2 SemVer policy

#### MAJOR

- changes to canonical artifact paths that break readers,
- incompatible reference grammar changes (`qfs://...`),
- incompatible artifact handle schema changes,
- immutable/atomic semantics changes.

#### MINOR

- new optional metadata fields,
- new artifact kinds/paths (additive),
- new backends (additive),
- new conformance checks (additive).

#### PATCH

- documentation and implementation fixes without semantic changes.

---

## 2. Responsibility

QFS is the **canonical persistence layer** for:

- submission inputs (JobSpec + sources),
- compiler outputs (AQO/QASM + diagnostics),
- runtime orchestration artifacts (manifests, timelines),
- execution results,
- error artifacts,
- explainability artifacts (where enabled),
- split/merge lineage artifacts (where enabled),
- replay and audit evidence.

QFS is not a general-purpose database API exposed to end users. Public APIs expose **artifact references**, not raw storage internals.

---

## 3. Architecture Position

QFS integrates with:

- `system-api`
- `eigen-kernel` (QRTX)
- `eigen-compiler`
- `driver-manager`
- future: `hwe`, `gnn-optimizer`, `knowledge-base`, `neuro-symbolic-core`

QFS is mandatory infrastructure for:

- deterministic replay,
- runtime artifact persistence,
- adaptive-runtime auditability,
- optimizer trace preservation,
- execution lineage reconstruction,
- distributed runtime coordination (Phase-1+),
- rollback verification,
- release-readiness evidence.

---

## 4. QFS Levels

### 4.1 Level 1 — LiveQubitManager

#### Implemented now

- Not implemented.
- No production runtime component currently exists.

#### Required target responsibility
Level-1 SHALL manage:

- live qubit handles,
- feed-forward execution state,
- runtime adaptive qubit coordination,
- low-latency runtime synchronization,
- transient hardware execution state.

This capability is post-MVP.

---

### 4.2 Level 2 — StateStore

#### Implemented now

- Not implemented as a production subsystem.
- MVP treats Level-2 behavior as stub/no-op.

#### Required target responsibility
Level-2 SHALL provide:

- distributed runtime coordination state,
- session/state persistence,
- scheduler coordination state,
- runtime leases/locks,
- replay correlation indexes,
- topology snapshot indexes (for adaptive routing),
- split/merge coordination state (where enabled).

This capability is post-MVP / Phase-1.

---

### 4.3 Level 3 — CircuitFS

#### Implemented now (baseline)

- Implemented as a simplified Level-3 subsystem in Rust via `CircuitFsLocal`.
- Deterministic job artifact persistence exists on local filesystem storage.
- Default storage root:
  - `/var/lib/eigen/circuit_fs`
- Configurable through:
  - `EIGEN_QFS_ROOT`

#### System API facade (implemented)
System API implements a `QFSStore` abstraction supporting:

- local backend,
- optional S3-compatible backend,
- bounded retry behavior,
- `qfs://...` artifact references and resolution.

#### Required target responsibility
CircuitFS SHALL evolve into:

- immutable artifact storage semantics,
- content-addressed persistence,
- integrity verification (checksums),
- cross-region replication support,
- replay-safe artifact resolution,
- deterministic lineage graphs.

---

## 5. Canonical Reference Model

### 5.1 Artifact reference grammar

QFS references are opaque strings of the form: `qfs://<namespace>/<path>`

Constraints:

- `<namespace>` and `<path>` MUST be ASCII and URL-safe.
- `..` traversal is forbidden.
- References MUST be deterministic and stable once published.
- References MUST NOT embed secrets or credentials.

---

### 5.2 Canonical job namespace

For job-scoped artifacts: `qfs://jobs/<job_id>/<relative_path>`

`<job_id>` is the runtime-assigned stable job identifier.

---

## 6. Canonical Job Artifact Layout (Normative)

QFS MUST expose a stable layout under `qfs://jobs/<job_id>/` for the following top-level categories:

```text
input/
source/
compiled/
results/
logs/
meta/
timeline/
```

---

### 6.1 Minimum required artifacts

#### Submission

- `qfs://jobs/<job_id>/input/job.yaml` (or equivalent canonical JobSpec payload)
- `qfs://jobs/<job_id>/source/<program>` (canonical source bundle or resolved program)

#### Compilation

- `qfs://jobs/<job_id>/compiled/compiled.aqo.json` (or stable AQO ref)
- `qfs://jobs/<job_id>/compiled/compiled.qasm` (optional; backend dependent)
- `qfs://jobs/<job_id>/compiled/diagnostics.json` (optional)

#### Results

- `qfs://jobs/<job_id>/results/results.json` (normalized result envelope)
- `qfs://jobs/<job_id>/results/error.json` (durable failure artifact when job is ERROR)

#### Timeline

- `qfs://jobs/<job_id>/timeline/timeline.json` (recommended; may be partial in MVP)

#### Logs

- `qfs://jobs/<job_id>/logs/run.log` (optional; deployment dependent)

---

### 6.2 Async failure artifact requirement

If job lifecycle reaches terminal `ERROR`, the system SHOULD persist: `qfs://jobs/<job_id>/results/error.json`

This is aligned with the error contract and is the canonical durable failure location.

---

## 7. Artifact Semantics

### 7.1 Determinism requirements

QFS storage MUST preserve:

- deterministic bytes for identical inputs (when upstream packaging is deterministic),
- stable naming and paths under the canonical layout,
- stable checksum computation for integrity verification.

---

### 7.2 Immutability rules

- Artifacts under `compiled/` and `results/` SHOULD be treated as immutable once published.
- If regeneration is required, it MUST produce a new versioned artifact (Phase-1 content-addressing) or a new job scope (MVP).

---

### 7.3 Atomicity rules (MVP baseline)

For a single artifact write operation:

- writes MUST be atomic from the perspective of readers (no partial reads).
- implementations MAY use temp-write + rename (local FS) or multipart upload + finalize (object store).

---

## 8. Interfaces

### 8.1 Runtime APIs (implemented)

#### Rust (`CircuitFsLocal`)

- `store_*`
- `load_*`
- path/layout helpers
- atomic write behavior (implementation dependent)

#### System API (`QFSStore`)

- `put`
- `get`
- `list`
- `delete` (subject to policy; see §12)
- `atomic_write`

Kernel initializes QFS through:

- `EIGEN_QFS_ROOT`
- fallback `/var/lib/eigen/circuit_fs`

---

### 8.2 gRPC Interfaces (target)

#### Implemented now

- No standalone `QfsService` gRPC service exists.

#### Required target gRPC API
A future centralized QFS subsystem SHALL expose:

`QfsService`

Required methods:

- `StoreArtifact`
- `LoadArtifact`
- `ListArtifacts`
- `ResolveReference`
- `PinArtifact` (prevent GC)
- `CreateSnapshot`
- `GetSnapshot`
- `HealthCheck`

`DeleteArtifact` MAY exist internally but MUST be policy-gated and never allow deletion of required audit artifacts.

---

## 9. ArtifactHandle Schema (Target Contract)

Canonical handle:

```text
ArtifactHandle {
  ref,                    // qfs://... reference (opaque)
  digest,                 // sha256:<hex> (or future multihash)
  size_bytes,
  content_type,           // e.g. application/json
  created_at_ms,
  producer,               // service name
  schema_version,         // for structured artifacts
  lineage: {
    job_id,
    parent_refs[],        // producing inputs
    stage                // compile/execute/merge/etc.
  }
}
```

Minimum metadata for structured artifacts SHOULD include:

- deterministic digest,
- producing component,
- creation timestamp,
- compatibility/schema version,
- lineage identifiers.

---

## 10. Failure Model and Error Semantics

QFS operations MUST use the canonical error model:

- `NOT_FOUND` for missing artifacts or missing job scope
- `INVALID_ARGUMENT` for malformed refs, forbidden paths, invalid digests
- `FAILED_PRECONDITION` for illegal lifecycle actions (e.g., reading results before available where applicable)
- `RESOURCE_EXHAUSTED` for quota/capacity limits
- `UNAVAILABLE` for transient backend outage
- `DEADLINE_EXCEEDED` for operation timeouts
- `PERMISSION_DENIED` / `UNAUTHENTICATED` for access control

Structured error details SHOULD include:

- `google.rpc.ResourceInfo` (artifact ref context)
- `google.rpc.ErrorInfo` (stable `EIGEN_*` reason)
- `google.rpc.RetryInfo` for retryable failures
- `google.rpc.DebugInfo` only for internal deployments (redacted)

---

## 11. Storage Backends

### 11.1 Implemented now

#### Local filesystem backend

Default root: `/var/lib/eigen/circuit_fs`

#### Optional S3-compatible backend

May be enabled via environment/configuration such as: `EIGEN_QFS_BACKEND=s3`

(Exact flags are deployment-specific; behavior must remain contract-compatible.)

---

### 11.2 Required target storage

QFS SHALL support:

- immutable object storage,
- multi-region replication,
- content-addressed storage,
- integrity verification,
- replication lag visibility,
- policy-driven retention.

---

## 12. Retention, Deletion, and Pinning

### 12.1 MVP baseline

Retention is deployment-configured; deletion behavior may exist for local dev, but MUST NOT compromise:

- job results,
- error artifacts,
- audit/replay evidence.

---

### 12.2 Target rules (normative)

- Required audit artifacts MUST NOT be deletable without elevated operator policy.
- `PinArtifact` MUST be supported for:
  - replay bundles,
  - compliance retention,
  - long-running investigations.
- GC policies MUST be deterministic and auditable.

---

## 13. Caching (Target)

#### Implemented now

- No dedicated shared caching subsystem.

#### Required target caches

- hot artifact cache,
- replay bundle cache,
- topology snapshot cache,
- optimizer artifact cache,
- adaptive-runtime telemetry cache.

Caching MUST NOT break determinism or serve stale artifacts without explicit staleness indicators.

---

## 14. Observability

### 14.1 Implemented now

- QFS references are surfaced in runtime/API metadata where applicable.
- Runtime tests validate artifact retrieval behavior.

---

### 14.2 Required target metrics (normative names)

QFS implementations MUST export the following metric families (exact labels MUST remain bounded):

```text
eigen_qfs_artifact_store_total{backend,kind}
eigen_qfs_artifact_load_total{backend,kind}
eigen_qfs_artifact_bytes_total{backend,kind}
eigen_qfs_operation_duration_seconds_bucket{op,backend}
eigen_qfs_operation_duration_seconds_sum{op,backend}
eigen_qfs_operation_duration_seconds_count{op,backend}
eigen_qfs_integrity_failures_total{backend}
eigen_qfs_replication_lag_seconds{backend,region}          // where replication exists
eigen_qfs_replay_bundles_total{kind}                       // where replay exists
```

Label rules:

- MUST NOT include `job_id`, `trace_id`, `artifact_ref` as labels.
- `kind`, `op`, `backend`, `region` MUST be bounded/enumerable.

---

### 14.3 Logs and traces (target)

QFS SHOULD emit traces/spans for:

- store/load/resolve operations,
- integrity verification,
- snapshot creation,
- replay bundle assembly.

Logs SHOULD include:

- `trace_id`,
- `job_id` (if job-scoped),
- `artifact_ref` (as a field, not a metric label),
- operation outcome and error reason codes.

---

## 15. Security and Compliance

### 15.1 Artifact security (target)

QFS SHALL support:

- immutable artifact enforcement,
- checksum/digest verification,
- signed manifests (Phase-1),
- encrypted storage backends,
- RBAC for artifact access,
- provenance tracking.

---

### 15.2 Multi-tenant safety

QFS MUST prevent:

- cross-tenant access (when multi-tenant mode is enabled),
- leaking tenant identifiers in metric labels,
- exposing credential material via logs or refs.

---

## 16. Conformance Requirements

An implementation is conformant if it:

1. Preserves canonical reference grammar (`qfs://...`) and forbids path traversal.
2. Provides atomic writes for artifact publish operations.
3. Supports the canonical job layout and required artifacts.
4. Enforces integrity checks where digests exist.
5. Uses canonical error semantics and structured details where applicable.
6. Exports required QFS metrics with bounded labels.
7. Preserves determinism and auditability guarantees.

Required test coverage (minimum):

- atomic write behavior,
- missing artifact mapping → `NOT_FOUND`,
- invalid ref mapping → `INVALID_ARGUMENT`,
- results/error artifact persistence contract,
- bounded label enforcement (no forbidden labels),
- backend outage mapping → `UNAVAILABLE` + retry guidance (where applicable).

---

## 17. ADR / RFC Follow-up Requirements (Normative TODOs)

Future governance work SHALL:

- add ADR for the current QFS split:
  - Rust `CircuitFsLocal`,
  - System API `QFSStore`,
  - optional S3 backend.
- define the deterministic replay bundle contract and its QFS layout.
- define distributed consistency guarantees and conformance tests for replication.
- define optimizer/neuro-symbolic artifact schemas and persistence standards.

---

## 18. Invariants (MUST remain true)

- QFS references are stable and traversal-safe.
- Job results and error artifacts remain durable and retrievable.
- Artifact writes are atomic for readers.
- Metrics labels remain bounded and do not contain correlation identifiers.
- QFS never weakens determinism, auditability, or security guarantees.
- Baseline execution MUST remain possible even if advanced QFS Level-1/2 features are not present.
