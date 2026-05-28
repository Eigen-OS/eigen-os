# REST API Contract: Benchmark Run (POST /benchmarks/run)

**Status**

- **Contract Version**: 1.0.0
- **Document Status**: Canonical Target Standard
- **Compatibility**: Eigen OS Target Standard v1.3.0
- **Transport Type**: REST binding over canonical gRPC System API
- **Normative Language**: RFC 2119 (MUST, SHOULD, MAY)

---

## 0. Architectural Positioning

This REST endpoint is an HTTP transport binding over the canonical Eigen OS System API benchmark submission contract.

Internally, the endpoint **MUST** translate incoming REST requests into a canonical `JobSpec` and submit them through the internal gRPC System API layer.

The REST transport layer **MUST NOT** bypass:

- QRTX scheduling
- authorization checks
- observability instrumentation
- audit logging
- Knowledge Base ingestion
- Continuous Learning hooks
- QFS storage policies
- Driver Manager validation

**Canonical execution authority** remains:

```
REST API → System API → QRTX → Runtime Services
```

REST is a **transport adapter only**.

The canonical contract for benchmark execution is defined in protobuf/gRPC specifications.

---

## 1. Endpoint Definition

### 1.1 HTTP Endpoint

- **Endpoint**: `POST /benchmarks/run`
- **Content-Type**: `application/json`
- **Authentication**: OAuth2/JWT required
- **Transport Security**: HTTPS/TLS 1.3 mandatory

---

### 1.2 Request Schema

**Request JSON**

```json
{
  "idempotency_key": "client-generated-key",
  "config": {
    "dataset": "qsbench-core",
    "dataset_version": "2026.04.27",
    "backend": "simulator",
    "seed": 42
  }
}
```

**Request Fields**

#### `idempotency_key`

- **Type**: string
- **Required**: true
- **Constraints**:
  - MUST be non-empty after trimming whitespace
  - MUST be UTF-8
  - SHOULD be globally unique per client
  - Maximum length: 256

**Purpose**: Used to guarantee idempotent benchmark submission.

#### `config`

- **Type**: object
- **Required**: true
- **Constraints**:
  - MUST be a non-empty JSON object
  - MUST conform to benchmark configuration schema
  - MUST be canonicalizable
  - MUST NOT contain NaN/Infinity values

---

### 1.3 Internal JobSpec Mapping

The REST layer **MUST** transform requests into canonical internal `JobSpec` objects.

**Example mapping:**

```json
{
  "job_id": "derived-from-run-id",
  "job_type": "BENCHMARK",
  "source": "REST_API",
  "benchmark_config": {
    "dataset": "qsbench-core",
    "backend": "simulator"
  },
  "target_device": "simulator",
  "priority": "NORMAL",
  "submitted_by": "authenticated-user-id",
  "trace_id": "otel-trace-id"
}
```

The REST API **MUST NOT** introduce transport-specific execution semantics.

---

## 2. Success Response

**HTTP Status**

```http
201 Created
```

**Response Body**

```json
{
  "api_version": "1.0.0",
  "run": {
    "run_id": "run_01JABCDEF",
    "state": "PENDING",
    "state_contract_version": "1.0.0",
    "parent_run_id": null,
    "idempotency_key": "client-generated-key"
  },
  "snapshot": {
    "contract_version": "1.0.0",
    "snapshot_version": "1.0.0",
    "history_entry_version": "1.0.0",
    "run_id": "run_01JABCDEF",
    "request_hash": "sha256:abcdef123456",
    "created_at": "2026-05-21T12:34:56Z",
    "payload": "{\"backend\":\"simulator\",\"dataset\":\"qsbench-core\",\"seed\":42}"
  },
  "trace": {
    "trace_id": "otel-trace-id",
    "correlation_id": "correlation-id"
  }
}
```

---

### 2.1 Response Field Semantics

- **`api_version`**: Semantic version of the public REST contract.
- **`run.run_id`**: Deterministic globally unique benchmark execution identifier.
- **`run.state`**: Canonical QRTX lifecycle state. Immediately after creation: **`PENDING`**.
- **`run.state_contract_version`**: Version of lifecycle semantics.
- **`snapshot.request_hash`**: SHA-256 hash of canonicalized payload.
- **`snapshot.payload`**: Canonical JSON payload representation.

**Requirements for canonical payload**:
- lexicographically sorted keys
- UTF-8 encoding
- no insignificant whitespace
- deterministic serialization

---

## 3. Canonical Lifecycle States

REST lifecycle states **MUST** mirror canonical QRTX job states. Transport-specific lifecycle states are prohibited.

**Allowed states**:

```
PENDING
COMPILING
QUEUED
RUNNING
DONE
ERROR
CANCELED
```

---

## 4. Error Response Contract

**HTTP Status**

```http
4xx / 5xx
```

**Error Envelope**

```json
{
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "benchmark run request validation failed",
    "details": [
      {
        "code": "field_required",
        "field": "idempotency_key",
        "message": "idempotency_key is required and must be a non-empty string"
      }
    ]
  }
}
```

---

### 4.1 Canonical Error Codes

REST responses **MUST** map canonical internal gRPC status codes.

**Allowed canonical codes**:

```
INVALID_ARGUMENT
UNAUTHENTICATED
PERMISSION_DENIED
RESOURCE_EXHAUSTED
ALREADY_EXISTS
FAILED_PRECONDITION
INTERNAL
UNAVAILABLE
DEADLINE_EXCEEDED
CANCELLED
```

---

### 4.2 Validation Rules

- **`idempotency_key`**: MUST exist, MUST be string, MUST be non-empty
- **`config`**: MUST exist, MUST be object, MUST be non-empty

---

## 5. Idempotency Semantics

The system **MUST** guarantee idempotent benchmark submission.

**Rules**:
- If the same `idempotency_key` is reused with **identical** canonical payload → return the original response.
- If the same `idempotency_key` is reused with **different** canonical payload → return `ALREADY_EXISTS`.

---

## 6. Canonical JSON Rules

Canonical payload generation **MUST**:
- sort keys lexicographically
- use UTF-8 encoding
- remove insignificant whitespace
- normalize floating-point representation
- preserve array ordering
- reject NaN/Infinity values

Hash generation **MUST** be deterministic across platforms.

---

## 7. Security Requirements

The endpoint **MUST** comply with the Eigen OS Security Module requirements.

### 7.1 Authentication
- OAuth2/JWT authentication **REQUIRED**
- JWT validation **MUST** be delegated to the Security Module
- Expired or invalid tokens **MUST** return `UNAUTHENTICATED`

---

### 7.2 Authorization
Authorization **MUST** use centralized RBAC/ABAC policies. The system **MUST** validate:
- benchmark execution permissions
- backend access permissions
- dataset access permissions
- quota permissions

Unauthorized requests **MUST** return `PERMISSION_DENIED`.

---

### 7.3 Transport Security
- TLS 1.3
- mTLS for internal services

---

### 7.4 Tenant Isolation
Benchmark runs **MUST** be namespace-isolated per authenticated tenant. Users **MUST NOT**:
- access foreign runs
- infer foreign run existence
- access foreign benchmark artifacts

---

### 7.5 Audit Requirements
Every benchmark submission **MUST** generate immutable audit records containing:
- `user_id`
- `request_hash`
- `trace_id`
- `timestamp`
- `authorization result`
- `originating IP/service`

Audit entries **MUST** be immutable.

---

## 8. Observability Requirements

The endpoint **MUST** emit OpenTelemetry traces and metrics.

**Required Metrics**:

```
benchmark_run_created_total
benchmark_run_validation_failed_total
benchmark_run_duration_seconds
benchmark_run_state_transitions_total
```

**Required Trace Metadata**  
Each request **MUST** generate: `trace_id`, `correlation_id`, `audit_event_id`.

Tracing **MUST** propagate through: REST API → QRTX → Benchmark Pipeline → Knowledge Base.

---

## 9. Dataset Resolution

Datasets referenced in benchmark configuration **MUST** be resolved through Dataset Pipeline Service.

Dataset loading **MUST**:
- validate schema
- verify dataset version
- cache artifacts in QFS-L3
- register provenance in Knowledge Base

---

## 10. Backend Validation

The `backend` field **MUST** reference a registered QDriver backend. Validation **MUST** verify:
- backend existence
- backend availability
- capability compatibility
- calibration freshness
- authorization permissions

Backend resolution **MUST** occur through Driver Manager.

---

## 11. Knowledge Base Integration

Successful benchmark runs **MUST** ingest:
- TaskRecord
- benchmark metadata
- execution metrics
- backend topology
- noise characteristics
- benchmark outputs

into the Knowledge Base.

Benchmark runs marked as `training_eligible` **MUST** participate in Continuous Learning pipelines.

---

## 12. Provenance Tracking

Each benchmark run **MUST** maintain provenance relationships:

```
run_id ↔ task_record ↔ circuit_records ↔ compiler_trace ↔ dataset_version
```

The provenance chain **MUST** remain queryable after archival.

---

## 13. Storage Integration

Benchmark artifacts **MUST** be stored using QFS.

**QFS-L3** (Persistent):
- benchmark snapshots
- benchmark outputs
- logs
- reports
- metadata

**QFS-L2** (Temporary):
- transient execution checkpoints
- intermediate quantum states

---

## 14. Retention and Archival

Benchmark artifacts **MUST** follow QFS retention policies.

- **Hot Storage**: active runs, recent benchmark snapshots
- **Cold Storage**: archived benchmark artifacts

Metadata **MUST** remain queryable after archival.

---

## 15. Deadlines and Cancellation

The endpoint **MUST** support client deadlines, timeout enforcement, and cancellation propagation.

Cancellation **MUST** propagate through: REST API → QRTX → Driver Manager → QDriver.

---

## 16. Versioning and Compatibility

**Contract Version**: `1.0.0`

**Backward-Compatible Changes** (allowed):
- new optional fields
- additive metadata
- non-breaking telemetry extensions

**Breaking Changes**

Require MAJOR version increment:

- required field changes
- lifecycle changes
- semantic behavior changes
- error contract modifications

Breaking changes MUST include:

- migration documentation
- compatibility guidance
- parallel version support

---

## 17. Acceptance Criteria

The implementation **MUST** satisfy:
- request validation < 50 ms
- queue submission < 100 ms
- deterministic request hashing
- idempotent retry behavior
- authenticated access only
- observability integration
- QRTX lifecycle compatibility

---

## 18. Implementation Requirements

**Mandatory Components**:
- REST transport layer
- canonical gRPC System API integration
- durable persistence
- JWT authentication
- RBAC/ABAC authorization
- OpenTelemetry instrumentation
- QFS integration
- Knowledge Base ingestion
- audit logging
- Driver Manager validation

---

## 19. Current Implementation Status

**Implemented**:
- benchmark contract logic
- validation
- idempotency handling
- snapshot generation
- fixture contract tests

**Missing / Partial**:
- Production REST handler
- Durable persistence
- Security (JWT, RBAC, tenant isolation)
- Full OpenTelemetry
- Knowledge Base & QFS integration

---

## 20. Required Completion Tasks

1. Implement production REST handler
2. Integrate canonical gRPC System API
3. Add durable persistence layer
4. Integrate Security Module
5. Implement OpenTelemetry tracing/metrics
6. Integrate QFS storage
7. Implement Knowledge Base ingestion
8. Add Driver Manager backend validation
9. Add Dataset Pipeline integration
10. Implement audit logging
11. Add CI contract compatibility validation
12. Add cancellation/deadline propagation
13. Add multi-tenant isolation
14. Add retention and archival policies

---

## 21. Compliance Statement

An implementation is considered compliant only if:

- all mandatory sections are implemented
- canonical lifecycle semantics are preserved
- REST remains a transport binding over System API
- all security requirements are enforced
- all observability requirements are enforced
- deterministic idempotency is guaranteed
- provenance tracking is preserved
- Continuous Learning integration remains functional

---

## 22. References

- Eigen OS Technical Specification v1.3.0
- QRTX Scheduling Contract
- QDriver API Contract
- Knowledge Base Contract
- Security Module Specification
- Dataset Pipeline Contract
- OpenTelemetry Specification
- RFC 9110 (HTTP Semantics)
- RFC 7519 (JWT)
- RFC 8446 (TLS 1.3)
