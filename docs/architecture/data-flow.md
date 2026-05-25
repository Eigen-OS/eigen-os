# Eigen OS — Data Flow Specification

- **Document status:** Normative MVP architecture contract
- **Contract scope:** End-to-end runtime and artifact flow
- **Snapshot date:** 2026-05-24
- **Compatibility target:** Eigen OS MVP / Phase-0 and validated Phase-1 - extensions

---

## 1. Purpose and Scope

This document defines the canonical end-to-end data flow contract for Eigen OS.

It serves four purposes simultaneously:

1. Defines the intended architectural flow required by the technical specification (ТЗ).
2. Captures the implementation state already present in the repository.
3. Fixes current runtime and artifact semantics so downstream components can rely on stable behavior.
4. Explicitly separates stable MVP guarantees from future-phase TODO items.

The document covers:

- user submission flow,
- compilation flow,
- execution flow,
- result retrieval flow,
- hybrid/VQE iterative orchestration,
- artifact persistence semantics,
- observability and trace propagation.

This specification is aligned with:

- `docs/architecture/contract-map.md`
- `docs/reference/jobspec.md`
- `docs/reference/error-model.md`
- `docs/reference/error-mapping.md`

---

## 2. Architectural Scope

### 2.1 Runtime Components

| **Component** | **Responsibility** | **Current State** |
|---|---|---|
| `eigen-cli` | User interaction, packaging, local compile helpers | Implemented |
| System API | Public gRPC gateway, auth, validation | Implemented |
| Kernel (QRTX) | Orchestration, lifecycle, persistence coordination | Implemented |
| Compiler Service | AST-based compilation to AQO/QASM | Implemented |
| Driver Manager | Backend abstraction and execution | Implemented |
| Vendor Backend / Simulator | Actual execution target | Implemented |
| QFS (CircuitFS) | Artifact and result persistence | Implemented |
| Observability stack | Metrics, tracing, structured logs | Partially implemented |

### 2.2 Primary Data Domains

| **Data Domain** | **Description** |
|---|---|
| Job specification | User submission descriptor (`job.yaml`) |
| Program source | Eigen-Lang source (`program.eigen.py`) |
| Intermediate representation | AQO / QASM artifacts |
| Execution payload | Driver-consumable circuit payload |
| Runtime state | Job lifecycle and orchestration metadata |
| Result artifacts | Counts, metadata, derived outputs |
| Telemetry | Metrics, traces, structured logs |

---

## 3. High-Level Data Flow

### 3.1 Canonical Runtime Flow

```text
User
  │
  ▼
eigen-cli / SDK
  │
  ▼
System API
  │
  ▼
Kernel (QRTX)
  ├──► Compiler Service
  │         │
  │         ▼
  │      AQO/QASM
  │
  ├──► Driver Manager
  │         │
  │         ▼
  │   Vendor Backend / Simulator
  │
  ▼
QFS (CircuitFS)
  │
  ▼
User Results
```

### 3.2 Contracted Runtime Stages

The canonical client-visible lifecycle is:

```text
PENDING → COMPILING → QUEUED → RUNNING → DONE | ERROR | CANCELLED
```

Additional internal orchestration substates may exist but must not violate the public lifecycle contract.

---

## 4. Core Data Formats

### 4.1 JobSpec (`job.yaml`)

Canonical MVP submission descriptor.

Reference:

- `docs/reference/jobspec.md`

Current MVP rules:

- `apiVersion: eigen.os/v0.1`
- `kind: QuantumJob`
- file-backed source packaging is canonical
- inline source parsing exists but submission rejection is currently enforced

Example:

```text
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: h2-ground-state
spec:
  target: sim:local
  entrypoint: main
  program_path: program.eigen.py
```

---

### 4.2 Eigen-Lang Source

Primary hybrid quantum-classical source representation.

Typical file:

```text
program.eigen.py
```

Current compiler pipeline characteristics:

- AST-based parsing only,
- no arbitrary runtime execution,
- import allowlist enforcement,
- `@hybrid_program` validation,
- entrypoint validation.

---

### 4.3 AQO (Abstract Quantum Operations)

Primary intermediate representation exchanged between compiler and runtime.

Current MVP representation:

- JSON payload,
- optionally protobuf-wrapped,
- persisted in QFS.

Example:

```json
{
  "version": "0.1",
  "qubits": 2,
  "operations": [
    {"op": "H", "q": [0]},
    {"op": "CX", "q": [0,1]},
    {"op": "MEASURE", "q": [0,1], "c": [0,1]}
  ]
}
```

---

### 4.4 CircuitPayload

Canonical Driver Manager execution envelope.

Logical structure:

- `format`
- `payload bytes/ref`
- `shots`
- execution options
- optional metadata

Current supported formats:

- AQO JSON
- QASM (limited/partial depending on backend)

---

### 4.5 ExecutionResult

Normalized execution response returned by Driver Manager.

Example:

```json
{
  "counts": {
    "00": 512,
    "11": 512
  },
  "execution_time_sec": 0.45,
  "metadata": {
    "backend": "qiskit_aer_simulator"
  }
}
```

Current implementation state:

- counts normalization exists,
- backend metadata exists,
- metadata naming is not yet fully standardized across all drivers.

---

### 4.6 JobResults

Final user-facing result envelope.

Contains:

- execution results,
- artifact references,
- runtime metadata,
- optional error metadata.

Large artifacts must be referenced through QFS refs instead of embedded raw payloads.

---

## 5. Primary Flow — Linear Job Execution

### 5.1 Flow Summary

The MVP execution path is:

```text
Submit → Validate → Persist → Compile → Execute → Persist Results → Retrieve
```

The current repository already implements:

- submission,
- compilation,
- execution,
- polling/status,
- result retrieval,
- artifact persistence.

Advanced scheduling and multi-provider orchestration remain future-phase extensions.

---

### 5.2 Detailed Runtime Sequence

```text
User
  │
  ▼
eigen-cli
  │ Read job.yaml + source
  ▼
System API
  │ Validate/authenticate
  ▼
Kernel (QRTX)
  │ Persist source bundle
  │ Create job state
  │
  ├──► Compiler Service
  │         │ Compile
  │         ▼
  │      AQO/QASM
  │
  ├──► QFS
  │      compiled artifacts
  │
  ├──► Driver Manager
  │         │ Execute
  │         ▼
  │   Vendor Backend
  │
  ├──► QFS
  │      results.json
  │
  ▼
System API
  │
  ▼
User Results
```

---

### 5.3 Submission and Packaging Flow

#### Input Artifacts

Required MVP artifacts:

- `job.yaml`
- `program.eigen.py`

Current canonical packaging model:

- source is file-backed,
- CLI reads source locally,
- SHA-256 checksum is generated,
- source bundle is forwarded through `SubmitJobRequest`.

#### CLI Responsibilities

The CLI currently:

1. Parses `job.yaml`.
2. Resolves `program_path`.
3. Loads source bytes.
4. Computes source checksum.
5. Builds `SubmitJobRequest`.
6. Sends request to System API.

Current implementation note:

- inline source mode is parsed but rejected during mapping/packaging.

---

### 5.4 System API Flow

The System API acts as the public gateway.

Responsibilities:

- request validation,
- auth/authz enforcement,
- trace propagation,
- gRPC contract enforcement,
- forwarding to Kernel.

Current implementation state:

- gRPC public API exists,
- validation exists,
- trace propagation exists,
- canonical gRPC status mapping exists.

Errors follow:

- `INVALID_ARGUMENT`
- `FAILED_PRECONDITION`
- `NOT_FOUND`
- `UNAVAILABLE`
- other canonical mappings from `error-model.md`.

---

### 5.5 Kernel (QRTX) Orchestration Flow

Kernel responsibilities:

- lifecycle management,
- orchestration,
- persistence coordination,
- compiler execution coordination,
- backend execution coordination,
- artifact management.

Current implemented behavior:

1. Create job record.
2. Assign `job_id`.
3. Persist submission artifacts.
4. Transition lifecycle states.
5. Call compiler.
6. Call Driver Manager.
7. Persist results.
8. Surface status/results.

Current persistent artifacts include:

```text
qfs://jobs/<job_id>/
```

Typical artifact layout:

```text
job.yaml
source/program.eigen.py
compiled/compiled.aqo.json
compiled/compiled.qasm
results/results.json
results/error.json
logs/run.log
```

Some paths may vary slightly by deployment profile.

---

### 5.6 Compilation Flow

#### Compiler Responsibilities

Compiler Service performs:

- parsing,
- validation,
- transformation,
- AQO/QASM generation.

#### Compiler Validation Rules

Current implementation enforces:

- AST-based parsing,
- single `@hybrid_program`,
- import restrictions,
- entrypoint existence checks,
- basic semantic validation.

Current implementation limitations:

- validation is not yet fully AST-semantic,
- some checks are still substring/textual,
- size-limit enforcement is incomplete.

#### Compiler Output

Compiler returns:

- AQO payload,
- optional QASM,
- compiler metadata,
- statistics.

Artifacts are persisted into QFS.

---

### 5.7 Execution Flow

#### Driver Manager Responsibilities

Driver Manager:

- abstracts vendor backends,
- manages driver lifecycle,
- normalizes backend responses,
- maps backend failures to canonical runtime errors.

#### Execution Pipeline

1. Kernel selects/resolves target.
2. Driver Manager receives `CircuitPayload`.
3. Backend-specific driver is loaded.
4. AQO/QASM translated into backend-native representation.
5. Vendor SDK/runtime invoked.
6. Raw results normalized.
7. Normalized result returned to Kernel.

#### Backend Types

Current MVP supports:

- simulator backends,
- local execution profiles.

Hardware integration exists architecturally but is deployment/provider dependent.

---

### 5.8 Result Persistence and Retrieval

#### Result Persistence

Kernel persists:

- normalized results,
- metadata,
- optional logs,
- optional error artifacts.

Current durable error artifact contract:

```text
results/error.json
```

#### Result Retrieval

The retrieval flow is:

```text
User → CLI/SDK → System API → Kernel → QFS
```

Current implemented retrieval capabilities:

- polling status,
- result retrieval,
- artifact references,
- stream-like poll-based updates.

---

## 6. Hybrid/VQE Iterative Flow

### 6.1 Scope

Eigen OS supports hybrid quantum-classical workloads.

Primary MVP example:

- Variational Quantum Eigensolver (VQE)

The system currently supports two orchestration models.

---

### 6.2 Pattern A — External Orchestration (Stable MVP Contract)

This is the canonical and safest integration model.

#### Flow

1. External optimizer computes parameters.
2. Parameters injected into job input/source.
3. Job submitted.
4. Quantum execution performed.
5. Results retrieved.
6. Optimizer computes next iteration.
7. Loop repeats.

#### System Semantics

Eigen OS acts as:

- stateless execution substrate,
- independent-job runtime.

Each iteration is treated as a separate job.

#### Current State
- fully supported,
- production-safe,
- primary recommended integration model.

---

### 6.3 Pattern B — Kernel-Managed Hybrid Loop

#### Scope

Kernel-managed loops are partially implemented.

Current MVP support exists for:

- recognized VQE-like execution paths,
- persisted iteration metadata,
- final optimizer state persistence.

#### Planned Expanded Semantics

Future phases intend:

- generalized hybrid-loop orchestration,
- child-job lineage,
- optimizer plugins,
- parameterized AQO reuse,
- orchestration DAG execution.

#### Current Limitation

Pattern B must not yet be treated as a fully generalized stable contract.

Pattern A remains the normative external integration contract.

---

## 7. QFS (CircuitFS) Persistence Contract

### Purpose

QFS is the canonical persistence layer for:

- source artifacts,
- compiled artifacts,
- runtime outputs,
- logs,
- error artifacts,
- lineage metadata.

### Current MVP Backends

Typical implementations:

- S3/MinIO object storage,
- SQLite metadata/indexing.

Alternative backend implementations are allowed if they preserve artifact semantics.

### Artifact Guarantees

Current repository direction guarantees:

- stable job artifact namespace,
- durable result storage,
- durable error artifacts,
- artifact retrieval by refs.

---

## 8. Error and Failure Data Flow

### Canonical Rule

All runtime failures follow:

- gRPC status-first semantics,
- normalized backend errors,
- durable async error persistence.

Reference documents:

- `docs/reference/error-model.md`
- `docs/reference/error-mapping.md`

### Async Failure Contract

Async execution failures surface through:

- lifecycle state `ERROR`,
- `error_code`,
- `error_summary`,
- `error_details_ref`.

### Backend Failure Normalization

Driver/provider-native failures are normalized into canonical Eigen status classes.

Examples:

| **Failure** | **Canonical Mapping** |
|---|---|
| Provider unavailable | `UNAVAILABLE` |
| Quota exceeded | `RESOURCE_EXHAUSTED` |
| Invalid auth | `UNAUTHENTICATED` |
| Access denied | `PERMISSION_DENIED` |
| Internal backend fault | `INTERNAL` |

---

## 9. Observability and Telemetry Flow

### 9.1 Trace Propagation

Trace propagation uses:

- W3C TraceContext,
- `traceparent` propagation across services.

Current implemented flow:

```text
CLI → System API → Kernel → Compiler → Driver Manager
```

Telemetry enrichment includes:

- `trace_id`,
- `job_id`,
- `device_id`.

---

### 9.2 Logging

Structured logging exists across core services.

Current implementation state:

- structured logs implemented,
- trace correlation implemented,
- deployment topology for centralized collection remains environment-specific.

Current supported integrations may include:

- OpenTelemetry collector,
- Loki,
- Grafana.

---

### 9.3 Metrics

Prometheus-oriented metrics are implemented.

Current contract areas include:

- orchestration metrics,
- intelligent-runtime metrics,
- runtime execution metrics.

Related contracts:

- `orchestration-observability-contract.md`
- `intelligent-runtime-observability-contract.md`

Current limitation:

- some metric families and exporter wiring remain partially implemented.

---

## 10. Current MVP Guarantees

The following behaviors are considered stable MVP contract surface:

1. gRPC-based submission flow.
2. File-backed `job.yaml` packaging.
3. Kernel-managed lifecycle states.
4. Compiler AQO generation flow.
5. Driver Manager abstraction layer.
6. QFS artifact persistence.
7. Poll-based update streaming.
8. Canonical gRPC error semantics.
9. Trace propagation across runtime services.
10. Durable result and error artifacts.

---

## 11. Known Gaps and Future Hardening

The following areas remain intentionally incomplete or partially frozen.

### Runtime and Scheduling

- advanced scheduling policies,
- full multi-provider orchestration,
- dynamic backend health scoring,
- generalized hybrid orchestration DAGs.

### Compiler

- fully semantic AST validation,
- stronger type/schema validation,
- stricter source/resource limits.

### Driver Layer

- fully standardized backend metadata schema,
- richer execution telemetry,
- broader hardware-provider coverage.

### Observability

- unified canonical metric catalog,
- finalized SLO definitions,
- deployment-standardized telemetry topology.

### Hybrid Runtime

- generalized optimizer plugin model,
- parameterized AQO reuse semantics,
- stable child-job lineage contract.

---

## 12. Compatibility and Evolution Rules

### Stable Contract Areas

The following are considered public/runtime contract surface:

- public gRPC semantics,
- lifecycle states,
- AQO handoff semantics,
- QFS artifact semantics,
- canonical error mappings.

### Compatibility Rules

- additive fields are backward compatible,
- breaking protocol/runtime semantic changes require version bump,
- public gRPC contract changes require compatibility review.

---

## 13. Final State Summary

Eigen OS currently implements a complete MVP execution pipeline:

```text
Submit → Compile → Execute → Persist → Retrieve
```

The repository already includes:

- public API contracts,
- orchestration runtime,
- compiler pipeline,
- driver abstraction layer,
- artifact persistence,
- observability foundations,
- hybrid execution foundations.

Remaining work is primarily:

- hardening,
- normalization,
- CI conformance coverage,
- production-grade policy freezing,
- advanced orchestration expansion.

The data-flow model defined in this document is therefore treated as:

- the normative MVP architectural baseline,
- the reference integration model for SDK/runtime work,
- the authoritative runtime flow contract unless superseded by a versioned successor specification.
