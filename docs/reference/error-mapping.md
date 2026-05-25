# Error Mapping Matrix — Eigen OS 1.0

**Document status:** Normative
**Subsystem:** Public API, Kernel, Runtime, Compiler, Driver Manager, Distributed Runtime
**Contract version:** `1.0.0`

This document defines the canonical error mapping contract for Eigen OS 1.0.

The contract standardizes:

- gRPC status usage,
- structured error semantics,
- async job failure representation,
- backend/provider normalization,
- retryability semantics,
- distributed runtime failure mapping,
- compiler/runtime validation behavior,
- and cross-service determinism guarantees.

This document is normative for:

- public APIs,
- internal APIs,
- SDKs,
- CLI tooling,
- runtime services,
- orchestration services,
- distributed runtime infrastructure.

Related references:

- `docs/reference/error-model.md`
- `docs/reference/error-codes.md`
- `docs/reference/error-cases-by-rpc.md`
- `docs/reference/api/grpc-public.md`
- `docs/reference/api/grpc-internal.md`

---

## 1. Core Error Contract

Eigen OS uses a strict:

- gRPC-status-first,
- structured-details-first,
- deterministic-error-mapping

model.

Transport-level failures MUST use gRPC status codes.

RPC payloads MUST NOT implement:

- `success=false`,
- `ok=false`,
- ad-hoc error wrappers,
- transport-layer error objects.

---

## 2. Canonical Error Representation

Every failure MUST consist of:

1. gRPC status code,
2. canonical status message,
4. optional structured details,
5. stable machine-readable reason code,
6. optional remediation metadata.

---

## 3. Structured Error Details

Eigen OS standardizes usage of:

| **Detail Type** | **Purpose** |
|---|---|
| `google.rpc.BadRequest` | validation failures |
| `google.rpc.ErrorInfo` | stable machine-readable semantics |
| `google.rpc.ResourceInfo` | resource identity context |
| `google.rpc.RetryInfo` | retry guidance |
| `google.rpc.DebugInfo` | internal diagnostics |
| `google.rpc.Help` | operator remediation |
| `google.rpc.LocalizedMessage` | localization-safe user messaging |

---

## 4. Canonical Status Usage

### 4.1 INVALID_ARGUMENT

Use when:

- request invalid independently of runtime state.

Examples:

- malformed JobSpec,
- unsupported compiler syntax,
- invalid parameter ranges,
- missing required fields,
- malformed resource identifiers,
- invalid artifact references.

MUST include:

- `BadRequest`
- field violations.

Retryability:

- NOT retryable.

---

### 4.2 FAILED_PRECONDITION

Use when:

- request valid,
- but current system/resource state prevents execution.

Examples:

- requesting results before completion,
- illegal lifecycle transition,
- missing prerequisite artifact,
- attempting merge before all required shards available,
- cluster worker not ready.

Retryability:

- conditionally retryable after state transition.

---

### 4.3 NOT_FOUND

Use when:

- referenced resource does not exist.

Examples:

- unknown job,
- missing artifact,
- unknown worker,
- missing queue,
- deleted execution context.

Retryability:

- usually non-retryable,
- MAY be retryable under eventual consistency semantics.

---

### 4.4 ALREADY_EXISTS

Use when:

- resource creation conflicts with existing resource.

Examples:

- duplicate artifact upload,
- duplicate registration,
- duplicate job namespace allocation.

Retryability:

- NOT retryable unless request identity changes.

---

### 4.5 RESOURCE_EXHAUSTED

Use when:

- quota,
- concurrency,
- capacity,
- or throttling limits exceeded.

Examples:

- backend quota exceeded,
- execution concurrency exhausted,
- memory budget exhausted,
- cluster scheduling saturation.

Retryability:

- retryable with backoff.

MUST include:

- `RetryInfo`.

---

### 4.6 UNAVAILABLE

Use when:

- service temporarily unavailable.

Examples:

- provider outage,
- network partition,
- backend unavailable,
- transient control-plane failure.

Retryability:

- retryable with backoff.

MUST include:

- `RetryInfo`.

---

### 4.7 DEADLINE_EXCEEDED

Use when:

- operation exceeded deadline budget.

Examples:

- backend execution timeout,
- scheduler timeout,
- trace propagation timeout,
- distributed merge timeout.

Retryability:

- implementation-dependent.

---

### 4.8 PERMISSION_DENIED

Use when:

- authenticated identity lacks authorization.

Examples:

- forbidden namespace access,
- denied backend entitlement,
- unauthorized administrative action.

Retryability:

- NOT retryable without permission changes.

---

### 4.9 UNAUTHENTICATED

Use when:

- authentication invalid or absent.

Examples:

- invalid token,
- expired token,
- missing credentials,
- invalid runtime certificate.

Retryability:

- retryable after re-authentication.

---

### 4.10 UNIMPLEMENTED

Use when:

- feature unsupported.

Examples:

- unsupported compiler feature,
- unsupported runtime backend,
- unavailable orchestration policy,
- unsupported API version.

Retryability:

- NOT retryable without changing request.

---

### 4.11 INTERNAL

Use when:

- unexpected invariant violation occurs.

Examples:

- runtime panic,
- corrupted execution state,
- impossible scheduler state,
- unexpected compiler failure.

Retryability:

- implementation-dependent.

MUST include:

- correlation metadata.

---

### 4.12 ABORTED

Use when:

- optimistic concurrency conflict occurs.

Examples:

- lease conflict,
- transactional state race,
- distributed coordination conflict.

Retryability:

- retryable.

---

### 4.13 CANCELLED

Use when:

- caller or orchestration explicitly cancels operation.

Examples:

- user cancellation,
- orchestration cancellation,
- shutdown interruption.

Retryability:

- caller-defined.

---

## 5. Canonical Error Mapping Matrix

| **Scenario** | **Origin** | **Internal Mapping** | **Public Behavior** | **Retryability** |
|-------------------|-------------------|-------------------|-------------------|-------------------|
| Missing required field | API validation | `INVALID_ARGUMENT` | RPC failure | No |
| Invalid JobSpec | Compiler/parser | `INVALID_ARGUMENT` | RPC failure or async `ERROR` | No |
| Invalid artifact checksum | Artifact layer | `INVALID_ARGUMENT` | RPC failure | No |
| Unknown `job_id` | Kernel/QFS | `NOT_FOUND` | RPC failure | Conditional |
| Unknown shard | Distributed runtime | `NOT_FOUND` | RPC failure | No |
| Duplicate artifact upload | Artifact store | `ALREADY_EXISTS` | RPC failure | No |
| Results requested before completion | Runtime lifecycle | `FAILED_PRECONDITION` | RPC failure | Yes |
| Merge before quorum satisfied | Runtime merge layer | `FAILED_PRECONDITION` | RPC failure | Yes |
| Unsupported language feature | Compiler | `UNIMPLEMENTED` | RPC failure | No |
| Unsupported backend capability | Driver Manager | `UNIMPLEMENTED` | RPC failure | No |
| Backend unavailable | Provider/runtime | `UNAVAILABLE` | Async or sync failure | Yes |
| Backend throttling | Provider/runtime | `RESOURCE_EXHAUSTED` | Async or sync failure | Yes |
| Queue capacity exhausted | Distributed runtime | `RESOURCE_EXHAUSTED` | RPC failure | Yes |
| Scheduler saturation | Orchestrator | `RESOURCE_EXHAUSTED` | RPC failure | Yes |
| Lease conflict | Cluster runtime | `ABORTED` | RPC failure | Yes |
| Worker unavailable | Cluster runtime | `UNAVAILABLE` | RPC failure | Yes |
| Cluster partition | Distributed runtime | `UNAVAILABLE` | RPC failure | Yes |
| Deadline exceeded | Any service | `DEADLINE_EXCEEDED` | RPC failure | Conditional |
| Invalid authentication | Auth layer | `UNAUTHENTICATED` | RPC failure | Yes |
| Permission denied | Authorization layer | `PERMISSION_DENIED` | RPC failure | No |
| Runtime invariant violation | Any service | `INTERNAL` | RPC failure | Conditional |
| Explicit cancellation | Caller/runtime | `CANCELLED` | RPC failure | Caller-defined |

---

## 6. Async Job Failure Contract

Asynchronous execution failures MUST be represented by BOTH:

1. lifecycle state:
   - ERROR

AND

2. structured failure metadata.

### 6.1 Required Async Failure Fields

Async failures MUST expose at least one of:

| **Field** | **Purpose** |
|---|---|
| `error_code` | stable machine-readable code |
| `error_summary` | human-readable summary |
| `error_details_ref` | durable artifact reference |

---

### 6.2 Durable Error Artifacts

Durable failure artifacts SHOULD be stored under:

```text
qfs://jobs/<job_id>/results/error.json
```

Artifacts MAY include:

- stack traces,
- backend diagnostics,
- retry metadata,
- trace references,
- scheduling rationale,
- distributed failure lineage.

---

## 7. Backend Normalization Contract

Backend/provider-native failures MUST be normalized before public exposure.

Raw provider payloads MUST NOT leak directly into:

- public APIs,
- SDK contracts,
- orchestration decisions.

---

### 7.1 Normalized Backend Error Envelope

Backend-facing failures MUST include:

```text
google.rpc.ErrorInfo
```

with:

| **Field** | **Requirement** |
|---|---|
| `reason` | stable `EIGEN_BACKEND_*` code |
| `domain` | owning subsystem |
| `metadata.taxonomy` | normalized category |
| `metadata.remediation` | remediation hint |
| `metadata.correlation_id` | incident correlation |
| `metadata.trace` | optional trace reference |
| `metadata.job_timeline` | optional timeline artifact |

---

### 7.2 Backend Taxonomy

Allowed taxonomy values:

- `provider`
- `network`
- `auth`
- `quota`
- `capacity`
- `runtime`
- `internal`

---

### 7.3 Canonical Backend Reason Codes

| **Backend Condition** | **Requirement** | **Requirement** |
|---|---|---|
| Invalid token | `UNAUTHENTICATED` | `EIGEN_BACKEND_AUTH` |
| Access denied | `PERMISSION_DENIED` | `EIGEN_BACKEND_AUTHZ` |
| Provider outage | `UNAVAILABLE` | `EIGEN_BACKEND_UNAVAILABLE` |
| Quota exceeded | `RESOURCE_EXHAUSTED` | `EIGEN_BACKEND_QUOTA` |
| Capacity exhausted | `RESOURCE_EXHAUSTED` | `EIGEN_BACKEND_CAPACITY` |
| Unsupported provider feature | `UNIMPLEMENTED` | `EIGEN_BACKEND_PROVIDER` |
| Invalid provider payload | `INVALID_ARGUMENT` | `EIGEN_BACKEND_INVALID_ARGUMENT` |
| Timeout | `DEADLINE_EXCEEDED` | `EIGEN_BACKEND_TIMEOUT` |
| Internal provider fault | `INTERNAL` | `EIGEN_BACKEND_INTERNAL` |

---

## 8. Distributed Runtime Failure Mapping

Distributed runtime semantics introduce additional failure classes.

### 8.1 Lease Failures

| **Condition** | **Status** |
|---|---|
| Lease expired | `ABORTED` |
| Lease conflict | `ABORTED` |
| Lease ownership invalid | `FAILED_PRECONDITION` |

---

### 8.2 Queue Failures

| **Condition** | **Status** |
|---|---|
| Queue unavailable | `UNAVAILABLE` |
| Queue overloaded | `RESOURCE_EXHAUSTED` |
| Invalid queue state | `FAILED_PRECONDITION` |

---

### 8.3 Merge Failures

| **Condition** | **Status** |
|---|---|
| Parent mismatch | `FAILED_PRECONDITION` |
| Duplicate shard envelope | `INVALID_ARGUMENT` |
| Missing quorum | `FAILED_PRECONDITION` |
| Invalid merge artifact | `INVALID_ARGUMENT` |

---

## 9. Retryability Contract

SDKs and clients MUST treat retryability deterministically.

### 9.1 Retryable Statuses

Typically retryable:

- `UNAVAILABLE`
- `RESOURCE_EXHAUSTED`
- `ABORTED`
- `DEADLINE_EXCEEDED`

Conditionally retryable:

- `FAILED_PRECONDITION`
- `NOT_FOUND`

---

### 9.2 Non-Retryable Statuses

Typically non-retryable:

- `INVALID_ARGUMENT`
- `UNIMPLEMENTED`
- `PERMISSION_DENIED`

---

## 10. Correlation & Traceability

All distributed/runtime failures SHOULD expose:

- correlation ID,
- trace ID,
- execution timeline reference,
- shard lineage (if applicable).

Distributed failures SHOULD remain traceable across:

- scheduler,
- dispatcher,
- worker,
- merge pipeline,
- artifact storage,
- replay systems.

---

## 11. SDK & CLI Requirements

SDKs MUST consistently expose:

1. gRPC status code,
2. canonical message,
3. structured details,
4. retryability semantics,
5. correlation metadata.

CLI tooling SHOULD:

- render validation failures clearly,
- expose remediation hints,
- display retry guidance,
- preserve structured diagnostics.

---

## 12. Conformance Requirements

CI MUST validate:

1. deterministic status mapping,
2. stable reason codes,
3. structured detail presence,
4. retryability correctness,
5. async failure envelope presence,
6. distributed-runtime failure normalization.

Required golden tests:

- validation failures,
- precondition failures,
- backend transient failures,
- auth/authz failures,
- distributed runtime conflicts,
- merge failures,
- quota failures,
- timeout behavior.

---

## 13. Operational Invariants

The following invariants are mandatory.

### Deterministic Mapping

The same failure class MUST map to the same canonical status.

### No Wrapper Errors

RPC bodies MUST NOT encode transport failures.

### Stable Reason Codes

Reason codes MUST remain stable within MAJOR versions.

### Backend Normalization

Provider-native failures MUST be normalized before public exposure.

### Async Failure Visibility

Async failures MUST remain inspectable after runtime completion.

### Traceability

Distributed/runtime failures MUST remain correlatable across services.

---

## 14. Migration & Compatibility Rules

### Additive Evolution

New:

- reason codes,
- metadata fields,
- structured detail fields

MAY be added in MINOR releases.

### Deprecation Policy

Deprecated reason codes MUST:

- remain functional for at least one MINOR release,
- remain documented,
- include migration guidance.

### Breaking Changes

Breaking changes require:

- MAJOR version bump,
- SDK compatibility updates,
- CLI compatibility updates,
- migration documentation,
- conformance test updates.

---

## 15. Minimum Closure Criteria

The Eigen OS error contract is considered fully realized only when:

1. all RPCs use deterministic canonical status mapping,
2. all runtime services normalize backend/provider failures,
3. structured detail schemas are frozen,
4. retryability semantics are standardized,
5. distributed runtime failures are fully mapped,
6. SDKs expose structured failure semantics consistently,
7. CI validates end-to-end mapping determinism,
8. async failure artifacts remain durable and inspectable.
