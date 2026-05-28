# Eigen OS — Data Flow Specification

- **Document status:** Normative MVP architecture contract
- **Contract scope:** End-to-end runtime and artifact flow (MVP + explicitly marked Phase-1 extensions)
- **Snapshot date:** 2026-05-24
- **Compatibility target:** Eigen OS 1.0 contracts (`eigen.api.v1`, `eigen.internal.v1`, JobSpec v1.0, QFS Layout v1.0)

---

## 1. Purpose and Scope

This document defines the canonical end-to-end **data flow contract** for Eigen OS.

It serves four purposes simultaneously:

1. Defines the intended architectural flow required by the Technical Specification (ТЗ).
2. Captures the current implementation state and freezes it into stable contracts.
3. Fixes runtime and artifact semantics so downstream components can rely on deterministic behavior.
4. Separates **stable MVP guarantees** from **future-phase / TODO** items.

This specification covers:

- user submission flow (CLI/SDK → public API),
- validation, packaging, and canonical hashing,
- compilation flow (Eigen-Lang → AQO/QASM),
- execution flow (Driver Manager → backend),
- result persistence and retrieval (QFS/CircuitFS),
- lifecycle and job-state propagation,
- error and failure data flow (sync + async),
- observability and trace propagation.

This document is aligned with:

- `docs/architecture/contract-map.md`
- `docs/reference/jobspec.md`
- `docs/reference/qfs-layout.md`
- `docs/reference/error-model.md`
- `docs/reference/error-mapping.md`

---

## 2. Architectural Scope

### 2.1 Runtime Components

| **Component** | **Responsibility** | **Contract status** |
|---|---|---|
| `eigen-cli` / SDKs | User interaction, JobSpec packaging, metadata propagation | Stable |
| System API | Public gateway (gRPC), validation, auth, tracing propagation | Stable (transport + mapping) |
| Kernel (QRTX) | Orchestration, lifecycle, persistence coordination | Stable (MVP flow) |
| Compiler Service | AST-based compilation to AQO/QASM | Stable (MVP feature-set) |
| Driver Manager | Backend abstraction + execution + normalization | Stable (MVP backends) |
| Vendor Backend / Simulator | Execution target | Provider-dependent |
| QFS (CircuitFS) | Durable artifacts and results persistence | Stable layout contract v1.0 |
| Observability stack | Metrics, tracing, structured logs | Stable contracts; wiring may be partial per deployment |

### 2.2 Primary Data Domains

| **Data domain** | **Description** |
|---|---|
| Job specification | Declarative submission descriptor (`job.yaml`, JobSpec v1.0) |
| Program source | Eigen-Lang source file (`program.eigen.py`) or other allowed program forms |
| Intermediate representation | AQO v1.0 (primary), QASM (optional export) |
| Execution payload | Driver-consumable envelope (CircuitPayload / bytes or QFS reference) |
| Runtime state | Job lifecycle + orchestration metadata |
| Result artifacts | Parquet primary result + JSON metadata artifacts |
| Telemetry | Metrics, traces, structured logs |

---

## 3. High-Level Data Flow

### 3.1 Canonical Runtime Flow

```text
User
  ↓
eigen-cli / SDK
  ↓
System API (public gRPC)
  ↓
Kernel (QRTX)
  ├──→ Compiler Service
  │       ↓
  │     AQO/QASM artifacts
  │
  ├──→ Driver Manager
  │       ↓
  │    Backend / Simulator / Hardware
  │
  └──→ QFS (CircuitFS persistence)
          ↓
       Result retrieval
          ↓
         User
```

### 3.2 Contracted Runtime Lifecycle

The canonical **client-visible** lifecycle is:

```text
PENDING → COMPILING → QUEUED → RUNNING → DONE | ERROR | CANCELLED
```

Notes:

- Services MAY have internal substates, but they MUST NOT violate the public contract ordering.
- Terminal states are immutable: `DONE`, `ERROR`, `CANCELED`.

---

## 4. Core Data Formats

### 4.1 JobSpec (job.yaml) — Canonical submission descriptor (v1.0)

Reference: `docs/reference/jobspec.md`

Minimum valid JobSpec:

```yaml
apiVersion: eigen.os/v1
kind: QuantumJob

metadata:
  name: hello-world

spec:
  target: sim:local
  program:
    path: program.eigen.py
    entrypoint: main
```

Normative rules:

- JobSpec is declarative; it describes intent, not procedure.
- Packaging MUST be deterministic (path normalization + stable hashing).
- Validation occurs before orchestration begins.

---

### 4.2 Eigen-Lang Source

Canonical file: `program.eigen.py`

Compiler behavior (MVP contract):

- AST-based parsing only (no arbitrary execution of user code),
- strict allowlist of imports (`eigen_lang` package only),
- exactly one `@hybrid_program(...)` entrypoint,
- deterministic compilation and deterministic validation errors.

---

### 4.3 AQO (Abstract Quantum Operations)

Reference: `docs/reference/formats/aqo.md` (AQO v1.0)

AQO is the canonical IR handed from compiler to runtime.

Minimal example:

```json
{
  "version": "1.0",
  "qubits": 2,
  "operations": [
    {"op": "H", "q": [0]},
    {"op": "CX", "q": [0, 1]},
    {"op": "MEASURE", "q": [0, 1], "c": [0, 1]}
  ]
}
```

Normative rules:

- `version`, `qubits`, `operations` are required.
- Unknown opcodes MUST be rejected with `INVALID_ARGUMENT`.
- `MEASURE` must satisfy `len(q) == len(c)`.
- Canonical bit ordering for counts MUST be stable (`c[0]` is LSB).

---

### 4.4 CircuitPayload (Kernel → Driver Manager execution envelope)

Logical fields (implementation-defined, but contractually required semantics):

- `format`: AQO_JSON | AQO_PROTO | QASM (subset / provider-dependent)
- `payload`: bytes OR QFS reference
- `shots`: integer
- `options`: bounded key-value options (stable keys when standardized)
- `metadata`: optional bounded metadata (no unbounded identifiers)

---

### 4.5 ExecutionResult (Driver Manager → Kernel normalized result)

Normalized structure:

- `counts`: map bitstring → integer
- `execution_time_sec`: float
- `metadata`: bounded, stable keys (backend id, device id, calibration snapshot refs, etc.)

Example:

```json
{
  "counts": {"00": 512, "11": 512},
  "execution_time_sec": 0.45,
  "metadata": {"backend": "sim:local"}
}
```

---

### 4.6 JobResults (Kernel/System API → user-facing envelope)

Contains:

- execution result summary (or QFS references),
- artifact references (Parquet and optional JSON),
- runtime metadata,
- async error visibility when applicable.

Large outputs MUST be returned via QFS references (not embedded raw payloads).

---

## 5. Primary Flow — Linear Job Execution (MVP)

### 5.1 Flow Summary


```text
Submit → Validate → Persist Inputs → Compile → Persist Compiled → Execute → Persist Results → Retrieve
```

MVP-stable contract surface includes:

- submission,
- compilation,
- execution,
- status polling,
- result retrieval,
- artifact persistence in QFS layout v1.0.

---

### 5.2 Detailed Runtime Sequence

```text
User
  ↓
CLI/SDK
  - reads job.yaml
  - resolves program source (path/inline/uri per JobSpec)
  - computes canonical hashes
  ↓
System API
  - validates request/authz
  - propagates trace context
  ↓
Kernel (QRTX)
  - creates job record + job_id
  - persists inputs into QFS
  - transitions lifecycle
  - calls compiler
  - persists compiled artifacts
  - calls Driver Manager
  - persists results + metadata
  ↓
System API
  - serves status/results using QFS refs
  ↓
User
```

---

## 6. Packaging & Submission Data Flow

### 6.1 Input Artifacts (MVP required)

MVP requires:

- `job.yaml`
- `program.eigen.py` (file-backed source is canonical in MVP)

Other program sources (`inline`, `uri`) may be supported by JobSpec, but if a deployment restricts them, rejection MUST be deterministic and MUST use canonical errors (`INVALID_ARGUMENT` or `PERMISSION_DENIED` depending on policy).

---

### 6.2 Deterministic Hashing

The CLI/SDK packaging layer MUST compute stable hashes:

- `source_sha256 = SHA-256(source_bytes)`
- optional: `job_yaml_sha256 = SHA-256(canonicalized_job_yaml_bytes)`

Canonicalization rules MUST include:

- normalized line endings,
- stable UTF-8 encoding,
- normalized relative paths.

---

### 6.3 Submission Request

Public submission uses `eigen.api.v1.JobService.SubmitJob`.

Contractual mapping from JobSpec to `SubmitJobRequest` is defined in `docs/reference/jobspec.md`.

---

## 7. System API (Public Gateway) Data Flow

System API responsibilities:

- validate request shape and required fields,
- enforce authn/authz policies (if enabled in deployment),
- enforce bounded metadata constraints,
- propagate trace context (W3C TraceContext),
- forward to Kernel (internal API).

Failure behavior:

- MUST be **gRPC-status-first** (no `success=false` wrappers),
- MUST use canonical statuses and structured details (see Section 10).

---

## 8. Kernel (QRTX) Orchestration & Persistence Data Flow

Kernel responsibilities:

1. Create job record and assign stable `job_id`.
2. Persist submission artifacts into QFS (CircuitFS layout v1.0).
3. Manage lifecycle transitions.
4. Trigger compilation.
5. Trigger execution.
6. Persist final outputs, logs, and error artifacts.
7. Serve status and results to System API.

---

### 8.1 QFS (CircuitFS) Layout (v1.0)

Reference: `docs/reference/qfs-layout.md`

Normative job root: `{qfs_root}/{job_id}/`

Canonical layout (abridged):

```text
{qfs_root}/{job_id}/
├── input/
│   ├── job.yaml
│   ├── program.eigen.py
│   └── metadata.json
├── compiled/
│   ├── circuit.aqo.json
│   ├── circuit.aqo.pb
│   ├── circuit.qasm
│   └── metadata.json
├── results/
│   ├── result.json
│   ├── manifest.json
│   └── error.json
└── results.parquet
```

Normative requirements:

- `input/job.yaml` and `input/program.eigen.py` MUST exist for every accepted job.
- `compiled/circuit.aqo.json` MUST exist after successful compilation.
- `results.parquet` MUST exist for successful jobs (`DONE`).
- `results/error.json` MUST exist for failed jobs (`ERROR`) when a durable failure is produced.

---

## 9. Compilation Data Flow (Kernel → Compiler Service)

Compiler Service responsibilities:

- parse and validate Eigen-Lang source,
- produce AQO v1.0 JSON (required),
- produce optional AQO protobuf and optional QASM,
- produce deterministic diagnostics,
- return metadata including hashes.

Compiler persistence:

- Kernel writes compiler outputs under:
  - `compiled/circuit.aqo.json` (required)
  - `compiled/circuit.aqo.pb` (optional)
  - `compiled/circuit.qasm` (optional)
  - `compiled/metadata.json` (optional)

Compiler failures:

- MUST map to canonical errors (`INVALID_ARGUMENT` for validation, `UNIMPLEMENTED` for unsupported feature, `INTERNAL` for invariant violations),
- MUST be deterministically reproducible for identical inputs.

---

## 10. Execution Data Flow (Kernel → Driver Manager → Backend)

Driver Manager responsibilities:

1. Accept `CircuitPayload`.
2. Select provider driver for the target backend.
3. Translate AQO/QASM to backend-native execution representation.
4. Execute against backend/simulator/hardware.
5. Normalize results into canonical `ExecutionResult`.
6. Normalize provider errors into canonical Eigen error model.

Execution persistence:

- Kernel persists successful outputs:
  - `results.parquet` (required on `DONE`)
  - `results/result.json` (optional extended metadata)
  - `results/manifest.json` (optional checksums + listing)
- Kernel persists failures:
  - `results/error.json` (recommended durable failure artifact)
  - optional logs under `logs/`

---

## 11. Result Retrieval Data Flow (User → System API → Kernel → QFS)

Retrieval paths:

- `GetJobStatus`: returns lifecycle state + timestamps + progress metadata.
- `GetJobResults`: returns result envelope + QFS references (Parquet primary).

Contract rules:

- Large artifacts MUST be referenced via QFS, not embedded.
- If results are requested before the job reaches terminal state:
  - MUST return `FAILED_PRECONDITION` (sync call behavior), OR
  - return an envelope that clearly indicates non-terminal state (only if the API contract defines it).
  - The canonical rule in Eigen OS is `FAILED_PRECONDITION` for “results not ready”.

---

## 12. Error and Failure Data Flow (Sync + Async)

### 12.1 Canonical Rule

Eigen OS is **gRPC-status-first**:

- transport failures use gRPC status codes,
- structured details use `google.rpc.*` types,
- payloads MUST NOT contain ad-hoc transport error wrappers.

Reference documents:

- `docs/reference/error-model.md`
- `docs/reference/error-mapping.md`

---

### 12.2 Async Failure Visibility (Terminal ERROR)

When a job ends with `ERROR`, the system MUST expose:

- terminal lifecycle: `ERROR`
- failure metadata:
  - `error_code` (stable machine-readable)
  - `error_summary` (human-readable)
  - `error_details_ref` (durable artifact reference, typically `results/error.json`)

---

### 12.3 Backend Failure Normalization

Provider-native failures MUST be normalized:

| **Provider failure class** | **Canonical mapping** |
|---|---|
| Provider unavailable / outage | `UNAVAILABLE` |
| Quota exceeded / throttling | `RESOURCE_EXHAUSTED` |
| Invalid authentication | `UNAUTHENTICATED` |
| Access denied | `PERMISSION_DENIED` |
| Provider timeout | `DEADLINE_EXCEEDED` |
| Provider internal fault | `INTERNAL` |

---

## 13. Observability and Telemetry Data Flow

### 13.1 Trace Propagation

Trace propagation uses:

- **W3C TraceContext**
- required metadata field: `traceparent`

Canonical propagation path:

```text
CLI/SDK → System API → Kernel → Compiler → Driver Manager → (backend boundary)
```

Rules:

- Trace context MUST be propagated across internal RPCs.
- Trace-level identifiers MUST NOT be used as Prometheus label values (bounded-cardinality rule).

---

### 13.2 Logs

Services SHOULD emit structured logs with:

- `trace_id` correlation,
- `job_id` correlation (as log fields, not metric labels),
- stage/lifecycle context.

---

### 13.3 Metrics

Metrics contracts are defined in dedicated documents:

- `orchestration-observability-contract.md`
- `cluster-runtime-observability-contract.md`
- `intelligent-runtime-observability-contract.md`
- `benchmark-observability-contract.md` (benchmarks)

This document’s requirement is data-flow correctness:

- key stage transitions and failures MUST be observable via metrics and traces,
- exporter failure MUST NOT break job execution.

---

## 14. Hybrid / VQE Iterative Data Flow

### 14.1 Pattern A — External Orchestration (Stable MVP Contract)

This is the canonical and safest MVP integration model.

Flow:

1. External optimizer selects parameters.
2. Parameters are injected into the job input/source.
3. Job is submitted.
4. Quantum execution runs.
5. Results are retrieved.
6. Optimizer computes next iteration.
7. Repeat.

Contract guarantee:

- Each iteration is a separate job with its own `job_id`.
- QFS artifacts form the audit trail for each iteration.

---

### 14.2 Pattern B — Kernel-Managed Hybrid Loop (Phase-1 extension)

Kernel-managed loops MAY exist as an implementation detail.

Constraints:

- MUST NOT be treated as a stable generalized DAG/orchestration contract unless explicitly versioned.
- If exposed, must include deterministic lineage and child-job relationships.

MVP guarantee remains Pattern A.

---

## 15. Benchmark Execution Data Flow (Phase-1 extension)

If the deployment includes benchmark APIs (e.g., `POST /benchmarks/run`), the benchmark runtime MUST:

- persist benchmark run snapshots and artifacts,
- expose run lifecycle and ingestion outcomes,
- follow benchmark observability contracts,
- remain idempotent when required by API contracts.

Benchmark data flow is intentionally separate from the core Job execution flow and must not weaken the JobSpec/QFS invariants.

---

## 16. Stable MVP Guarantees (Frozen)

The following behaviors are stable MVP contract surface:

1. Public gRPC submission flow (`eigen.api.v1`).
2. JobSpec v1.0 as canonical job descriptor (`job.yaml`).
3. Client-visible lifecycle state machine (per ТЗ).
4. Compiler → AQO v1.0 generation flow.
5. Driver Manager backend abstraction and result normalization.
6. QFS (CircuitFS) persistence per layout contract v1.0, including Parquet for successful jobs.
7. Canonical gRPC error model + deterministic mapping.
8. Trace propagation across core services.
9. Durable result and error artifacts.

---

## 17. Known Gaps and Future Hardening (Explicitly Non-Normative)

These areas are intentionally incomplete or future-phase:

- advanced multi-provider scheduling policies beyond MVP,
- full intelligent scoring + explainability linkage across submission → decision → explain endpoint,
- full semantic AST/type validation and stricter resource limits,
- fully standardized backend metadata keys across all drivers,
- uniform SLO definitions across all runtime profiles,
- generalized kernel-managed hybrid DAG orchestration.

These items MUST NOT change the stable MVP guarantees above without a versioned contract update.

---

## 18. Compatibility and Evolution Rules

Stable contract areas:

- public gRPC semantics,
- lifecycle states and transitions,
- AQO handoff semantics,
- QFS artifact layout and mandatory artifacts,
- canonical error model and mappings.

Rules:

- additive fields are backward compatible,
- breaking semantic changes require a version bump (SemVer discipline),
- changes to observability contracts require synchronized updates to dashboards, alerts, tests, and documentation.

---

## 19. Final Summary

Eigen OS implements a complete MVP execution pipeline:

```text
Submit → Compile → Execute → Persist → Retrieve
```

This document freezes the **data-flow contract** as the normative MVP baseline and the canonical integration reference for SDK/CLI and runtime development.
