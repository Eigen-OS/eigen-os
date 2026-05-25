# Contract Map

- **Document status:** Normative architecture contract
- **Contract scope:** MVP → Phase-5 runtime evolution baseline
- **Contract type:** End-to-end system interface map
- **Last updated:** 2026-05-24

---

## 1. Purpose

This document defines the canonical end-to-end contract topology of Eigen OS:

```text
User → SDK/CLI → System API → Kernel/QRTX
→ Compiler / Driver Manager / Runtime
→ Backend / Simulator / Hardware
→ QFS / Results / Observability
→ User
```

The document serves as:

- the authoritative architectural interface map,
- the canonical boundary definition between services,
- the normative source for API/runtime interaction semantics,
- the compatibility baseline for MVP and post-MVP evolution.

This document intentionally includes:

1. required architecture contracts from the original MVP specification,
2. currently implemented runtime/API behavior,
3. additive functionality implemented beyond the original MVP scope.

This document is normative unless explicitly marked otherwise.

---

## 2. System Architecture Boundaries

### 2.1 External Client Layer

#### Components

- `eigen-cli`
- SDKs
- automation/integration clients

#### Responsibilities

- construct and submit jobs,
- package JobSpec artifacts,
- propagate tracing/auth metadata,
- observe lifecycle/results,
- interact with public APIs only.

#### Public contract namespace

```text
eigen.api.v1
```

---

### 2.2 Public Gateway Layer

#### Component

System API

#### Responsibilities

- public gRPC API exposure,
- authentication/authorization,
- request validation,
- request normalization,
- lifecycle/result serving,
- trace propagation,
- orchestration delegation.

#### Contract type

Stable public API surface.

---

### 2.3 Orchestration Layer

#### Component

Kernel / QRTX

#### Responsibilities

- job lifecycle orchestration,
- DAG/state management,
- runtime scheduling,
- compiler coordination,
- execution coordination,
- distributed runtime orchestration,
- artifact persistence coordination,
- queue/resource management.

#### Internal contract namespace

```text
eigen.internal.v1
```

---

### 2.4 Compilation Layer

#### Component

CompilationService

#### Responsibilities

- Eigen-Lang compilation,
- AQO/QASM generation,
- optimization pipeline execution,
- compilation diagnostics,
- artifact generation.

---

### 2.5 Execution Layer

#### Component

DriverManagerService

#### Responsibilities

- backend abstraction,
- vendor integration,
- execution dispatch,
- execution normalization,
- device metadata,
- calibration/state access.

---

### 2.6 Backend Layer

#### Components

- local simulators,
- vendor simulators,
- cloud providers,
- hardware backends.

#### Notes

Backend APIs are vendor-specific and are normalized through Driver Manager contracts before exposure to public/runtime layers.

---

### 2.7 Artifact Layer

#### Component

QFS (CircuitFS)

#### Responsibilities

- durable artifact persistence,
- compiled artifact storage,
- execution result storage,
- logs/error persistence,
- timeline/provenance persistence.

#### MVP storage profile

- S3/MinIO-compatible object storage,
- SQLite metadata/state layer.

---

## 3. Canonical API Namespaces

### 3.1 Public APIs

Canonical namespace:

```text
eigen.api.v1
```

#### Public services

- `JobService`
- `DeviceService`
- `KnowledgeBaseService`

---

### 3.2 Internal APIs

Canonical namespace:

```text
eigen.internal.v1
```

#### nternal services

- `KernelGatewayService`
- `CompilationService`
- `DriverManagerService`

---

## 4. Versioning and Compatibility

### 4.1 Public API Compatibility

Public APIs are treated as stable contracts.

#### Breaking changes require:

- new package version,
- compatibility coexistence period,
- explicit migration documentation.

#### Breaking changes include:

- renaming package/service/method,
- field semantic changes,
- field removals,
- incompatible enum/state changes.

---

### 4.2 Non-Breaking Changes

Allowed additive changes:

- optional request/response fields,
- additional RPCs,
- additional metadata,
- additive observability labels with bounded cardinality.

---

### 4.3 Internal Contract Compatibility

Internal APIs follow SemVer-style compatibility discipline and must remain synchronized with runtime orchestration semantics.

---

### 4.4 Job Specification Versioning

Current JobSpec contract:

```yaml
apiVersion: eigen.os/v0.1
```

Canonical job descriptor:

```text
job.yaml
```

---

## 5. End-to-End Execution Flow

### 5.1 Submit Flow

```text
Client
→ SubmitJob
→ System API
→ Kernel/QRTX
→ enqueue lifecycle
→ persist metadata/artifacts
```

#### Submit guarantees
- request validation occurs before orchestration,
- accepted jobs receive stable `job_id`,
- trace context is propagated,
- orchestration state is persisted.

--- 

### 5.2 Compilation Flow

```text
Kernel/QRTX
→ CompilationService
→ compiled artifacts
→ QFS persistence
```

#### Generated artifacts may include

- AQO,
- QASM,
- compiler metadata,
- diagnostics,
- optimization artifacts.

---

### 5.3 Execution Flow

```text
Kernel/QRTX
→ DriverManagerService
→ backend/simulator/hardware
→ normalized execution result
```

#### Driver Manager responsibilities

- backend normalization,
- payload normalization,
- retry/error normalization,
- execution metadata normalization.

---

### 5.4 Results Flow

```text
Client
→ GetJobResults
→ System API
→ Kernel/QRTX
→ QFS artifact retrieval
→ normalized response
```

Large artifacts are returned through QFS references rather than raw payload embedding.

---

## 6. Job Lifecycle Contract

### 6.1 Stable Client-Facing States

Canonical public lifecycle:

```text
PENDING
→ COMPILING
→ QUEUED
→ RUNNING
→ DONE | ERROR | CANCELLED
```

---

### 6.2 Runtime Guarantees

#### PENDING

Job accepted but not yet executing.

#### COMPILING

Compilation pipeline executing.

#### QUEUED

Awaiting runtime/backend scheduling.

#### RUNNING

Execution active on runtime/backend.

#### DONE

Execution completed successfully.

#### ERROR

Terminal failure state with normalized error envelope.

#### CANCELLED

Execution cancelled before completion.

---

## 7. Public API Contracts

### 7.1 JobService

#### Stable RPC Surface

- `SubmitJob`
- `GetJobStatus`
- `CancelJob`
- `StreamJobUpdates`
- `GetJobResults`
- `GetDispatchRationale`

---

#### SubmitJob

**Input**

`SubmitJobRequest`

#### Required fields

- `name`
- `program`
- `target`

#### Optional fields

- `priority`
- `compiler_options`
- `metadata`

**Output**

```text
SubmitJobResponse {
  job_id,
  accepted_at
}
```

#### Semantics

- creates orchestration job,
- validates request before enqueue,
- may persist artifacts to QFS,
- propagates trace/auth context.

---

#### GetJobStatus

Returns:

- lifecycle state,
- progress,
- stage,
- timestamps,
- optional runtime messages.

---

#### CancelJob

**Contract**

Cancellation is:

- allowed for `PENDING`,
- allowed for `COMPILING`,
- allowed for `QUEUED`,
- best-effort for `RUNNING`.

Terminal jobs return deterministic terminal semantics.

---

#### GetJobResults

Returns:

- normalized results,
- artifact references,
- execution metadata,
- async error information when applicable.

---

#### StreamJobUpdates

**MVP implementation**

Poll-based streaming.

**Contract guarantee**

Clients receive ordered lifecycle updates reflecting Kernel runtime state progression.

---

#### GetDispatchRationale

Returns explainability/scheduling rationale metadata for orchestration/runtime decisions.

---

### 7.2 DeviceService

#### Stable RPC Surface

- `ListDevices`
- `GetDeviceStatus`
- `GetDeviceDetails`
- `ReserveDevice`

---

#### Device Metadata

Device contracts may expose:

- availability,
- queue depth,
- calibration state,
- estimated wait,
- backend capabilities,
- scheduling metadata.

---

#### ReserveDevice Semantics

Reservation applies to scheduler/runtime orchestration capacity rather than exclusive hardware ownership.

---

### 7.3 KnowledgeBaseService

#### Stable RPC Surface

- `UpsertRecord`
- `BatchUpsertRecords`
- `QueryRecords`
- `GetRecord`

---

#### Contract Version

```text
1.0.0
```

---

#### Stable Error Taxonomy

- `KB_INVALID_ARGUMENT`
- `KB_NOT_FOUND`
- `KB_INDEX_UNAVAILABLE`
- `KB_RATE_LIMITED`
- `KB_INTERNAL`

---

## 8. Internal Service Contracts

### 8.1 KernelGatewayService

#### Responsibilities

- enqueue jobs,
- expose orchestration lifecycle,
- cancellation,
- result retrieval,
- runtime coordination.

---

#### Semantic Rule

Internal lifecycle semantics must remain compatible with public API semantics.

---

### 8.2 CompilationService

#### Stable Operations

**Compile**

Input:

- program,
- target,
- options.

Output:

- compiled artifact,
- metadata,
- stats,
- normalized payload format.

---

### 8.3 DriverManagerService

#### Stable Operations

- `ListDevices`
- `GetDeviceStatus`
- `ExecuteCircuit`
- `CalibrateDevice`

---

#### ExecuteCircuit Responsibilities

- backend dispatch,
- result normalization,
- timing metadata,
- backend error normalization.

---

## 9. QFS Artifact Contract

### Canonical Artifact Types

- compiled circuits,
- AQO artifacts,
- results,
- logs,
- timelines,
- diagnostics,
- error artifacts.

---

### Stable Artifact Expectations

#### Results

```text
results.json
```

#### Error artifacts

```text
results/error.json
```

#### Timeline artifacts

```text
timeline.json
```

---

## 10. Error Contract

Eigen OS uses:

```text
gRPC-status-first semantics
```

Transport-level failures must not be encoded through:

```json
success=false
```

style wrappers.

---

### Canonical Status Rules

#### INVALID_ARGUMENT

Invalid request independent of runtime state.

#### FAILED_PRECONDITION

Valid request blocked by runtime/system state.

#### RESOURCE_EXHAUSTED

Quota/capacity exhaustion.

#### UNAVAILABLE

Transient backend/runtime unavailability.

#### DEADLINE_EXCEEDED

Timeout/deadline breach.

#### NOT_FOUND

Missing resource identity.

#### UNAUTHENTICATED / PERMISSION_DENIED

Authentication/authorization failures.

---

### Structured Error Details

Recommended structured details:

- `google.rpc.BadRequest`
- `google.rpc.ErrorInfo`
- `google.rpc.ResourceInfo`
- `google.rpc.RetryInfo`

---

### Backend Error Normalization

Vendor/provider failures must be normalized before reaching public contracts.

---

## 11. Tracing and Correlation

### Trace Propagation

Canonical propagation format:

```text
W3C TraceContext
```

Primary metadata field:

```text
traceparent
```

---

### Required Correlation Metadata

Where applicable:

- `trace_id`
- `job_id`
- `device_id`
- correlation identifiers.

---

## 12. Timeout and Deadline Semantics

### External RPCs

Clients set deadlines.

### Internal propagation

System API propagates deadlines downstream.

### Long-running operations

Long-running execution must use async orchestration semantics rather than indefinite RPC blocking.

---

## 13. Observability Architecture

### Supported telemetry

- Prometheus metrics,
- OpenTelemetry traces,
- structured logs.

---

### Observability Coverage Areas

- orchestration observability,
- runtime observability,
- intelligent runtime observability,
- cluster runtime observability,
- benchmark observability.

---

### Runtime Expectations

All runtime services should expose:

- metrics,
- traces,
- lifecycle-correlated logs.

---

## 14. Interface Matrix

### 14.1 External Layer

| **Caller** | **Callee** | **Contract** | **Operations** |
|---|---|---|---|
| SDK / CLI | System API | `eigen.api.v1` | submit/status/results |
| SDK / CLI | System API | `eigen.api.v1` | streaming updates |
| SDK / CLI | System API | `eigen.api.v1` | device operations |

---

### 14.2 Orchestration Layer

| **Caller** | **Callee** | **Contract** | **Operations** |
|---|---|---|---|
| System API | Kernel/QRTX | `eigen.internal.v1` | enqueue/status/results |
| Kernel/QRTX | CompilationService | `eigen.internal.v1` | compile |
| Kernel/QRTX | DriverManagerService | `eigen.internal.v1` | execute |
| Kernel/QRTX | QFS | internal IO | artifacts/results |

---

### 14.3 Backend Layer

| **Caller** | **Callee** | **Contract** |
|---|---|---|
| DriverManagerService |backend/vendor | vendor-specific |
| backend/vendor | DriverManagerService | normalized response |

---

## 15. Operational and CI Requirements

### Proto Compatibility

CI should enforce:

- `buf lint`
- `buf breaking`

### Contract Consistency

Changes affecting:

- metrics,
- APIs,
- runtime semantics,
- dashboards,
- alerts,

must be updated in the same change set.

---

## 16. Production Hardening Targets

The following remain required for full production-grade contract freeze:

1. Full runtime topology synchronization across architecture docs.
2. Unified retry/deadline governance.
3. Full cross-service conformance testing.
4. Runtime/observability contract CI validation.
5. Distributed runtime orchestration hardening.
6. Deterministic explainability/runtime reasoning semantics.

---

## 17. MVP Success Criterion

The baseline MVP success flow is:

```text
eigen-cli submit --job job.yaml
```

followed by successful:

- validation,
- orchestration,
- compilation,
- execution,
- result persistence,
- observability/tracing,
- result retrieval.

The full path must operate deterministically end-to-end across the supported simulator/runtime profile.
