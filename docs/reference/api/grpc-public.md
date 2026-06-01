# gRPC Public API (eigen.api.v1)

**Status**: Normative Contract  
**Contract Version**: 1.0.0  
**Protocol**: gRPC / Protocol Buffers  
**Namespace**: `eigen.api.v1`  
**Source of Truth**: `proto/eigen/api/v1/*.proto`

This document defines the public gRPC API exposed to external clients of Eigen OS.  
All breaking changes require a **MAJOR** version increment (v2).

---

## 1. Scope

The public gRPC API provides:

- Job submission and orchestration
- Job lifecycle monitoring
- Device discovery and reservation
- Dispatch rationale and explainability
- Knowledge Base access

Compilation, optimizer internals, scheduler internals, and driver coordination are **intentionally excluded** from the public surface.

---

## 2. Transport & Protocol Requirements

### 2.1 Protocol

- **Transport**: gRPC over HTTP/2
- **Serialization**: Protocol Buffers v3
- **Encoding**: binary protobuf only
- **JSON transcoding**: NOT part of the v1 contract

--

### 2.2 Authentication

All public RPCs **REQUIRE** authentication.

Supported mechanisms:
- OAuth2 Bearer JWT
- mTLS service identity (internal trusted clients only)

JWTs **MUST** include:

| **Claim**     | **Required** | **Description** |
|---------------|----------|-----------|
| `sub`         | YES      | Subject / principal |
| `aud`         | YES      | Must include Eigen API audience |
| `exp`         | YES      | Expiration timestamp |
| `tenant_id`   | YES      | Tenant isolation identifier |
| `roles` / `scopes` | YES | Authorization scopes |

---

### 2.3 Required Metadata

Clients **SHOULD** send:

| **Metadata Key**      | **Required** | **Description** |
|-----------------------|--------------|-----------|
| `x-request-id`        | YES          | Client correlation ID |
| `x-idempotency-key`   | CONDITIONAL  | Required for idempotent submit |
| `traceparent`         | RECOMMENDED  | W3C trace propagation |
| `x-client-version`    | OPTIONAL     | SDK/client version |

---

## 3. Services Overview

### 3.1 JobService

```protobuf
service JobService {
  rpc SubmitJob(SubmitJobRequest) returns (SubmitJobResponse);
  rpc GetJobStatus(GetJobStatusRequest) returns (GetJobStatusResponse);
  rpc CancelJob(CancelJobRequest) returns (CancelJobResponse);
  rpc StreamJobUpdates(StreamJobUpdatesRequest) returns (stream StreamJobUpdatesResponse);
  rpc GetJobResults(GetJobResultsRequest) returns (GetJobResultsResponse);
  rpc GetDispatchRationale(GetDispatchRationaleRequest) returns (GetDispatchRationaleResponse);
}
```

---

### 3.2 DeviceService

```protobuf
service DeviceService {
  rpc ListDevices(ListDevicesRequest) returns (ListDevicesResponse);
  rpc GetDeviceDetails(GetDeviceDetailsRequest) returns (GetDeviceDetailsResponse);
  rpc GetDeviceStatus(GetDeviceStatusRequest) returns (GetDeviceStatusResponse);
  rpc ReserveDevice(ReserveDeviceRequest) returns (ReserveDeviceResponse);
}
```

---

### 3.3 KnowledgeBaseService

```protobuf
service KnowledgeBaseService {
  rpc UpsertRecord(UpsertRecordRequest) returns (UpsertRecordResponse);
  rpc BatchUpsertRecords(BatchUpsertRecordsRequest) returns (BatchUpsertRecordsResponse);
  rpc QueryRecords(QueryRecordsRequest) returns (QueryRecordsResponse);
  rpc GetRecord(GetRecordRequest) returns (GetRecordResponse);
  rpc AppendDecisionLog(AppendDecisionLogRequest) returns (AppendDecisionLogResponse);
  rpc QueryDecisionLogs(QueryDecisionLogsRequest) returns (QueryDecisionLogsResponse);
}
```

---

## 4. Product 1.0 Envelope and Version Negotiation

All public requests MUST carry, or allow the System API to derive from authenticated transport metadata, a canonical `ApiRequestEnvelope`. The normalized envelope is persisted with request audit records and idempotency records.

```protobuf
message ApiRequestEnvelope {
  string contract_version = 1;
  string request_id = 2;
  string idempotency_key = 3;
  string traceparent = 4;
  google.protobuf.Duration deadline = 5;
  string tenant_id = 6;
  string project_id = 7;
  string client_version = 8;
}
```

| Field | Required | Source | Semantics |
|---|---|---|---|
| `contract_version` | YES | Request payload or negotiated default | SemVer public payload contract. Product 1.0 accepts `1.0.0` on `eigen.api.v1`. |
| `request_id` | YES | `x-request-id`, payload, or deterministic server derivation | Client correlation ID used in audit, logs, metrics exemplars, and traces. If omitted by an MVP client, the System API derives `req_<sha256-prefix>` from the deterministic serialized request bytes before audit/logging. |
| `idempotency_key` | CONDITIONAL | `x-idempotency-key` or payload | Required for idempotent `SubmitJob`; optional for read-only calls. |
| `traceparent` | RECOMMENDED | `traceparent` metadata or payload | W3C TraceContext parent propagated to internal services. |
| `deadline` | OPTIONAL | gRPC deadline or payload | Client deadline hint normalized before internal dispatch. |
| `tenant_id` | YES | JWT/auth context, metadata, payload, or deterministic local-dev default | Canonical tenant scope. Auth context wins on conflict; local/dev allow-all mode defaults to `tenant-default` when no tenant is supplied. |
| `project_id` | YES | JWT/auth context, metadata, payload, or deterministic local-dev default | Canonical project scope. Auth context wins on conflict; local/dev allow-all mode defaults to `project-default` when no project is supplied. |
| `client_version` | OPTIONAL | `x-client-version` or payload | SDK/CLI version for compatibility diagnostics. |

Version negotiation rules:

- Missing `contract_version` MAY default to `1.0.0` only for backward-compatible MVP clients on the `eigen.api.v1` namespace.
- Missing `request_id`, `tenant_id`, or `project_id` is normalized deterministically before dispatch using the sources above; the normalized envelope is the value used for audit, logs, metrics, idempotency scope, and internal forwarding.
- Malformed SemVer MUST return `INVALID_ARGUMENT` with `google.rpc.ErrorInfo.reason = EIGEN_PUBLIC_CONTRACT_VERSION_MALFORMED`.
- Unsupported but well-formed versions MUST return `FAILED_PRECONDITION` with `google.rpc.ErrorInfo.reason = EIGEN_PUBLIC_CONTRACT_VERSION_UNSUPPORTED` and the supported version in details metadata.
- Incompatible MAJOR versions MUST be rejected; they MUST NOT be silently coerced.
- Compatible MINOR/PATCH versions MAY be accepted only when documented in this file or the Product 1.0 manifest.

---

## 4.1 Versioning Policy

| **Change Type**          | **Version Impact** |
|--------------------------|----------------|
| Add optional field       | MINOR          |
| Add new RPC              | MINOR          |
| Remove field             | MAJOR          |
| Change field meaning     | MAJOR          |
| Rename enum value        | MAJOR          |
| Change wire number       | FORBIDDEN      |

---

## 5. JobService Contracts

### 5.1 SubmitJob

#### Request

```protobuf
message SubmitJobRequest {
  string name = 1;

  oneof program {
    EigenLangSource eigen_lang = 2;
    QasmSource qasm = 3;
    AqoRef aqo_ref = 4;
  }

  string target = 5;
  int32 priority = 6;
  map<string,string> compiler_options = 7;
  map<string,string> metadata = 8;
  repeated string dependencies = 9;
  TenantQuotaEnvelope tenant = 10;
  string reservation_id = 11;
  ApiRequestEnvelope envelope = 12;
}
```

#### Field Semantics

| **Field** | **Required** | **Notes** |
|-------------|------------|-----------|
| `envelope` | NORMALIZED YES | Canonical Product 1.0 request envelope; transport metadata and deterministic defaults MAY be normalized into this field by the System API for MVP clients |
| `name` | YES | Human-readable job name |
| `program` | YES | Exactly one variant required |
| `target` | YES | Backend/device identifier |
| `priority` | NO | Range `[0..100]`, default `50` |
| `compiler_options` | NO | Compiler-specific tuning |
| `metadata` | NO | Arbitrary client metadata |
| `dependencies` | NO | Parent job IDs |
| `tenant` | NO | Quota envelope |
| `reservation_id` | NO | Binds submission to reserved capacity |

**Idempotency**: Required for production use via `x-idempotency-key` header.

Rules:

- Retry identity is `(tenant_id, project_id, idempotency_key, sha256(canonical normalized SubmitJobRequest excluding volatile transport-only metadata))`.
- Same key + same normalized request body MUST return the same logical job and canonical `job_id`, including after System API process restart while the idempotency record is inside its retention window.
- Same key + different normalized payload MUST return `FAILED_PRECONDITION`.
- Missing idempotency key on production `SubmitJob` MUST return `FAILED_PRECONDITION` unless a deployment explicitly enables non-idempotent development mode.
- Idempotency records MUST persist the normalized request digest, assigned `job_id`, expiration timestamp, and tenant/project scope.
- Idempotency retention window MUST be configurable and default to at least 24h.
- Expired idempotency records MUST be purged before comparison; after expiry, a same-key request is treated as a new submission.

#### CLI/SDK conformance baseline

Product 1.0 clients MUST submit public payloads that contain the canonical `ApiRequestEnvelope` plus a normalized JobSpec representation. CLI and SDK implementations MUST prove conformance with at least one minimal inline JobSpec fixture and one full file-backed JobSpec fixture. Public clients MUST NOT depend on legacy bare `SubmitJobRequest` JSON shapes except as a transport-internal compatibility shim during migration.

#### Validation Rules

| **Rule** | **Error** |
|----------|-----------|
| Missing program | `INVALID_ARGUMENT` |
| Multiple oneof values | `INVALID_ARGUMENT` |
| Priority outside range | `INVALID_ARGUMENT` |
| Unknown target | `NOT_FOUND` |
| Invalid reservation | `FAILED_PRECONDITION` |
| Unsupported contract version | `FAILED_PRECONDITION` |
| Payload exceeds public limit | `RESOURCE_EXHAUSTED` with `EIGEN_PUBLIC_PAYLOAD_LIMIT_EXCEEDED`, `BadRequest`, and `QuotaFailure` details |

#### Response

```protobuf
message SubmitJobResponse {
  string job_id = 1;
  JobStatus status = 2;
}
```

#### Runtime Semantics

Submission lifecycle:

```text
SubmitJob
  -> JOB_STATE_PENDING
  -> JOB_STATE_COMPILING
  -> JOB_STATE_QUEUED
  -> JOB_STATE_RUNNING
  -> JOB_STATE_DONE | JOB_STATE_ERROR | JOB_STATE_CANCELLED | JOB_STATE_TIMEOUT
```

The response MUST contain the canonical assigned `job_id`.

---

## 5.2 GetJobStatus

Returns current job state.

#### Request

```protobuf
message GetJobStatusRequest {
  string job_id = 1;
  ApiRequestEnvelope envelope = 10;
}
```

#### Guarantees

- Read-after-write consistency for same client session
- Eventually consistent across replicas
- Final states are immutable

---

### 5.3 CancelJob

#### Request

```protobuf
message CancelJobRequest {
  string job_id = 1;
  ApiRequestEnvelope envelope = 10;
}
```

#### Response

```protobuf
message CancelJobResponse {
  bool accepted = 1;
}
```

#### Cancellation Matrix

| **Current State** | **Allowed** |
|----------|-----------|
| `JOB_STATE_PENDING` | YES |
| `JOB_STATE_COMPILING` | YES |
| `JOB_STATE_QUEUED` | YES |
| `JOB_STATE_RUNNING` | BEST-EFFORT |
| `JOB_STATE_DONE` | NO |
| `JOB_STATE_ERROR` | NO |
| `JOB_STATE_CANCELLED` | NO |
| `JOB_STATE_TIMEOUT` | NO |

#### Semantics

- `accepted=true` means cancellation request entered processing
- It does NOT guarantee cancellation success
- Cancellation is idempotent

---

### 5.4 StreamJobUpdates

#### Request

```protobuf
message StreamJobUpdatesRequest {
  string job_id = 1;
  uint64 last_event_seq = 2;
  ApiRequestEnvelope envelope = 10;
}
```

#### Response

```protobuf
message StreamJobUpdatesResponse {
  JobUpdate update = 1;
}
```

#### Ordering Guarantees

- Events MUST be delivered in ascending sequence order
- Sequence numbers are monotonically increasing
- Duplicate delivery MAY occur during reconnects
- Clients MUST de-duplicate by sequence number

#### Replay Semantics

`last_event_seq` requests replay starting from the NEXT sequence number.

Replay retention policy:

| **Policy** | **Value** |
|----------|-----------|
| Minimum retention | 24h |
| Minimum retained events | 1000 |
| Replay guarantee | Best-effort |

If replay window expired:

- server returns `OUT_OF_RANGE`
- client must re-sync via `GetJobStatus`

---

### 5.5 GetJobResults

Returns immutable final outputs.

#### Request

```protobuf
message GetJobResultsRequest {
  string job_id = 1;
  ApiRequestEnvelope envelope = 10;
}
```

#### Preconditions

Job MUST be in terminal state:

- `JOB_STATE_DONE`
- `JOB_STATE_ERROR`
- `JOB_STATE_CANCELLED`
- `JOB_STATE_TIMEOUT`

Otherwise:

```text
FAILED_PRECONDITION
```

MUST be returned.

---

### 5.6 GetDispatchRationale

Returns scheduler explanation for backend selection.

#### Request

```protobuf
message GetDispatchRationaleRequest {
  string job_id = 1;
  ApiRequestEnvelope envelope = 10;
}
```

#### Semantics

| **Case** | **Behavior** |
|----------|-----------|
| Rationale exists | Return rationale |
| Unknown job | `NOT_FOUND` |
| No rationale retained | `FAILED_PRECONDITION` |

#### Consistency

Dispatch rationale MUST match:

- backend actually used
- scheduler decision artifact
- stored audit logs

---

## 6. DeviceService Contracts

### 6.1 ListDevices

Returns all visible devices for caller tenant.

Filtering MAY include:

- backend type
- simulator/hardware
- capabilities
- topology

---

### 6.2 GetDeviceDetails

Returns static metadata:

- qubit count
- topology
- vendor
- calibration timestamp
- supported gates
- capability flags

---

### 6.3 GetDeviceStatus

Returns dynamic runtime information:

- availability
- queue depth
- health
- estimated latency
- maintenance state

---

### 6.4 ReserveDevice

Creates temporary scheduling reservation.

#### Reservation Semantics

Reservation does NOT guarantee exclusive hardware ownership unless explicitly configured by backend policy.

Reservation MUST include:

| **Field** | **Description** |
|----------|-----------|
| `reservation_id` | Unique identifier |
| `expires_at` | Expiration timestamp |
| `device_id` | Reserved device |


#### Reservation Binding

`SubmitJobRequest.reservation_id` binds a job to a reservation.

If reservation expired:

```text
FAILED_PRECONDITION
```

MUST be returned.

---

## 7. KnowledgeBaseService Contracts

### 7.1 UpsertRecord

Creates or updates a KB record atomically.

---

### 7.2 BatchUpsertRecords

Bulk variant of `UpsertRecord`.

Atomicity:

| **Mode** | **Behavior** |
|----------|-----------|
| Full atomic | Optional |
| Partial success | Allowed if documented |

If partial success is enabled:

- per-record errors MUST be returned

---

### 7.3 QueryRecords

Supports:

- vector similarity
- metadata filtering
- pagination
- ordering

---

### 7.4 GetRecord

Returns canonical stored record.

---

### 7.5 AppendDecisionLog

Appends immutable audit/event log entries.

Retention MUST follow audit policy.

---

### 7.6 QueryDecisionLogs

Returns paginated immutable decision logs filtered by trace ID and/or model version. Query results MUST be tenant-scoped and MUST preserve append order for entries with the same trace ID.

---

## 8. Error Model

Public APIs use the canonical public error model in `docs/reference/error-model.md` and the mapping matrix in `docs/reference/error-mapping.md`. Every public failure MUST be represented as `google.rpc.Status` with a deterministic gRPC status code, stable `google.rpc.ErrorInfo.reason`, retryability metadata, and structured details appropriate for the failure shape. Public responses MUST NOT leak raw internal exceptions, stack traces, provider-private payloads, credentials, filesystem paths, or unnormalized backend errors.

#### Allowed Status Codes

| **Code** | **Meaning** | **Canonical public reason examples** | **Retryability** |
|----------|-----------|-----------|-----------|
| `INVALID_ARGUMENT` | Validation failure | `EIGEN_PUBLIC_VALIDATION_FAILED`, `EIGEN_PUBLIC_CONTRACT_VERSION_MALFORMED` | No |
| `UNAUTHENTICATED` | Missing/invalid auth | `EIGEN_PUBLIC_UNAUTHENTICATED` | After re-authentication |
| `PERMISSION_DENIED` | Insufficient scope | `EIGEN_PUBLIC_PERMISSION_DENIED` | No |
| `NOT_FOUND` | Missing resource | `EIGEN_PUBLIC_JOB_NOT_FOUND` | No unless documented eventual consistency applies |
| `FAILED_PRECONDITION` | Invalid state transition, version mismatch, or idempotency conflict | `EIGEN_PUBLIC_RESULTS_NOT_READY`, `EIGEN_PUBLIC_CONTRACT_VERSION_UNSUPPORTED`, `EIGEN_PUBLIC_IDEMPOTENCY_CONFLICT` | Conditional |
| `RESOURCE_EXHAUSTED` | Payload/quota/capacity limit exceeded | `EIGEN_PUBLIC_PAYLOAD_LIMIT_EXCEEDED` | Retry only after reducing payload or waiting for quota/capacity recovery |
| `UNAVAILABLE` | Backend/service temporarily unavailable | `EIGEN_PUBLIC_UNAVAILABLE`, `EIGEN_BACKEND_UNAVAILABLE` | Yes with backoff |
| `DEADLINE_EXCEEDED` | Deadline budget exceeded | `EIGEN_PUBLIC_DEADLINE_EXCEEDED` | Conditional on idempotency |
| `ABORTED` | Coordination/idempotent conflict that can be retried | `EIGEN_PUBLIC_CONFLICT_ABORTED` | Yes with backoff/jitter |
| `CANCELLED` | Caller/runtime cancellation | `EIGEN_PUBLIC_CANCELLED` | Caller-defined |
| `OUT_OF_RANGE` | Stream replay cursor outside retention window | `EIGEN_PUBLIC_STREAM_CURSOR_OUT_OF_RANGE` | No without a new cursor |
| `INTERNAL` | Unexpected failure | `EIGEN_PUBLIC_INTERNAL` | Conditional, bounded retry only |

#### Error Details

Structured protobuf error details are mandatory at the public boundary where supported. Detail ordering MUST be deterministic with `google.rpc.ErrorInfo` first so SDKs can extract `reason` and `metadata.retryable` uniformly. Scenario-specific details then follow:

- validation: `BadRequest` field violations,
- payload/quota limits: `BadRequest` plus `QuotaFailure`,
- retryable transient failures: `RetryInfo`,
- missing resources: `ResourceInfo`,
- lifecycle/idempotency/version conflicts: `PreconditionFailure`,
- cancellation/internal correlation: `RequestInfo` when a request identifier is available.

---

## 9. Retry Policy

#### Safe To Retry

| **RPC** | **Retryable** |
|----------|-----------|
| `GetJobStatus` | YES |
| `ListDevices` | YES |
| `GetDeviceStatus` | YES |
| `GetRecord` | YES |

#### Conditionally Retryable

| **RPC** | **Notes** |
|----------|-----------|
| `SubmitJob` | ONLY with idempotency key |
| `CancelJob` | Idempotent |
| `ReserveDevice` | Depends on backend |

---

## 10. Observability

#### Required Trace Propagation

All public clients (CLI and SDKs) SHOULD send W3C TraceContext as the `traceparent` gRPC metadata key or as `ApiRequestEnvelope.traceparent`. System API MUST preserve that value, derive the 32-character `trace_id` from it when present, and include the correlation identifiers in request logs, downstream trace context, job status messages, result metadata, and dispatch rationale where the downstream contract exposes them.

```text
traceparent
```

metadata.

#### Metrics

Minimum metrics:

| **Metric** | **Type** |
|----------|-----------|
| `eigen_api_public_contract_requests_total{contract_version,outcome}` | Counter with bounded `contract_version in {1.0.0,unsupported}` and `outcome in {accepted,replayed,conflict,limit,error}`; canonical System API public-boundary marker. |
| `eigen_public_api_contract_requests_total{contract_version,outcome}` | Counter alias for the public API contract marker, emitted with the same bounded labels for compatibility with the global public API catalog. |
| `eigen_public_api_contract_request_duration_ms` | Histogram |
| `grpc.requests_total` | Counter |
| `grpc.request_duration_ms` | Histogram |
| `jobs.submitted_total` | Counter |
| `eigen_api_submit_job_outcomes_total{outcome}` | Counter with bounded `outcome in {accepted,replayed,conflict,limit}` |
| `jobs.cancelled_total` | Counter |
| `stream.replay_requests_total` | Counter |

#### Audit Logging

The following operations MUST be auditable:

- SubmitJob
- CancelJob
- ReserveDevice
- AppendDecisionLog
- GetDispatchRationale

---

## 11. SLA / SLO Targets

| **Operation** | **Target** |
|----------|-----------|
| SubmitJob p95 | <100ms |
| GetJobStatus p95 | <50ms |
| Stream reconnect | <5s |
| Device list p95 | <100ms |

These are operational targets, not protocol guarantees.

---

## 12. Security Requirements

#### Authorization Scopes

| **RPC Group** | **Required Scope** |
|----------|-----------|
| Job submission | `jobs:submit` |
| Job status/results | `jobs:read` |
| Job cancellation | `jobs:cancel` |
| Dispatch rationale | `jobs:explain` |
| Device access | `devices:read` |
| Device reservation | `devices:reserve` |
| Knowledge Base write | `kb:write` |
| Knowledge Base read | `kb:read` |

#### Multi-Tenant Isolation

Servers MUST enforce:

- tenant isolation
- project isolation
- quota isolation
- audit partitioning

Cross-tenant reads are forbidden unless explicitly authorized.

---

## 13. Compatibility Guarantees

The following are frozen in v1:

- Service names
- RPC names
- Field numbers
- Enum numeric values
- Streaming ordering semantics
- Canonical envelope field meanings
- Version-negotiation rejection behavior
- Idempotency behavior
- Error status semantics

---

## 14. CI / Contract Enforcement

The following CI checks are REQUIRED:

- Buf breaking-change validation
- Golden response fixtures
- SDK compatibility tests
- Stream replay tests
- Auth enforcement tests
- Idempotency replay tests

---

## Appendix A. Diagrams

### A.1 Scope

![Scope](https://i.imgur.com/WWOmpG4.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Client[External Clients]
    SDK[SDK / CLI] --> API[gRPC Public API<br/>eigen.api.v1]
  end

  subgraph PublicSurface[Public Surface]
    API --> JS[JobService]
    API --> DS[DeviceService]
    API --> KBS[KnowledgeBaseService]
  end

  subgraph Internal["Internal (not exposed)"]
    JS -.-> INT[eigen.internal.v1<br/>KernelGatewayService]
    INT --> QRTX[QRTX]
    QRTX --> COMP[CompilationService]
    QRTX --> DM[DriverManagerService]
    QRTX --> QFS[QFS]
    QRTX --> OPT[OptimizerService]
  end

  note1{{Public API excludes:<br/>compiler internals, optimizer internals,<br/>driver coordination semantics}}
  PublicSurface --- note1
```

</details>

---

### A.2 Transport & Protocol Requirements

![Transport & Protocol Requirements](https://i.imgur.com/Gs6pLC0.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant C as Client (SDK/CLI)
  participant API as Public gRPC (eigen.api.v1)
  participant SEC as Security Module (AuthN/AuthZ)
  participant OTel as OTel Collector

  C->>API: RPC call (HTTP/2)\nmetadata: x-request-id, traceparent,\n(optional) x-idempotency-key, authorization: Bearer JWT
  API->>SEC: Validate JWT (iss/aud/exp/sub/tenant_id)\nEvaluate scopes (RBAC/ABAC)
  alt authorized
    SEC-->>API: allow + policy snapshot/version
    API-->>C: gRPC response (status OK + payload)
  else denied
    SEC-->>API: deny (reason)
    API-->>C: PERMISSION_DENIED / UNAUTHENTICATED\n+ structured details
  end
  API->>OTel: spans/metrics/logs (bounded labels)
```

</details>

---

### A.3 Services Overview

![Services Overview](https://i.imgur.com/wM4K82S.png)

<details>
<summary>code</summary>

```text
flowchart TB
  API[eigen.api.v1] --> JS[JobService]
  API --> DS[DeviceService]
  API --> KBS[KnowledgeBaseService]

  JS -->|submit/status/results| JOB[(Job resources)]
  DS -->|inventory/status/reserve| DEV[(Device resources)]
  KBS -->|records + decision logs| KB[(KB records)]

  %% cross-cutting rules
  RULES{{Global rules:<br/>Auth required • bounded metric labels<br/>• traceparent propagation • gRPC status-first}}
  API --- RULES
```

</details>

---

### A.4 SubmitJob

![SubmitJob](https://i.imgur.com/P4myZbd.png)

<details>
<summary>code</summary>

```text
flowchart LR
  A[Client submits SubmitJob\nx-idempotency-key=K] --> B[Server normalizes request\ncanonical bytes = R]
  B --> H["hash = sha256(R)"]
  H --> C{"Lookup (tenant,K)"}
  C -->|miss| D["Create job_id<br/>persist idempotency record<br/>(K,H)->job_id"]
  C -->|hit same H| E[Return existing job_id<br/>same logical job]
  C -->|hit different H| F["FAILED_PRECONDITION\nidempotency conflict"]
  D --> G[Response: job_id + initial status]
  E --> G
```

</details>

---

### A.5 Runtime Semantics

![Runtime Semantics](https://i.imgur.com/p0syl9x.png)

<details>
<summary>code</summary>

```text
stateDiagram-v2
  [*] --> PENDING
  PENDING --> COMPILING
  COMPILING --> QUEUED
  QUEUED --> RUNNING
  RUNNING --> DONE
  RUNNING --> ERROR
  PENDING --> CANCELLED
  COMPILING --> CANCELLED
  QUEUED --> CANCELLED
  RUNNING --> CANCELLED

  %% timeout is represented as ERROR with deadline_exceeded semantics unless v2 introduces TIMEOUT publicly
  RUNNING --> ERROR: deadline_exceeded
```

</details>

---

### A.6 StreamJobUpdates

![StreamJobUpdates](https://i.imgur.com/1AwbooY.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
    autonumber

    participant C as Client
    participant JS as JobService

    C->>JS: StreamJobUpdates(job_id, last_event_seq=N)

    alt replay window available
        loop events with seq > N
            JS-->>C: JobUpdate(seq, state, refs)
        end
        Note over C,JS: Duplicate delivery MAY occur. Client MUST dedupe by seq
    else replay expired
        JS-->>C: OUT_OF_RANGE (replay window expired)
        C->>JS: GetJobStatus(job_id) (re-sync)
    end
```

</details>

---

### A.7 CancelJob

![CancelJob](https://i.imgur.com/RhuUGnF.png)

<details>
<summary>code</summary>

```text
flowchart TD
  A["CancelJob(job_id)"] --> B{Current state}
  B -->|PENDING/COMPILING/QUEUED| C[accepted=true<br/>cancel guaranteed]
  B -->|RUNNING| D[accepted=true<br/>best-effort cancel]
  B -->|DONE/ERROR/CANCELLED| E["accepted=false<br/>(or OK idempotent no-op)"]
  D --> F["Cancellation propagates downstream\n(kernel/driver/backend)"]
```

</details>

---

### A.8 ReserveDevice

![ReserveDevice](https://i.imgur.com/NGbvRWx.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant C as Client
  participant DS as DeviceService
  participant RM as Resource/Reservation Authority
  participant JS as JobService

  C->>DS: ReserveDevice(device_id)
  DS->>RM: Create reservation (policy-gated)
  RM-->>DS: reservation_id + expires_at
  DS-->>C: ReserveDeviceResponse(reservation_id, expires_at)

  C->>JS: SubmitJob(..., reservation_id)
  JS->>RM: Validate reservation (owner + not expired)
  alt valid
    RM-->>JS: ok
    JS-->>C: job_id
  else expired/invalid
    RM-->>JS: reject
    JS-->>C: FAILED_PRECONDITION (+ details)
  end
```

</details>

---

### A.9 Error Model

![Error Model](https://i.imgur.com/wuGSr24.png)

<details>
<summary>code</summary>

```text
flowchart LR
  S[gRPC Status Code] --> EI[google.rpc.ErrorInfo<br/>reason=EIGEN_*]
  S --> BR[google.rpc.BadRequest<br/>field violations]
  S --> RI[google.rpc.ResourceInfo<br/>resource context]
  S --> RET[google.rpc.RetryInfo<br/>retry delay]
  EI --> H[Client handling]
  BR --> H
  RI --> H
  RET --> H
```

</details>

---

### A.10 Observability

![Observability](https://i.imgur.com/4Q0xkdR.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant C as Client
  participant API as eigen.api.v1
  participant OTel as OTel Collector

  C->>API: RPC (traceparent, x-request-id)
  API-->>C: response (grpc.status_code)
  API->>OTel: span.server (rpc.service, rpc.method, grpc.status_code)
  API->>OTel: metrics grpc_requests_total{rpc,code}
  API->>OTel: metrics grpc_request_duration_ms_bucket{rpc}
  API->>OTel: audit log events for sensitive ops\n(SubmitJob/CancelJob/ReserveDevice/GetDispatchRationale/AppendDecisionLog)
  Note over API: No job_id/trace_id/tenant_id as metric labels (bounded labels only)
```

</details>

---

### A.11 Security Requirements

![Security Requirements](https://i.imgur.com/aOvK4DK.png)

<details>
<summary>code</summary>

```text
flowchart TB
  C[Caller JWT: sub, tenant_id, scopes] --> A["AuthN validate\n(iss/aud/exp/signature)"]
  A --> Z["AuthZ policy\n(scope + tenant isolation)"]
  Z -->|allow| SVC[Execute RPC handler]
  Z -->|deny| DENY["PERMISSION_DENIED\n(+ ErrorInfo.reason)"]
  SVC --> AUD[Immutable audit event]
  AUD --> OBS[Observability pipeline]
  SVC --> TEN["Enforce tenant/project isolation\n(resource partitioning)"]
```

</details>
