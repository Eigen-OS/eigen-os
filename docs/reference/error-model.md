# Error Model — Eigen OS 1.0

**Document status:** Normative
**Subsystem:** Public API, Internal API, Runtime, Compiler, Driver Manager, Distributed Runtime
**Contract version:** `1.0.0`
**Applies to:** Eigen OS 1.0

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

For detailed scenario-level mappings, see `docs/reference/error-mapping.md`.

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

Structured semantics SHOULD be encoded via: `google.rpc.Status`

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

### 1.5 Security & Information Disclosure

Errors MUST be safe for external exposure.

Implementations MUST:

- avoid leaking secrets,
- avoid exposing credentials,
- avoid exposing provider-private payloads,
- avoid exposing filesystem internals,
- avoid exposing unsafe stack traces to untrusted clients.

Production deployments SHOULD:

- redact sensitive metadata,
- sanitize provider diagnostics,
- sanitize backend payload fragments,
- sanitize internal infrastructure identifiers.

Structured diagnostics MAY contain internal metadata only in trusted/internal environments.

---

### 1.6 Deterministic Serialization

Structured error serialization MUST be deterministic.

Requirements:

- stable field ordering where serialization format permits,
- deterministic reason-code emission,
- deterministic structured-detail ordering,
- canonical UTF-8 encoding,
- stable enum serialization.

This guarantees:

- reproducible diagnostics,
- deterministic replay behavior,
- stable SDK behavior,
- stable audit artifacts.

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
- malformed resource references,
- invalid AQO payload,
- invalid Eigen-Lang AST,
- invalid distributed merge envelope.

Characteristics:

- deterministic,
- non-retryable,
- validation-originated.

Required details:

- `google.rpc.BadRequest`

Compiler validation failures SHOULD also include:

- `google.rpc.ErrorInfo` with `reason="EIGEN_COMPILER_VALIDATION_FAILED"`,
- `metadata.stage`,
- `metadata.rule`,
- `metadata.pass_name`,
- `metadata.diagnostics_json`.

The compiler service uses these fields to provide stage-level attribution for parsing, validation, lowering, and emission decisions while keeping the transport status itself on `INVALID_ARGUMENT`.

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
- invalid runtime phase,
- restore attempted before checkpoint availability,
- cluster worker not ready.

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
- missing runtime resource,
- unknown worker,
- deleted execution context.

Characteristics:

- deterministic,
- potentially retryable under eventual consistency.

---

#### 2.4 ALREADY_EXISTS

Use when:

- resource creation conflicts with existing resource.

Examples:

- duplicate artifact upload,
- duplicate registration,
- duplicate queue creation,
- duplicate checkpoint generation.

Characteristics:

- deterministic,
- non-retryable unless identity changes.

---

### 2.5 RESOURCE_EXHAUSTED

Use when:

- quota,
- capacity,
- concurrency,
- or throttling limits exceeded.

Examples:

- backend quota exceeded,
- cluster saturation,
- memory exhaustion,
- queue capacity exhaustion,
- checkpoint budget exceeded,
- artifact size budget exceeded.

Required details:

- `google.rpc.RetryInfo`

---

### 2.6 UNAVAILABLE

Use when:

- service temporarily unavailable.

Examples:

- provider outage,
- runtime unavailable,
- cluster partition,
- transient network failure,
- queue backend unavailable.

Required details:

- `google.rpc.RetryInfo`

---

### 2.7 DEADLINE_EXCEEDED

Use when:

- operation exceeds deadline budget.

Examples:

- execution timeout,
- scheduling timeout,
- distributed merge timeout,
- backend response timeout,
- replay timeout.

---

### 2.8 UNAUTHENTICATED

Use when:

- authentication invalid or absent.

Examples:

- expired token,
- invalid credentials,
- invalid runtime certificate.

---

### 2.9 PERMISSION_DENIED

Use when:

- authenticated identity lacks authorization.

Examples:

- forbidden namespace access,
- unauthorized runtime action,
- restricted administrative operation.

---

### 2.10 UNIMPLEMENTED

Use when:

- requested feature unsupported.

Examples:

- unsupported compiler feature,
- unsupported backend capability,
- unavailable orchestration policy,
- unsupported AQO transport format,
- unsupported observability contract version.

---

### 2.11 INTERNAL

Use when:

- unexpected invariant violation occurs.

Examples:

- runtime panic,
- corrupted scheduler state,
- impossible execution state,
- invariant violation,
- corrupted replay state.

Internal failures SHOULD expose:

- correlation metadata,
- traceability metadata,
- diagnostic references.

---

### 2.12 ABORTED

Use when:

- distributed coordination conflict occurs.

Examples:

- lease conflicts,
- optimistic concurrency conflicts,
- transactional race conditions.
- merge ownership conflicts.
- replay identity conflicts where the recorded audit lineage does not match the deterministic replay input set.

---

### 2.13 REPLAY VS RETRY DISTINCTION

Replay mismatches MUST be surfaced as deterministic audit/evidence failures and
MUST NOT be silently treated as transient retries.

---

### 2.14 CANCELLED

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

Validation failures MUST include: `google.rpc.BadRequest`

with one or more: `FieldViolation`

entries.

Each violation MUST contain:

| **Field** | **Requirement** |
|---|---|
| `field` | stable field path |
| `description` | actionable explanation |

---

### 3.2 Retry Semantics

Retryable failures SHOULD include: `google.rpc.RetryInfo`

Retry metadata MAY include:

- retry delay,
- retry class,
- retry budget hints,
- recommended backoff strategy.

---

### 3.3 Resource Context

Resource-oriented failures SHOULD include: `google.rpc.ResourceInfo`

Examples:

- job references,
- artifact references,
- queue references,
- worker identity.
- shard identifiers.

---

### 3.4 Stable Machine Semantics

Machine-readable semantics MUST use: `google.rpc.ErrorInfo`

Required fields:

| **Field** | **Requirement** |
|---|---|
| `reason` | stable `EIGEN_*` code |
| `domain` | owning subsystem |
| `metadata` | optional structured metadata |

---

### 3.5 Diagnostic Context

Internal/runtime failures MAY include: `google.rpc.DebugInfo`

Production deployments SHOULD redact:

- secrets,
- credentials,
- unsafe provider payloads,
- filesystem paths,
- infrastructure-sensitive identifiers.

---

### 3.6 Remediation Guidance

Operator-facing failures SHOULD include: `google.rpc.Help`

Examples:

- runbook URLs,
- remediation instructions,
- support references,
- migration documentation.

---

### 3.7 Public Boundary Conformance

Public API implementations MUST normalize every public error into a deterministic `google.rpc.Status` before returning it to SDKs, CLI tools, or external callers. The public boundary contract is:

| **Failure class** | **Status** | **Reason** | **Retryable metadata** | **Required detail shape** |
|---|---|---|---|---|
| Validation failure | `INVALID_ARGUMENT` | `EIGEN_PUBLIC_VALIDATION_FAILED` | `false` | `ErrorInfo`, `BadRequest` |
| Authentication failure | `UNAUTHENTICATED` | `EIGEN_PUBLIC_UNAUTHENTICATED` | `true` after re-authentication | `ErrorInfo` |
| Authorization denial | `PERMISSION_DENIED` | `EIGEN_PUBLIC_PERMISSION_DENIED` | `false` | `ErrorInfo` |
| Idempotency payload conflict | `FAILED_PRECONDITION` | `EIGEN_PUBLIC_IDEMPOTENCY_CONFLICT` | `false` | `ErrorInfo`, `PreconditionFailure` |
| Public contract version mismatch | `FAILED_PRECONDITION` | `EIGEN_PUBLIC_CONTRACT_VERSION_UNSUPPORTED` | `false` | `ErrorInfo`, optional `PreconditionFailure` |
| Payload limit exceeded | `RESOURCE_EXHAUSTED` | `EIGEN_PUBLIC_PAYLOAD_LIMIT_EXCEEDED` | `false` | `ErrorInfo`, `BadRequest`, `QuotaFailure` |
| Deadline exceeded | `DEADLINE_EXCEEDED` | `EIGEN_PUBLIC_DEADLINE_EXCEEDED` | conditional | `ErrorInfo`, optional `RetryInfo` |
| Cancellation | `CANCELLED` | `EIGEN_PUBLIC_CANCELLED` | caller-defined | `ErrorInfo`, optional `RequestInfo` |
| Temporary unavailable | `UNAVAILABLE` | `EIGEN_PUBLIC_UNAVAILABLE` or normalized `EIGEN_BACKEND_UNAVAILABLE` | `true` | `ErrorInfo`, `RetryInfo` |
| Unexpected internal failure | `INTERNAL` | `EIGEN_PUBLIC_INTERNAL` | conditional | `ErrorInfo`, optional `RequestInfo`; `DebugInfo` only for trusted/internal callers |

`google.rpc.ErrorInfo` MUST be the first detail entry for public errors. Its metadata MUST include `retryable` with a string value of `true` or `false`. Implementations MAY add bounded, non-sensitive correlation metadata, but MUST NOT expose raw internal exceptions, provider-private payloads, secrets, filesystem paths, or stack traces to public callers.

---

### 3.8 Localization Safety

User-facing messages MAY include: `google.rpc.LocalizedMessage`

Localized messages MUST NOT alter:

- reason codes,
- retryability semantics,
- structured machine-readable semantics.

---

## 4. Backend Normalization Model

Provider/backend-native failures MUST be normalized before public exposure.

Raw provider semantics MUST NOT directly leak into:

- public APIs,
- SDK contracts,
- orchestration decisions.

### 4.1 Normalized Backend Envelope

Backend-facing failures MUST include: `google.rpc.ErrorInfo`

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

Unknown taxonomy values MUST NOT be emitted in MAJOR version `1.x`.

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
- replay corruption,
- dead-letter exhaustion.

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
- replay ownership race.

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
- orchestration saturation,
- runtime quarantine.

Canonical statuses:

- UNAVAILABLE
- RESOURCE_EXHAUSTED

---

### 5.5 Replay & Recovery Failures

Examples:

- replay divergence,
- checkpoint corruption,
- restore validation failure,
- lineage mismatch.

Canonical statuses:

- `FAILED_PRECONDITION`
- `INVALID_ARGUMENT`
- `INTERNAL`

Replay failures MUST remain inspectable through durable error artifacts.

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
- replay diagnostics,
- orchestration metadata.

---

### 6.2 Traceability

Distributed failures SHOULD expose:

- correlation ID,
- trace ID,
- shard lineage,
- execution timeline references.

---

### 6.3 Error Artifact Stability

Error artifacts MUST remain:

- schema-versioned,
- backward-compatible within MAJOR versions,
- deterministic in structure,
- safe for long-term inspection.

Artifacts SHOULD include:

```json
{
  "schema_version": "1.0",
  "error_code": "EIGEN_BACKEND_TIMEOUT"
}
```

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

### 8.3 Backoff Requirements

Retryable failures SHOULD use:

- exponential backoff,
- jitter,
- bounded retry budgets.

Clients MUST honor: google.rpc.RetryInfo

when provided.

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
- replay failures,
- artifact corruption failures.

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

#### Bounded Diagnostics

Error metadata MUST remain bounded in size.

Systems MUST avoid:

- unbounded stack traces,
- unlimited provider payload embedding,
- recursive diagnostic structures.

#### Safe Observability

Observability pipelines MUST NOT leak secrets through:

- metrics,
- logs,
- traces,
- structured error details.

---

## 11. Compatibility & Evolution

### 11.1 Additive Evolution

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

## Appendix A. Diagrams

### A.1 Core Principles

![Core Principles](https://i.imgur.com/viG5nZC.png)

<details>
<summary>code</summary>

```text
flowchart LR
  A[Failure occurs] --> B["Deterministic classify (failure class)"]
  B --> C["gRPC status-first (code + message)"]
  B --> D["Stable reason code (ErrorInfo.reason)"]
  B --> E["Structured details (google.rpc.*)"]
  B --> F["Retryability semantics (deterministic)"]
  B --> G["Safe disclosure (redaction/sanitization)"]
  C --> OUT["RPC terminates (no success=false wrappers)"]
  E --> OUT
  D --> OUT
```

</details>

---

### A.2 Transport-Level Failure Semantics

![Transport-Level Failure Semantics](https://i.imgur.com/y7FheJo.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant Client
  participant Svc as Service

  Client->>Svc: RPC request
  alt success
    Svc-->>Client: Response payload (OK)
  else failure
    Note over Svc: NO payload-level wrappers (success=false / ok=false forbidden)
    Svc-->>Client: gRPC status code + message
    Svc-->>Client: google.rpc.Status.details[]
  end
```

</details>

---

### A.3 Deterministic Mapping

![Deterministic Mapping](https://i.imgur.com/hoem55t.png)

<details>
<summary>code</summary>

```text
flowchart LR
  IN[Same semantic failure] --> MAP["Same mapping function (versioned)"]
  MAP --> S[Same gRPC status]
  MAP --> R[Same reason-code family]
  MAP --> RT[Same retry class]
  MAP --> DT["Same detail types (where applicable)"]
  MAP --> SER["Deterministic serialization (ordering + UTF-8)"]
```

</details>

---

### A.4 Structured Error Semantics

![Structured Error Semantics](https://i.imgur.com/wws760x.png)

<details>
<summary>code</summary>

```text
flowchart LR
  ST[google.rpc.Status] --> CODE[code + message]
  ST --> DETAILS["details[]"]

  DETAILS --> EI["ErrorInfo (reason/domain/metadata)"]
  DETAILS --> BR["BadRequest (field violations)"]
  DETAILS --> PF[PreconditionFailure]
  DETAILS --> QF[QuotaFailure]
  DETAILS --> RI[RetryInfo]
  DETAILS --> RS[ResourceInfo]
  DETAILS --> DI["DebugInfo (internal only)"]
  DETAILS --> HL["Help (runbook/remediation)"]
  DETAILS --> LM["LocalizedMessage (optional)"]
```

</details>

---

### A.5 Async Failure Visibility

![Async Failure Visibility](https://i.imgur.com/rR01eCL.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant Client
  participant API as System API
  participant K as Kernel/QRTX
  participant Q as QFS

  Client->>API: SubmitJob
  API->>K: Enqueue
  K->>Q: persist inputs
  API-->>Client: job_id + state=PENDING

  loop observe
    Client->>API: GetJobStatus / Stream updates
    API->>K: query/stream
    K-->>API: lifecycle state
    API-->>Client: lifecycle state
  end

  alt terminal ERROR
    K->>Q: write results/error.json (durable)
    K-->>API: state=ERROR + error_code + error_summary + error_details_ref
    API-->>Client: ERROR envelope (inspectable)
  else terminal DONE
    K->>Q: write results.parquet (+ manifest)
    API-->>Client: DONE (results available via refs)
  end
```

</details>

---

### A.6 Security & Information Disclosure

![Security & Information Disclosure](https://i.imgur.com/xfruTVw.png)

<details>
<summary>code</summary>

```text
flowchart LR
  RAW["Raw internal error (stack/provider payload/paths)"] --> SAN[Sanitize + redact]
  SAN --> EXT["External-safe surface (public API)"]
  SAN --> INT["Internal diagnostics (trusted env only)"]
  EXT --> RULES[Rules: - no; secrets - no; credentials - no; provider-private payloads - no; filesystem internals]
  INT --> ALLOW["Allowed: - DebugInfo<br>- internal IDs - richer traces (only if policy allows)"]
```

</details>

---

### A.7 Canonical Status Model

![Canonical Status Model](https://i.imgur.com/6D7t9Ci.png)

<details>
<summary>code</summary>

```text
mindmap
  root((Canonical gRPC statuses))
    INVALID_ARGUMENT
      request invalid
      BadRequest
    FAILED_PRECONDITION
      state prevents execution
      PreconditionFailure
    NOT_FOUND
      missing resource
      ResourceInfo
    ALREADY_EXISTS
      creation conflict
    RESOURCE_EXHAUSTED
      quota/capacity/throttle
      RetryInfo
      QuotaFailure
    UNAVAILABLE
      transient outage
      RetryInfo
    DEADLINE_EXCEEDED
      deadline budget exceeded
    UNAUTHENTICATED
      invalid/missing auth
    PERMISSION_DENIED
      lacks authorization
    UNIMPLEMENTED
      unsupported feature
    INTERNAL
      invariant violation
      DebugInfo (internal)
    ABORTED
      concurrency/lease conflict
    CANCELLED
      explicit cancellation
```

</details>

---

### A.8 Structured Error Detail Model

![Structured Error Detail Model](https://i.imgur.com/Yks1M9M.png)

<details>
<summary>code</summary>

```text
flowchart LR
  F[Failure classified] --> T{Type}
  T -->|Validation| V[INVALID_ARGUMENT + BadRequest]
  T -->|Precondition / lifecycle| P[FAILED_PRECONDITION + PreconditionFailure]
  T -->|Quota / capacity| Q["RESOURCE_EXHAUSTED + RetryInfo (+ QuotaFailure)"]
  T -->|Transient outage| U[UNAVAILABLE + RetryInfo]
  T -->|Missing resource| N[NOT_FOUND + ResourceInfo]
  T -->|AuthN| A[UNAUTHENTICATED]
  T -->|AuthZ| Z[PERMISSION_DENIED]
  T -->|Concurrency conflict| C[ABORTED]
  T -->|Unsupported| X[UNIMPLEMENTED]
  T -->|Invariant violation| I["INTERNAL (+ DebugInfo internal)"]
  V --> EI["Always add ErrorInfo (reason/domain)"]
  P --> EI
  Q --> EI
  U --> EI
  N --> EI
  A --> EI
  Z --> EI
  C --> EI
  X --> EI
  I --> EI
```

</details>

---

### A.9 Backend Normalization Model

![Backend Normalization Model](https://i.imgur.com/PDQwJVn.png)

<details>
<summary>code</summary>

```text
flowchart TB
  PV["Provider/Vendor failure (raw)"] --> DM[Driver Manager normalize + classify]
  DM --> EI[Emit ErrorInfo EIGEN_BACKEND_* + taxonomy]
  DM --> ST[gRPC status canonical]
  ST --> K[Kernel/QRTX]
  K --> API[Public API / SDK]
  DM -.optional, policy.-> QFS["qfs://jobs/<job_id>/execution/backend_response.json (raw stored)"]
  style QFS stroke-dasharray: 5 5
```

</details>

---

### A.10 Distributed Runtime Error Semantics

![Distributed Runtime Error Semantics](https://i.imgur.com/xqwzDIG.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Queue & delivery
    QITEM[Queue item] --> DEL["Deliver (lease)"]
    DEL -->|ack| ACK[ACK]
    DEL -->|lease expired| RED[Redeliver]
    RED -->|retry limit| DLQ[Dead-letter]
  end

  subgraph Canonical statuses
    LE[Lease expired/conflict] --> AB[ABORTED]
    QNA[Queue unavailable] --> UA[UNAVAILABLE]
    QOL[Queue overloaded] --> RE[RESOURCE_EXHAUSTED]
    IQS[Invalid queue state] --> FP[FAILED_PRECONDITION]
    POI[Poison message] --> IA[INVALID_ARGUMENT]
    MQ[Missing quorum / merge prereq] --> FP2[FAILED_PRECONDITION]
  end

  DEL --> LE
  QITEM --> QNA
  QITEM --> QOL
  QITEM --> IQS
  QITEM --> POI
  DLQ --> MQ
```

</details>

---

### A.11 Retryability Model

![Retryability Model](https://i.imgur.com/LsBasw9.png)

<details>
<summary>code</summary>

```text
flowchart LR
  R[Received error] --> S{Status}
  S -->|UNAVAILABLE| R1[Retry exp backoff + jitter]
  S -->|RESOURCE_EXHAUSTED| R2[Retry backoff + respect RetryInfo]
  S -->|ABORTED| R3["Retry (conflict) with jitter"]
  S -->|DEADLINE_EXCEEDED| R4{Idempotent?}
  R4 -->|yes| R4a[Retry new deadline budget]
  R4 -->|no| N4[No retry without idempotency]
  S -->|FAILED_PRECONDITION| R5[Retry only after state change]
  S -->|NOT_FOUND| R6["Conditional retry (eventual consistency)"]
  S -->|INVALID_ARGUMENT| N1[No retry fix request]
  S -->|PERMISSION_DENIED| N2[No retry policy/permissions]
  S -->|UNAUTHENTICATED| N3[Re-authenticate then retry]
  S -->|UNIMPLEMENTED| N5[No retry feature unsupported]
  S -->|ALREADY_EXISTS| N6[No retry resolve conflict]
  S -->|INTERNAL| R7[Conditional retry bounded budget]
  S -->|CANCELLED| N7[Caller-defined]
```

</details>

---

### A.12 Operational Invariants

![Operational Invariants](https://i.imgur.com/VRiGnkk.png)

<details>
<summary>code</summary>

```text
flowchart TB
  I1[Deterministic semantics] --> I2[Stable reason codes]
  I2 --> I3[No wrapper errors]
  I3 --> I4[Backend normalization]
  I4 --> I5[Async failure inspectability]
  I5 --> I6[Traceability across hops]
  I6 --> I7["Bounded diagnostics (size/shape)"]
  I7 --> I8["Safe observability (no secrets in telemetry)"]
```

</details>
