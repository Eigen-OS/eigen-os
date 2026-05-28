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
}
```

---

## 4. Versioning Policy

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
}
```

#### Field Semantics

| **Field** | **Required** | **Notes** |
|-------------|------------|-----------|
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

- Same key + same request body MUST return same logical job
- Same key + different payload MUST return:
  - `ALREADY_EXISTS`
  - or `INVALID_ARGUMENT`
- Idempotency retention window MUST be at least 24h

#### Validation Rules

| **Rule** | **Error** |
|----------|-----------|
| Missing program | `INVALID_ARGUMENT` |
| Multiple oneof values | `INVALID_ARGUMENT` |
| Priority outside range | `INVALID_ARGUMENT` |
| Unknown target | `NOT_FOUND` |
| Invalid reservation | `FAILED_PRECONDITION` |


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
  -> PENDING
  -> QUEUED
  -> RUNNING
  -> SUCCEEDED | FAILED | CANCELLED | TIMEOUT
```

The response MUST contain the canonical assigned `job_id`.

---

## 5.2 GetJobStatus

Returns current job state.

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
| `PENDING` | YES |
| `QUEUED` | YES |
| `RUNNING` | BEST-EFFORT |
| `SUCCEEDED` | NO |
| `FAILED` | NO |
| `CANCELLED` | NO |
| `TIMEOUT` | NO |

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

#### Preconditions

Job MUST be in terminal state:

- SUCCEEDED
- FAILED
- CANCELLED
- TIMEOUT

Otherwise:

```text
FAILED_PRECONDITION
```

MUST be returned.

---

### 5.6 GetDispatchRationale

Returns scheduler explanation for backend selection.

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

## 8. Error Model

Public APIs use canonical gRPC status codes.

#### Allowed Status Codes

| **Code** | **Meaning** |
|----------|-----------|
| `INVALID_ARGUMENT` | Validation failure |
| `UNAUTHENTICATED` | Missing/invalid auth |
| `PERMISSION_DENIED` | Insufficient scope |
| `NOT_FOUND` | Missing resource |
| `FAILED_PRECONDITION` | Invalid state transition |
| `RESOURCE_EXHAUSTED` | Quota exceeded |
| `UNAVAILABLE` | Backend unavailable |
| `DEADLINE_EXCEEDED` | Timeout |
| `ALREADY_EXISTS` | Idempotency conflict |
| `INTERNAL` | Unexpected failure |

#### Error Details

Structured protobuf error details SHOULD be attached:

- field violations
- quota failures
- retry hints
- resource metadata

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

All services MUST propagate:

```text
traceparent
```

metadata.

#### Metrics

Minimum metrics:

| **Metric** | **Type** |
|----------|-----------|
| `grpc.requests_total` | Counter |
| `grpc.request_duration_ms` | Histogram |
| `jobs.submitted_total` | Counter |
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
