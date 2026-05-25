# Error Model — Eigen OS 1.0

**Document status:** Normative
**Subsystem:** Public API, Internal API, Runtime, Compiler, Driver Manager, Distributed Runtime
**Contract version:** `1.0.0`

This document defines the canonical error model for Eigen OS 1.0.

The error model standardizes:

- transport-level failure semantics,
- structured error representation,
- deterministic status mapping,
- retryability semantics,
- backend normalization,
- distributed runtime failure behavior,
- async execution failure visibility,
- and client interoperability guarantees.

This document is normative for:

- public APIs,
- internal APIs,
- SDKs,
- CLI tooling,
- runtime services,
- orchestration systems,
- distributed runtime infrastructure.

For detailed scenario-level mappings, see:

- `docs/reference/error-mapping.md`
- `docs/reference/error-cases-by-rpc.md`

---

## 1. Core Principles

Eigen OS follows a strict:

- gRPC-status-first,
- structured-details-first,
- deterministic-error-contract

model.

The same failure class MUST always map to the same canonical semantics.

---

### 1.1 Transport-Level Failure Semantics

RPC failures MUST be represented using canonical gRPC status codes:

Examples:

- `INVALID_ARGUMENT`
- `FAILED_PRECONDITION`
- `NOT_FOUND`
- `UNAVAILABLE`
- `RESOURCE_EXHAUSTED`
- `INTERNAL`

RPC payloads MUST NOT implement:

- `success=false`
- `ok=false`
- embedded transport error wrappers
- transport-level error payload fields

Transport semantics belong exclusively to:

- gRPC status,
- structured status details.

---

### 1.2 Deterministic Mapping

The same failure category MUST:

- map to the same gRPC status,
- expose the same reason-code family,
- preserve retryability semantics,
- preserve structured detail semantics.

Determinism is mandatory across:

- services,
- SDKs,
- runtime components,
- orchestration systems,
- distributed execution environments.

---

### 1.3 Structured Error Semantics

Structured semantics SHOULD be encoded via:

```text
google.rpc.Status
```

using standardized detail types.

Structured details are mandatory for:

- validation failures,
- retryable transient failures,
- distributed runtime failures,
- normalized backend/provider failures.

---

### 1.4 Async Failure Visibility

Asynchronous execution failures MUST be represented by BOTH:

1. lifecycle state:
   - `ERROR`

AND

2. durable or inspectable failure metadata.

Minimum required visibility:

| **Field** | **Purpose** |
|---|---|
| `error_code` | stable machine-readable failure code |
| `error_summary` | human-readable summary |
| `error_details_ref` | durable artifact reference |

---

## 2. Canonical Status Model

### 2.1 INVALID_ARGUMENT

Use when:

- request invalid independently of runtime state.

Examples:

- malformed JobSpec,
- invalid syntax,
- unsupported format version,
- invalid field ranges,
- malformed resource references.

Characteristics:

- deterministic,
- non-retryable,
- validation-originated.

Required details:

- `google.rpc.BadRequest`

---

### 2.2 FAILED_PRECONDITION

Use when:

- request valid,
- but current state prevents execution.

Examples:

- requesting results before terminal completion,
- illegal lifecycle transition,
- unavailable prerequisite artifact,
- merge quorum not satisfied,
- invalid runtime phase.

Characteristics:

- state-dependent,
- conditionally retryable.

This status MUST remain semantically distinct from:

- `INVALID_ARGUMENT`.

---

### 2.3 NOT_FOUND

Use when:

- referenced resource does not exist.

Examples:

- unknown job,
- missing artifact,
- unknown shard,
- missing runtime resource.

Characteristics:

- deterministic,
- potentially retryable under eventual consistency.

### 2.4 RESOURCE_EXHAUSTED

Use when:

- quota,
- capacity,
- concurrency,
- or throttling limits exceeded.

Examples:

- backend quota exceeded,
- cluster saturation,
- memory exhaustion,
- queue capacity exhaustion.

Required details:

- `google.rpc.RetryInfo`

---

### 2.5 UNAVAILABLE

Use when:

- service temporarily unavailable.

Examples:

- provider outage,
- runtime unavailable,
- cluster partition,
- transient network failure.

Required details:

- `google.rpc.RetryInfo`

---

### 2.6 DEADLINE_EXCEEDED

Use when:

- operation exceeds deadline budget.

Examples:

- execution timeout,
- scheduling timeout,
- distributed merge timeout,
- backend response timeout.

---

### 2.7 UNAUTHENTICATED

Use when:

- authentication invalid or absent.

Examples:

- expired token,
- invalid credentials,
- invalid runtime certificate.

---

### 2.8 PERMISSION_DENIED

Use when:

- authenticated identity lacks authorization.

Examples:

- forbidden namespace access,
- unauthorized runtime action,
- restricted administrative operation.

---

### 2.9 UNIMPLEMENTED

Use when:

- requested feature unsupported.

Examples:

- unsupported compiler feature,
- unsupported backend capability,
- unavailable orchestration policy.

---

### 2.10 INTERNAL

Use when:

- unexpected invariant violation occurs.

Examples:

- runtime panic,
- corrupted scheduler state,
- impossible execution state,
- invariant violation.

Internal failures SHOULD expose:

- correlation metadata,
- traceability metadata,
- diagnostic references.

---

### 2.11 ABORTED

Use when:

- distributed coordination conflict occurs.

Examples:

- lease conflicts,
- optimistic concurrency conflicts,
- transactional race conditions.

---

### 2.12 CANCELLED

Use when:

- operation explicitly cancelled.

Examples:

- user cancellation,
- orchestration cancellation,
- runtime shutdown interruption.

---

## 3. Structured Error Detail Model

Eigen OS standardizes the following structured detail types.

### 3.1 Validation Failures

Validation failures MUST include:

```text
google.rpc.BadRequest
```

with one or more:

```text
FieldViolation
```

entries.

Each violation MUST contain:

| **Field** | **Requirement** |
|---|---|
| `field` | stable field path |
| `description` | actionable explanation |

---

### 3.2 Retry Semantics

Retryable failures SHOULD include:

```text
google.rpc.RetryInfo
```

Retry metadata MAY include:

- retry delay,
- retry class,
- retry budget hints.

---

### 3.3 Resource Context

Resource-oriented failures SHOULD include:

```text
google.rpc.ResourceInfo
```

Examples:

- job references,
- artifact references,
- queue references,
- worker identity.

---

### 3.4 Stable Machine Semantics

Machine-readable semantics MUST use:

```text
google.rpc.ErrorInfo
```

Required fields:

| **Field** | **Requirement** |
|---|---|
| `reason` | stable `EIGEN_*` code |
| `domain` | owning subsystem |
| `metadata` | optional structured metadata |

---

### 3.5 Diagnostic Context

Internal/runtime failures MAY include:

```text
google.rpc.DebugInfo
```

Production deployments SHOULD redact:

- secrets,
- credentials,
- unsafe provider payloads.

---

## 4. Backend Normalization Model

Provider/backend-native failures MUST be normalized before public exposure.

Raw provider semantics MUST NOT directly leak into:

- public APIs,
- SDK contracts,
- orchestration decisions.

### 4.1 Normalized Backend Envelope

Backend-facing failures MUST include:

```text
google.rpc.ErrorInfo
```

with:

| **Field** | **Requirement** |
|---|---|
| `reason` | stable `EIGEN_*` code |
| `domain` | `eigen.driver_manager` or owning subsystem |
| `metadata.taxonomy` | normalized category |
| `metadata.remediation` | remediation hint |
| `metadata.correlation_id` | incident correlation |
| `metadata.trace` | optional trace reference |
| `metadata.job_timeline` | optional timeline reference |

---

### 4.2 Backend Taxonomy

Allowed normalized taxonomy values:

- `provider`
- `network`
- `auth`
- `quota`
- `capacity`
- `runtime`
- `internal`

---

### 4.3 Canonical Backend Reason Codes

| **Condition** | **Status** | **Reason** |
|---|---|---|
| Invalid token | `UNAUTHENTICATED` | `EIGEN_BACKEND_AUTH` |
| Access denied | `PERMISSION_DENIED` | `EIGEN_BACKEND_AUTHZ` |
| Provider unavailable | `UNAVAILABLE` | `EIGEN_BACKEND_UNAVAILABLE` |
| Quota exceeded | `RESOURCE_EXHAUSTED` | `EIGEN_BACKEND_QUOTA` |
| Capacity exhausted | `RESOURCE_EXHAUSTED` | `EIGEN_BACKEND_CAPACITY` |
| Unsupported operation | `UNIMPLEMENTED` | `EIGEN_BACKEND_PROVIDER` |
| Invalid provider payload | `INVALID_ARGUMENT` | `EIGEN_BACKEND_INVALID_ARGUMENT` |
| Timeout | `DEADLINE_EXCEEDED` | `EIGEN_BACKEND_TIMEOUT` |
| Internal provider failure | `INTERNAL` | `EIGEN_BACKEND_INTERNAL` |

---

## 5. Distributed Runtime Error Semantics

Distributed execution introduces additional failure categories.

### 5.1 Queue Failures

Examples:

- queue unavailable,
- queue overload,
- invalid lease state,
- replay corruption.

Canonical statuses:

- `UNAVAILABLE`
- `RESOURCE_EXHAUSTED`
- `FAILED_PRECONDITION`

---

### 5.2 Lease & Coordination Failures

Examples:

- lease expiration,
- lease ownership conflict,
- concurrent merge conflict.

Canonical statuses:

- `ABORTED`
- `FAILED_PRECONDITION`

---

### 5.3 Merge Failures

Examples:

- quorum not reached,
- duplicate shard envelope,
- parent mismatch,
- invalid merge artifact.

Canonical statuses:

- FAILED_PRECONDITION
- INVALID_ARGUMENT

---

### 5.4 Cluster Runtime Failures

Examples:

- worker unavailable,
- node partition,
- scheduling collapse,
- orchestration saturation.

Canonical statuses:

- UNAVAILABLE
- RESOURCE_EXHAUSTED

---

## 6. Async Error Artifact Model

Async execution failures MUST remain inspectable after runtime completion.

### 6.1 Durable Error Artifacts

Durable failure artifacts SHOULD be stored under:

```text
qfs://jobs/<job_id>/results/error.json
```

Artifacts MAY include:

- runtime diagnostics,
- provider diagnostics,
- trace references,
- retry metadata,
- execution lineage,
- shard failure context.

---

### 6.2 Traceability

Distributed failures SHOULD expose:

- correlation ID,
- trace ID,
- shard lineage,
- execution timeline references.

---

## 7. Client & SDK Contract

SDKs MUST consistently expose:

1. gRPC status code,
2. canonical message,
3. structured detail payloads,
4. retryability semantics,
5. correlation metadata.

CLI tooling SHOULD:

- display validation failures clearly,
- preserve structured diagnostics,
- expose remediation hints,
- expose retry guidance.

---

## 8. Retryability Model

Retryability MUST remain deterministic.

### 8.1 Retryable Statuses

Typically retryable:

- `UNAVAILABLE`
- `RESOURCE_EXHAUSTED`
- `ABORTED`
- `DEADLINE_EXCEEDED`

Conditionally retryable:

- `FAILED_PRECONDITION`
- `NOT_FOUND`

---

### 8.2 Non-Retryable Statuses

Typically non-retryable:

- `INVALID_ARGUMENT`
- `UNIMPLEMENTED`
- `PERMISSION_DENIED`

---

## 9. Conformance Requirements

CI MUST validate:

1. deterministic status mapping,
2. stable reason-code behavior,
3. required structured details,
4. retryability semantics,
5. backend normalization,
6. distributed-runtime failure mapping,
7. async error artifact presence.

Required golden tests:

- validation failures,
- precondition failures,
- backend transient failures,
- quota failures,
- auth/authz failures,
- merge conflicts,
- lease conflicts,
- distributed runtime failures.

---

## 10. Operational Invariants

The following invariants are mandatory.

### Deterministic Semantics

The same failure class MUST map to the same status semantics.

### Structured Errors

Validation/runtime failures MUST expose structured semantics where applicable.

### No Wrapper Errors

RPC bodies MUST NOT implement transport error wrappers.

### Backend Normalization

Provider-native failures MUST be normalized before public exposure.

### Async Failure Visibility

Async failures MUST remain durable and inspectable.

### Traceability

Distributed/runtime failures MUST remain traceable across services.

---

## 11. Compatibility & Evolution

### 1.1 Additive Evolution

MINOR releases MAY add:

- reason codes,
- metadata fields,
- detail fields,
- taxonomy extensions.

---

### 11.2 Deprecation Policy

Deprecated reason codes MUST:

- remain documented,
- remain functional for at least one MINOR release,
- include migration guidance.

---

### 11.3 Breaking Changes

Breaking changes require:

- MAJOR version bump,
- SDK compatibility updates,
- CLI compatibility updates,
- migration documentation,
- conformance test updates.

---

## 12. Minimum Closure Criteria

The Eigen OS error model is considered fully realized only when:

1. all services use deterministic canonical mapping,
2. structured detail schemas are frozen,
3. retryability semantics are standardized,
4. distributed-runtime failures are fully normalized,
5. backend/provider normalization is complete,
6. SDKs expose consistent structured semantics,
7. CI validates end-to-end conformance,
8. async failures remain durable and inspectable.
