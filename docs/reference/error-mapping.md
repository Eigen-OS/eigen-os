# Error Mapping Matrix — Eigen OS 1.0

**Document status:** Normative
**Subsystem:** Public API, Kernel, Runtime, Compiler, Driver Manager, Distributed Runtime
**Contract version:** `1.0.0`
**Applies to:** Eigen OS 1.0

This document defines the canonical error mapping contract for Eigen OS 1.0.

The contract standardizes:

- gRPC status usage,
- structured error semantics,
- async job failure representation,
- backend/provider normalization,
- retryability semantics,
- distributed runtime failure mapping,
- compiler/runtime validation behavior,
- observability correlation guarantees,
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
- `docs/reference/api/grpc-public.md`
- `docs/reference/api/grpc-internal.md`
- `docs/reference/formats/aqo.md`
- `docs/reference/formats/qfs-layout.md`
- `docs/reference/cluster-runtime-observability-contract.md`

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
- embedded transport status fields.

Application-level async failures MUST be represented via lifecycle state plus structured failure metadata.

---

## 2. Canonical Error Representation

Every failure MUST consist of:

1. gRPC status code,
2. canonical status message,
3. stable machine-readable reason code,
4. optional structured details,
5. optional remediation metadata,
6. optional correlation and trace metadata.

The same semantic failure MUST always map to the same:

- gRPC status,
- reason code,
- retryability class.

This invariant is mandatory across:

- public APIs,
- internal APIs,
- SDKs,
- orchestration services,
- distributed runtime components.

---

## 3. Structured Error Details

Eigen OS standardizes usage of the following Google RPC detail types.

| **Detail Type** | **Purpose** |
|---|---|
| `google.rpc.BadRequest` | validation failures |
| `google.rpc.ErrorInfo` | stable machine-readable semantics |
| `google.rpc.ResourceInfo` | resource identity context |
| `google.rpc.RetryInfo` | retry guidance |
| `google.rpc.DebugInfo` | internal diagnostics |
| `google.rpc.Help` | operator remediation |
| `google.rpc.LocalizedMessage` | localization-safe user messaging |
| `google.rpc.QuotaFailure` | quota enforcement semantics |
| `google.rpc.PreconditionFailure` | lifecycle/precondition violations |
| `google.rpc.RequestInfo` | request correlation metadata |

Structured details MUST remain backward-compatible within the same MAJOR contract version.

---

## 4. Canonical Status Usage

### 4.1 INVALID_ARGUMENT

Use when:

- request invalid independently of runtime state.

Examples:

- malformed JobSpec,
- unsupported compiler syntax,
- invalid AQO schema,
- invalid parameter ranges,
- missing required fields,
- malformed resource identifiers,
- invalid artifact references,
- unsupported metadata values,
- invalid optimizer configuration.

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
- cluster worker not ready,
- reservation expired,
- backend calibration unavailable.

Retryability:

- conditionally retryable after state transition.

MUST include when applicable:

- `PreconditionFailure`.

---

### 4.3 NOT_FOUND

Use when:

- referenced resource does not exist.

Examples:

- unknown job,
- missing artifact,
- unknown worker,
- missing queue,
- deleted execution context,
- unknown reservation ID.

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
- duplicate job namespace allocation,
- duplicate idempotency key reuse with incompatible payload.

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
- cluster scheduling saturation,
- tenant queue limit exceeded,
- artifact storage limit exceeded.

Retryability:

- retryable with backoff.

MUST include:

- `RetryInfo`.

SHOULD include:

- `QuotaFailure`.

---

### 4.6 UNAVAILABLE

Use when:

- service temporarily unavailable.

Examples:

- provider outage,
- network partition,
- backend unavailable,
- transient control-plane failure,
- distributed queue outage.

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
- distributed merge timeout,
- compilation timeout.

Retryability:

- implementation-dependent.

---

### 4.8 PERMISSION_DENIED

Use when:

- authenticated identity lacks authorization.

Examples:

- forbidden namespace access,
- denied backend entitlement,
- unauthorized administrative action,
- missing required OAuth scope,
- forbidden tenant resource access.

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
- invalid runtime certificate,
- invalid mTLS identity.

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
- unsupported API version,
- stub RPC invocation.

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
- unexpected compiler failure,
- invariant breach in merge pipeline.

Retryability:

- implementation-dependent.

MUST include:

- correlation metadata.

SHOULD include:

- `DebugInfo`.

---

### 4.12 ABORTED

Use when:

- optimistic concurrency conflict occurs.

Examples:

- lease conflict,
- transactional state race,
- distributed coordination conflict,
- replay conflict.

Retryability:

- retryable.

---

### 4.13 CANCELLED

Use when:

- caller or orchestration explicitly cancels operation.

Examples:

- user cancellation,
- orchestration cancellation,
- shutdown interruption,
- deadline-propagated cancellation.

Retryability:

- caller-defined.

---

## 5. Canonical Error Mapping Matrix

| **Scenario** | **Origin** | **Internal Mapping** | **Public Behavior** | **Retryability** |
|-------------------|-------------------|-------------------|-------------------|-------------------|
| Missing required field | API validation | `INVALID_ARGUMENT` | RPC failure | No |
| Invalid JobSpec | Compiler/parser | `INVALID_ARGUMENT` | RPC failure or async `ERROR` | No |
| Invalid AQO schema | Compiler/runtime | `INVALID_ARGUMENT` | RPC failure | No |
| Invalid artifact checksum | Artifact layer | `INVALID_ARGUMENT` | RPC failure | No |
| Unknown job_id | Kernel/QFS | `NOT_FOUND` | RPC failure | Conditional |
| Unknown shard | Distributed runtime | `NOT_FOUND` | RPC failure | No |
| Unknown reservation | Reservation manager | `NOT_FOUND` | RPC failure | No |
| Duplicate artifact upload | Artifact store | `ALREADY_EXISTS` | RPC failure | No |
| Duplicate idempotency key with different normalized payload | API gateway | `FAILED_PRECONDITION` | RPC failure | No |
| Results requested before completion | Runtime lifecycle | `FAILED_PRECONDITION` | RPC failure | Yes |
| Merge before quorum satisfied | Runtime merge layer | `FAILED_PRECONDITION` | RPC failure | Yes |
| Reservation expired | Device runtime | `FAILED_PRECONDITION` | RPC failure | Conditional |
| Unsupported language feature | Compiler | `UNIMPLEMENTED` | RPC failure | No |
| Unsupported backend capability | Driver Manager | `UNIMPLEMENTED` | RPC failure | No |
| Stub RPC invoked | Internal API | `UNIMPLEMENTED` | RPC failure | No |
| Backend unavailable | Provider/runtime | `UNAVAILABLE` | Async or sync failure | Yes |
| Backend throttling | Provider/runtime | `RESOURCE_EXHAUSTED` | Async or sync failure | Yes |
| Queue capacity exhausted | Distributed runtime | `RESOURCE_EXHAUSTED` | RPC failure | Yes |
| Scheduler saturation | Orchestrator | `RESOURCE_EXHAUSTED` | RPC failure | Yes |
| Tenant quota exceeded | Admission control | `RESOURCE_EXHAUSTED` | RPC failure | Yes |
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

Async failures MUST remain durable and inspectable after execution completion.

### 6.1 Required Async Failure Fields

Async failures MUST expose at least one of:

| **Field** | **Purpose** |
|---|---|
| `error_code` | stable machine-readable code |
| `error_summary` | human-readable summary |
| `error_details_ref` | durable artifact reference |
| `retryable` | retry guidance |
| `origin_service` | originating subsystem |
| `trace_id` | distributed tracing correlation |

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
- distributed failure lineage,
- normalized provider payloads,
- AQO validation diagnostics.

Artifacts MUST NOT expose:

- secrets,
- raw authentication tokens,
- private credentials,
- internal-only infrastructure topology.

---

## 7. Backend Normalization Contract

Backend/provider-native failures MUST be normalized before public exposure.

Raw provider payloads MUST NOT leak directly into:

- public APIs,
- SDK contracts,
- orchestration decisions,
- stable telemetry contracts.

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
| Poison message detected | `INVALID_ARGUMENT` |

---

### 8.3 Merge Failures

| **Condition** | **Status** |
|---|---|
| Parent mismatch | `FAILED_PRECONDITION` |
| Duplicate shard envelope | `INVALID_ARGUMENT` |
| Missing quorum | `FAILED_PRECONDITION` |
| Invalid merge artifact | `INVALID_ARGUMENT` |

---

### 8.4 Replay & Recovery Failures

| **Condition** | **Status** |
|---|---|
| Replay lineage mismatch | `FAILED_PRECONDITION` |
| Replay artifact missing | `NOT_FOUND` |
| Recovery checkpoint invalid | `INVALID_ARGUMENT` |
| Replay timeout | `DEADLINE_EXCEEDED` |

---

## 9. Retryability Contract

SDKs and clients MUST treat retryability deterministically.

Retries MUST respect:

- exponential backoff,
- bounded retry budgets,
- propagated deadlines,
- idempotency guarantees.

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
- `UNAUTHENTICATED`
- `ALREADY_EXISTS`

---

### 9.3 Retry Metadata

Retryable failures SHOULD include:

- `RetryInfo.retry_delay`
- retry classification metadata
- retry budget hints when available

---

## 10. Correlation & Traceability

All distributed/runtime failures SHOULD expose:

- correlation ID,
- trace ID,
- execution timeline reference,
- shard lineage (if applicable),
- originating subsystem,
- runtime worker identity (internal only).

Distributed failures SHOULD remain traceable across:

- scheduler,
- dispatcher,
- worker,
- merge pipeline,
- artifact storage,
- replay systems,
- observability exporters.

Trace propagation SHOULD use:

- W3C `traceparent`
- OpenTelemetry-compatible correlation metadata.

---

## 11. SDK & CLI Requirements

SDKs MUST consistently expose:

1. gRPC status code,
2. canonical message,
3. structured details,
4. retryability semantics,
5. correlation metadata.
6. stable reason codes.

CLI tooling SHOULD:

- render validation failures clearly,
- expose remediation hints,
- display retry guidance,
- preserve structured diagnostics,
- expose correlation IDs for operator support.

SDKs MUST NOT:

- collapse canonical statuses into generic exceptions,
- discard structured detail payloads,
- mutate retryability semantics.

---

## 12. Conformance Requirements

CI MUST validate:

1. deterministic status mapping,
2. stable reason codes,
3. structured detail presence,
4. retryability correctness,
5. async failure envelope presence,
6. distributed-runtime failure normalization.
7. backend normalization correctness,
8. traceability metadata propagation.

Required golden tests:

- validation failures,
- precondition failures,
- backend transient failures,
- auth/authz failures,
- distributed runtime conflicts,
- merge failures,
- quota failures,
- timeout behavior,
- AQO validation failures,
- replay/recovery failures.

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

#### Retry Consistency

Retry guidance MUST remain deterministic across SDKs and services.

#### Security Preservation

Failure payloads MUST NOT leak:

- secrets,
- credentials,
- internal tokens,
- privileged infrastructure topology.

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
- conformance test updates,
- observability compatibility review.

---

## Appendix A. Diagrams

### A.1 Core Error Contract

![Core Error Contract](https://i.imgur.com/Wxe6WJX.png)

<details>
<summary>code</summary>

```text
flowchart TB
  REQ[RPC request] --> FAIL{Failure occurs?}
  FAIL -->|no| OK[Normal response]
  FAIL -->|yes| MAP["Deterministic mapping (class → status + reason)"]
  MAP --> ST["gRPC status code (status-first)"]
  MAP --> RI["ErrorInfo.reason (stable code)"]
  MAP --> DET["Structured details (google.rpc.*)"]
  MAP --> OUT["RPC terminates with status (no success=false wrappers)"]

  OUT --> OBS["Logs/Traces (correlation IDs as fields)"]
```

</details>

---

### A.2 Canonical Error Representation

![Canonical Error Representation](https://i.imgur.com/yDgINPg.png)

<details>
<summary>code</summary>

```text
flowchart LR
  E[Error] --> S["gRPC status (code + message)"]
  E --> R["Stable reason code (ErrorInfo.reason)"]
  E --> D[Structured details BadRequest / ResourceInfo / RetryInfo / ...]
  E --> M["Remediation metadata (help, retry hints)"]
  E --> C["Correlation fields (request_id, trace_id) (no metric labels)"]

  D --> BR["BadRequest (field violations)"]
  D --> EI["ErrorInfo (domain, reason, metadata)"]
  D --> PI[PreconditionFailure]
  D --> QF[QuotaFailure]
  D --> RT[RetryInfo]
  D --> RI2[ResourceInfo]
  D --> DI[DebugInfo]
```

</details>

---

### A.3 Structured Error Details

![Structured Error Details](https://i.imgur.com/8bJLeFZ.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant S as Service
  participant M as Mapper
  participant B as Builder

  S->>M: classify(error_class, context)
  M->>B: status(code,message) + ErrorInfo(reason,domain)
  opt validation
    M->>B: BadRequest(field_violations)
  end
  opt precondition/lifecycle
    M->>B: PreconditionFailure(violations)
  end
  opt quota/capacity
    M->>B: QuotaFailure + RetryInfo(delay)
  end
  opt resource identity
    M->>B: ResourceInfo(type,name,owner)
  end
  opt internal diagnostics (internal only)
    M->>B: DebugInfo(stack, detail)
  end
  B-->>S: Status + Details (deterministic)
```

</details>

---

### A.4 Canonical Error Mapping Matrix

![Canonical Error Mapping Matrix](https://i.imgur.com/Z94WJAb.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Sources
    API[System API validation]
    K[Kernel / QRTX]
    C[Compiler]
    DM[Driver Manager]
    DR[Distributed runtime]
    QFS[QFS / artifact layer]
  end

  subgraph Canonical statuses
    IA[INVALID_ARGUMENT]
    FP[FAILED_PRECONDITION]
    NF[NOT_FOUND]
    AE[ALREADY_EXISTS]
    RE[RESOURCE_EXHAUSTED]
    UA[UNAVAILABLE]
    DE[DEADLINE_EXCEEDED]
    PD[PERMISSION_DENIED]
    UN[UNAUTHENTICATED]
    UI[UNIMPLEMENTED]
    IN[INTERNAL]
    AB[ABORTED]
    CA[CANCELLED]
  end

  API --> IA
  C --> IA
  QFS --> NF
  K --> FP
  DM --> UA
  DR --> AB
  DR --> RE
  DM --> DE
  API --> PD
  API --> UN
  C --> UI
  K --> IN
  K --> CA
```

</details>

---

### A.5 Async Job Failure Contract

![Async Job Failure Contract](https://i.imgur.com/VAZEvxt.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant Client
  participant API as System API (public)
  participant K as Kernel/QRTX
  participant Q as QFS

  Client->>API: SubmitJob
  API->>K: EnqueueJob
  K->>Q: persist inputs (job.yaml, source)
  K-->>API: job_id + PENDING
  API-->>Client: Accepted (job_id)

  loop status polling / streaming
    Client->>API: GetJobStatus
    API->>K: GetJobStatus
    K-->>API: state
    API-->>Client: state
  end

  alt terminal success
    K->>Q: persist results.parquet + manifest
    K-->>API: DONE
  else terminal failure
    K->>Q: persist results/error.json (durable)
    K-->>API: ERROR + (error_code, error_summary, error_details_ref)
  end

  Client->>API: GetJobResults
  API->>K: GetJobResults
  K->>Q: read refs
  API-->>Client: results or async failure envelope
```

</details>

---

### A.6 Backend Normalization Contract

![Backend Normalization Contract](https://i.imgur.com/wgsKt85.png)

<details>
<summary>code</summary>

```text
flowchart TB
  P["Provider/Vendor error (raw payload)"] --> DM["Driver Manager (normalize + classify)"]
  DM --> MAP[Map to canonical status + EIGEN_BACKEND_* reason]
  MAP --> DET[Attach google.rpc.ErrorInfo + optional RetryInfo/ResourceInfo]
  DET --> K["Kernel/QRTX (orchestrator)"]
  K --> PUB["Public surface (System API / SDK)"]
  DM -.optional.-> QFSRAW["qfs://jobs/<job_id>/execution/backend_response.json (raw stored under policy)"]
  style QFSRAW stroke-dasharray: 5 5
```

</details>

---

### A.7 Retryability Contract

![Retryability Contract](https://i.imgur.com/9TpsGMh.png)

<details>
<summary>code</summary>

```text
flowchart LR
  R[Received failure] --> C{Status code}
  C -->|UNAVAILABLE| Y1[Retry exponential backoff]
  C -->|RESOURCE_EXHAUSTED| Y2[Retry backoff + quota hints]
  C -->|ABORTED| Y3["Retry (conflict/lease) with jitter"]
  C -->|DEADLINE_EXCEEDED| Y4{Idempotent?}
  Y4 -->|yes| Y4a[Retry with new deadline budget]
  Y4 -->|no| N4[Do not retry without idempotency]
  C -->|FAILED_PRECONDITION| Y5[Retry only after state change]
  C -->|NOT_FOUND| Y6{Eventual consistency?}
  Y6 -->|yes| Y6a[Retry with short backoff]
  Y6 -->|no| N6[Do not retry]
  C -->|INVALID_ARGUMENT| N1["Do not retry (fix request)"]
  C -->|PERMISSION_DENIED| N2["Do not retry (policy change needed)"]
  C -->|UNAUTHENTICATED| N3[Re-authenticate then retry]
  C -->|UNIMPLEMENTED| N5["Do not retry (change request/feature"]
  C -->|ALREADY_EXISTS| N7["Do not retry (resolve conflict"]
  C -->|INTERNAL| Y7[Conditional retry bounded budget]
  C -->|CANCELLED| N8[Caller-defined]
```

</details>

---

### A.8 Distributed Runtime Failure Mapping

![Distributed Runtime Failure Mapping](https://i.imgur.com/Mu1tmRz.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Queue path
    QITEM[Queue item] --> DEL["Deliver (lease-based)"]
    DEL -->|ack| ACK[ACK]
    DEL -->|lease expired| RED[Redeliver]
    RED -->|retry budget exceeded| DLQ[Dead-letter]
  end

  subgraph Canonical mapping
    LE[Lease expired/conflict] --> AB[ABORTED]
    QNA[Queue unavailable] --> UA[UNAVAILABLE]
    QOL[Queue overloaded] --> RE[RESOURCE_EXHAUSTED]
    POI[Poison message] --> IA[INVALID_ARGUMENT]
    MQ[Missing quorum] --> FP[FAILED_PRECONDITION]
  end

  DEL --> LE
  QITEM --> QNA
  QITEM --> QOL
  QITEM --> POI
  DLQ --> MQ
```

</details>

---

### A.9 Correlation & Traceability

![Correlation & Traceability](https://i.imgur.com/ZLDZJ0y.png)

<details>
<summary>code</summary>

```text
flowchart LR
  S1[System API] -->|traceparent + request_id| K[Kernel/QRTX]
  K -->|propagate| C[Compiler]
  K -->|propagate| DM[Driver Manager]
  K -->|propagate| QFS[QFS]
  DM -->|provider corr_id| P[Provider boundary]

  K --> LOGS["Structured logs (trace_id, request_id, job_id)"]
  K --> TRACES["Distributed traces (span lineage)"]
  K --> ART["QFS artifacts (error.json, timeline.json)"]
  note1{{"No job_id/trace_id as metric labels (bounded cardinality rule)"}}
  LOGS --- note1
```

</details>
