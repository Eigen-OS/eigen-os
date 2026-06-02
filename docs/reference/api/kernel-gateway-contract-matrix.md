# KernelGateway Internal Contract Matrix and State Machine

**Document status:** Normative  
**Contract version:** `1.0.0`  
**Last updated:** 2026-06-02  
**Related documents:**
- `docs/reference/api/grpc-internal.md`
- `proto/eigen/internal/v1/kernel_gateway.proto`
- `rfcs/0004-public-gRPC-API-v0.1.md`
- `rfcs/0007-qrtx-mvp.md`

---

## 1. Purpose

This document defines the authoritative internal **KernelGatewayService** contract for Eigen OS, including:

- Complete method and message matrix,
- canonical lifecycle state machine and terminal state semantics,
- state transition rules and invalid-transition error mapping,
- event subscription/streaming semantics,
- internal request metadata requirements,
- deterministic deadline and retry behavior,
- versioning and compatibility obligations.

The **KernelGatewayService** is the primary internal bridge between System API and QRTX, and must enforce strict lifecycle contracts to ensure deterministic observability, auditability, and replay-safety.

---

## 2. Canonical Service Definition

```proto
service KernelGatewayService {
  rpc EnqueueJob(EnqueueJobRequest)
    returns (EnqueueJobResponse);

  rpc GetJobStatus(GetJobStatusRequest)
    returns (GetJobStatusResponse);

  rpc CancelJob(CancelJobRequest)
    returns (CancelJobResponse);

  rpc GetJobResults(GetJobResultsRequest)
    returns (GetJobResultsResponse);

  rpc PollJobUpdates(PollJobUpdatesRequest)
    returns (stream JobUpdateEvent);
}
```

---

## 3. Method/Message Matrix

### 3.1 EnqueueJob

**Purpose:** Create a new job and enqueue into QRTX for orchestration.

**Request:** `EnqueueJobRequest`

| Field | Type | Required | Description |
|---|---|---|---|
| `request_id` | string | yes | Unique request correlation ID for idempotency and tracing. |
| `job_name` | string | yes | User-friendly job identifier. |
| `program` | bytes | yes | Program payload (AQO protobuf or JSON). |
| `program_format` | string | yes | Format identifier: `aqo_proto`, `aqo_json`, or `qasm3_text`. |
| `target` | string | yes | Backend identifier (e.g., `sim:local`, `vendor:device`). |
| `priority` | int32 | no | Priority [0..100], default 50. |
| `compiler_options` | map | no | Compiler configuration overrides. |
| `execution_options` | map | no | Runtime execution options. |
| `metadata` | map | no | Arbitrary job metadata. |
| `tenant_id` | string | yes | Tenant scope (security boundary). |
| `project_id` | string | yes | Project scope within tenant. |
| `deadline_seconds` | uint32 | no | Total deadline in seconds; 0 means server default. |
| `trace_context` | map | yes | W3C TraceContext headers (traceparent, tracestate). |

**Response:** `EnqueueJobResponse`

| Field | Type | Description |
|---|---|---|
| `job_id` | string | Canonical job identifier (deterministically generated). |
| `state` | TaskState | Initial state (always `TASK_STATE_PENDING`). |
| `created_at` | Timestamp | Job creation timestamp. |

**Semantics:**

- MUST validate authorization via Security Module before accepting.
- MUST assign deterministic `job_id` based on tenant/project/name/hash.
- MUST persist JobSpec into QFS at `circuit_fs/<job_id>/job.yaml`.
- MUST enqueue job into QRTX scheduler.
- MUST initialize internal state machine to `PENDING`.
- Idempotency: if `request_id` matches prior successful request within retention window, return same `job_id`.
- MUST return gRPC status `INVALID_ARGUMENT` if program format is unsupported.
- MUST return gRPC status `PERMISSION_DENIED` if authorization fails.
- MUST return gRPC status `RESOURCE_EXHAUSTED` if tenant/project quota exceeded.

---

### 3.2 GetJobStatus

**Purpose:** Query current job lifecycle state and progress.

**Request:** `GetJobStatusRequest`

| Field | Type | Required | Description |
|---|---|---|---|
| `request_id` | string | yes | Request correlation ID. |
| `job_id` | string | yes | Job identifier. |
| `tenant_id` | string | yes | Tenant scope (authorization check). |
| `trace_context` | map | yes | W3C TraceContext. |

**Response:** `GetJobStatusResponse`

| Field | Type | Description |
|---|---|---|
| `job_id` | string | Job identifier. |
| `state` | TaskState | Current canonical state. |
| `stage` | string | Optional sub-stage label (e.g., "COMPILING", "EXECUTING", "STORING_RESULTS"). |
| `progress` | float | Progress hint in [0.0..1.0]; semantics depend on stage. |
| `message` | string | Optional human-readable status message. |
| `updated_at` | Timestamp | Last state transition timestamp. |
| `error_code` | string | Terminal error code if state == `TASK_STATE_ERROR`. |
| `error_summary` | string | Human-readable error summary. |
| `error_details_ref` | string | QFS reference to full error/logs/trace. |

**Semantics:**

- MUST return current canonical state from QRTX state machine.
- MUST return gRPC status `NOT_FOUND` if job does not exist.
- MUST return gRPC status `PERMISSION_DENIED` if tenant mismatch.
- MUST include `updated_at` with nanosecond precision for causality tracking.
- If state is terminal (`DONE`, `ERROR`, `CANCELLED`), `updated_at` is immutable.

---

### 3.3 CancelJob

**Purpose:** Initiate cancellation of a job and all downstream work.

**Request:** `CancelJobRequest`

| Field | Type | Required | Description |
|---|---|---|---|
| `request_id` | string | yes | Request correlation ID. |
| `job_id` | string | yes | Job identifier. |
| `tenant_id` | string | yes | Tenant scope. |
| `reason` | string | no | Cancellation reason (for audit trail). |
| `trace_context` | map | yes | W3C TraceContext. |

**Response:** `CancelJobResponse`

| Field | Type | Description |
|---|---|---|
| `accepted` | bool | true if cancellation request accepted. |
| `previous_state` | TaskState | State before cancellation attempt. |
| `final_state` | TaskState | State after cancellation. |

**Semantics:**

- MUST validate authorization (tenant/project match).
- MUST be idempotent: multiple cancellations of same job are safe.
- MUST propagate cancellation signal to:
  - Compiler (if in COMPILING state),
  - Driver Manager (if in RUNNING state),
  - QFS (mark artifacts for cleanup if cleanup_on_cancel policy set).
- MUST transition job to `TASK_STATE_CANCELLED` unless already in terminal state.
- If job already in terminal state, return `FAILED_PRECONDITION`.
- MUST emit structured cancellation log with trace_id, job_id, reason.
- MUST release reserved resources (qubits, quotas).

---

### 3.4 GetJobResults

**Purpose:** Retrieve final results after job completion.

**Request:** `GetJobResultsRequest`

| Field | Type | Required | Description |
|---|---|---|---|
| `request_id` | string | yes | Request correlation ID. |
| `job_id` | string | yes | Job identifier. |
| `tenant_id` | string | yes | Tenant scope. |
| `trace_context` | map | yes | W3C TraceContext. |

**Response:** `GetJobResultsResponse`

| Field | Type | Description |
|---|---|---|
| `job_id` | string | Job identifier. |
| `state` | TaskState | Terminal state (`DONE`, `ERROR`, or `CANCELLED`). |
| `counts` | map<string, int64> | Measurement outcome histogram; omitted if ERROR or CANCELLED. |
| `metadata` | map<string, string> | Result metadata (execution time, backend, etc.). |
| `error_code` | string | Error code if state == `TASK_STATE_ERROR`. |
| `error_summary` | string | Error summary. |
| `error_details_ref` | string | QFS reference to full error details/logs. |
| `completed_at` | Timestamp | Completion timestamp. |
| `result_ref` | string | QFS reference to full result artifact. |

**Semantics:**

- MUST return gRPC status `NOT_FOUND` if job does not exist.
- MUST return gRPC status `FAILED_PRECONDITION` if job is not in terminal state.
- MUST normalize result histogram to canonical bit ordering (per backend).
- MUST include QFS references to full artifacts for auditability and replay.
- Results are immutable once terminal state reached.

---

### 3.5 PollJobUpdates (streaming)

**Purpose:** Subscribe to incremental job state updates via server streaming.

**Request:** `PollJobUpdatesRequest`

| Field | Type | Required | Description |
|---|---|---|---|
| `request_id` | string | yes | Request correlation ID. |
| `job_id` | string | yes | Job identifier. |
| `tenant_id` | string | yes | Tenant scope. |
| `last_event_seq` | uint64 | no | Resume point (0 = from start). |
| `heartbeat_interval_ms` | uint32 | no | Desired heartbeat cadence; server may use different value. |
| `deadline_seconds` | uint32 | no | Stream deadline (not individual event timeout). |
| `trace_context` | map | yes | W3C TraceContext. |

**Response (streamed):** `JobUpdateEvent`

| Field | Type | Description |
|---|---|---|
| `event_seq` | uint64 | Monotonic per-job sequence number (starts at 1). |
| `job_id` | string | Job identifier. |
| `state` | TaskState | New state (or same state for heartbeat). |
| `stage` | string | Sub-stage label. |
| `progress` | float | Progress hint. |
| `message` | string | Status message. |
| `timestamp` | Timestamp | Event emission timestamp. |
| `is_terminal` | bool | true if event is terminal (`DONE`, `ERROR`, `CANCELLED`). |

**Semantics:**

- MUST emit events in strict temporal order per job_id.
- MUST emit exactly one terminal event: `(DONE | ERROR | CANCELLED)` with `is_terminal = true`.
- MUST emit heartbeat events (unchanged state) at least every `heartbeat_interval_ms` if job is still active.
- MUST use monotonically increasing `event_seq` (no gaps or resets).
- Resume on `last_event_seq` is best-effort in MVP (mandatory in Phase 1+); if event buffer exhausted, may restart from latest.
- MUST propagate stream cancellation to QRTX (e.g., if client cancels, does NOT auto-cancel job).
- MUST enforce stream deadline (not individual event timeout).
- MUST return gRPC status `NOT_FOUND` if job does not exist.
- MUST return gRPC status `PERMISSION_DENIED` if tenant mismatch.
- On error, close stream with gRPC error status.

---

## 4. Canonical Lifecycle State Machine

### 4.1 State Definitions

```
enum TaskState {
  TASK_STATE_UNSPECIFIED = 0;  // Invalid/unset
  TASK_STATE_PENDING = 1;      // Initial: queued for compilation
  TASK_STATE_COMPILING = 2;    // Compiling Eigen-Lang → AQO
  TASK_STATE_QUEUED = 3;       // Compiled, awaiting backend resources
  TASK_STATE_RUNNING = 4;      // Executing on backend
  TASK_STATE_DONE = 5;         // Terminal: successful completion
  TASK_STATE_ERROR = 6;        // Terminal: execution/system error
  TASK_STATE_CANCELLED = 7;    // Terminal: user-initiated cancellation
  TASK_STATE_TIMEOUT = 8;      // Terminal: deadline exceeded
}
```

### 4.2 State Transition Graph

**Valid transitions:**

```
PENDING
  ├─→ COMPILING       [normal path]
  ├─→ CANCELLED       [user-initiated cancellation]
  └─→ ERROR           [validation failure]

COMPILING
  ├─→ QUEUED          [compilation succeeded]
  ├─→ CANCELLED       [cancellation during compilation]
  ├─→ ERROR           [compilation failure]
  └─→ TIMEOUT         [compilation exceeded deadline]

QUEUED
  ├─→ RUNNING         [backend resources acquired]
  ├─→ CANCELLED       [user cancellation before execution]
  ├─→ ERROR           [scheduling failure]
  └─→ TIMEOUT         [deadline exceeded]

RUNNING
  ├─→ DONE            [successful execution & result storage]
  ├─→ ERROR           [execution failure or result storage failure]
  ├─→ CANCELLED       [user cancellation during execution]
  └─→ TIMEOUT         [execution exceeded deadline]

DONE            [terminal: no further transitions]
ERROR           [terminal: no further transitions]
CANCELLED       [terminal: no further transitions]
TIMEOUT         [terminal: no further transitions]
```

### 4.3 Invalid Transitions and Error Codes

| From | To (Invalid) | gRPC Code | Error Code | Details |
|---|---|---|---|---|
| DONE/ERROR/CANCELLED/TIMEOUT | Any non-terminal | `FAILED_PRECONDITION` | `INVALID_STATE_TRANSITION` | Cannot transition from terminal state. |
| Any non-terminal | Any non-adjacent | `INTERNAL` | `INVALID_STATE_MACHINE_BUG` | Kernel bug: state machine violation. |
| * | UNSPECIFIED | `INTERNAL` | `INVALID_STATE_UNSPECIFIED` | Kernel must never emit UNSPECIFIED. |

**Example:** if PENDING job is already CANCELLED, calling CancelJob again returns `FAILED_PRECONDITION` with `ALREADY_CANCELLED`.

### 4.4 Terminal State Semantics

**DONE state:**
- Job executed successfully, results stored in QFS.
- `counts` histogram is canonical and immutable.
- No further work scheduled.
- `completed_at` marks completion timestamp.

**ERROR state:**
- Job failed due to:
  - Compilation error (source syntax, unsupported construct),
  - Execution error (backend failure, timeout, resource exhaustion),
  - System error (storage failure, scheduler failure).
- `error_code` and `error_details_ref` must be populated.
- Results (if any) are best-effort and may be incomplete.
- No retry is automatic; user may resubmit.

**CANCELLED state:**
- User requested cancellation via CancelJob RPC.
- All downstream work (compilation, execution) stopped.
- Resources released.
- Results are discarded.

**TIMEOUT state:**
- Job deadline exceeded.
- Execution stopped, backend execution cancelled.
- `error_details_ref` must reference timeout context (deadline, elapsed time).

---

## 5. Internal Request Metadata

All KernelGatewayService RPCs MUST propagate the following metadata:

### 5.1 Mandatory Metadata

| Metadata Key | Type | Purpose |
|---|---|---|
| `x-eigen-request-id` | string | Request correlation and idempotency key. |
| `x-eigen-tenant-id` | string | Tenant scope (security boundary). |
| `x-eigen-project-id` | string | Project scope within tenant. |
| `x-eigen-user-id` | string | Calling user (from System API auth context). |
| `x-eigen-service-id` | string | Calling service identifier (e.g., "system-api" or "test-harness"). |
| `traceparent` | string | W3C TraceContext parent; format: `00-<trace-id>-<parent-id>-<flags>`. |
| `tracestate` | string | W3C vendor tracestate (optional). |
| `authorization` | string | Bearer token or service identity assertion. |

### 5.2 Optional Metadata

| Metadata Key | Type | Purpose |
|---|---|---|
| `x-eigen-idempotency-key` | string | Explicit idempotency key (used by EnqueueJob). |
| `x-eigen-deadline-seconds` | uint32 | Per-request deadline override. |
| `x-eigen-retry-count` | uint32 | Retry attempt number (for observability). |

### 5.3 Propagation Semantics

- **System API → KernelGateway:** System API MUST inject all mandatory metadata before calling KernelGatewayService.
- **KernelGateway → downstream services:** KernelGatewayService MUST propagate all received metadata to downstream services (Compiler, DriverManager, QFS).
- **W3C TraceContext:** KernelGatewayService MUST generate a new child span and update `traceparent` header before forwarding to downstream services.

---

## 6. Deadline and Retry Semantics

### 6.1 Deadline Propagation

- **User deadline:** specified in EnqueueJobRequest or gRPC deadline metadata.
- **Default deadline:** if not specified, server applies default (e.g., 24 hours for PENDING+COMPILING+RUNNING).
- **Propagation:** KernelGatewayService MUST propagate deadline to all downstream services.
- **Timeout behavior:** if job execution exceeds deadline, transition to `TASK_STATE_TIMEOUT`, not `ERROR`.

### 6.2 Retry Policy

| RPC | Idempotent | Retry Logic |
|---|---|---|
| EnqueueJob | yes | Explicit idempotency key; server caches response for retention window (e.g., 5 minutes). If `request_id` matches, return cached response. |
| GetJobStatus | yes | No special handling; safe to retry. |
| CancelJob | yes | Multiple cancellations same job are safe (no-op if already terminal). |
| GetJobResults | yes | No special handling; safe to retry. |
| PollJobUpdates | partial | Resume on `last_event_seq` is best-effort; full replay not guaranteed in MVP. |

### 6.3 Exponential Backoff

When downstream services return `UNAVAILABLE` or `RESOURCE_EXHAUSTED`, KernelGatewayService MUST:
1. Retry with exponential backoff (base 100ms, max 32s).
2. Emit structured retry log with attempt count, sleep duration, and error reason.
3. After max retries, return `UNAVAILABLE` to caller.

---

## 7. Security Context

### 7.1 Authorization Checks

All KernelGatewayService RPCs MUST:
1. Extract tenant/project from request or auth context.
2. Call Security Module to validate caller has `jobs:read` or `jobs:write` scope.
3. Enforce tenant isolation: jobs belong to tenant; cross-tenant access forbidden.
4. Return `PERMISSION_DENIED` if check fails.

### 7.2 Audit Trail

All mutations (EnqueueJob, CancelJob) MUST emit audit logs with:
- caller identity (`x-eigen-user-id`),
- action (submit/cancel),
- job_id,
- timestamp,
- result (success/failure reason),
- trace_id (for correlation).

---

## 8. Trace Context and Observability

### 8.1 Span Creation

Each KernelGatewayService RPC MUST create an OpenTelemetry span with:

| Attribute | Value |
|---|---|
| `rpc.service` | `eigen.internal.v1.KernelGatewayService` |
| `rpc.method` | (EnqueueJob / GetJobStatus / CancelJob / GetJobResults / PollJobUpdates) |
| `eigen.job_id` | Job ID (if applicable) |
| `eigen.tenant_id` | Tenant ID |
| `eigen.user_id` | User ID |
| `eigen.trace_id` | W3C trace ID |
| `rpc.status` | gRPC status code (OK, INVALID_ARGUMENT, etc.) |

### 8.2 Metrics

Each RPC MUST increment:
- `kernel_gateway_requests_total{method, status}` (counter)
- `kernel_gateway_latency_ms{method}` (histogram)
- `kernel_gateway_errors_total{method, error_code}` (counter)

---

## 9. Versioning and Compatibility

### 9.1 Proto Versioning

All protobuf definitions MUST follow SemVer:
- **Minor additions:** new optional fields, new enum values, new RPCs.
- **Major changes:** field removal, semantic changes, required field additions.

### 9.2 Compatibility Marker

All request/response messages MUST include a versioned contract envelope:

```proto
message ContractEnvelope {
  string contract_version = 1;  // SemVer (e.g., "1.0.0")
  map<string, string> metadata = 2;  // Extensibility
}
```

### 9.3 Breaking Change Notification

If a breaking change is required:
1. Create new proto package version (e.g., `eigen.internal.v2`).
2. Support both v1 and v2 in runtime for grace period.
3. Emit deprecation warnings for v1 calls.
4. Document migration path in RFC + ADR.
5. Set sunset date for v1 support.

---

## 10. Implementation Checklist

- [ ] Proto definitions locked and linted with `buf lint` + `buf breaking`.
- [ ] All state transitions tested with explicit test cases.
- [ ] Idempotency semantics implemented and tested.
- [ ] Metadata propagation enforced in all downstream calls.
- [ ] Deadline propagation tested end-to-end.
- [ ] Error codes mapped to gRPC status codes.
- [ ] Audit trail logging instrumented.
- [ ] OpenTelemetry spans created for all RPCs.
- [ ] Metrics exported and scraped successfully.
- [ ] Trace context propagation validated with jaeger or equivalent.
- [ ] Authorization checks enforced.
- [ ] Streaming semantics (heartbeat, terminal events) tested.
- [ ] State machine diagram documented and validated against implementation.
- [ ] Versioning and compatibility tests added to CI.

---

## 11. Appendix A: State Transition Validation Rules

QRTX MUST enforce these invariants at every transition:

1. **No state skipping:** transitions must be adjacent in state graph.
2. **No re-entrancy:** if job currently in state S, pending transition to S' is idempotent (no effect if S == S').
3. **No concurrent transitions:** all state changes serialized (via QRTX lock or CAS).
4. **Terminal immutability:** once job reaches terminal state, no further transitions.
5. **Timestamp ordering:** each `updated_at` MUST be >= prior `updated_at` (monotonic).

---

## 12. Appendix B: Example State Traces

### Successful execution:
```
PENDING (0s)
  → COMPILING (1s, 50% progress)
  → QUEUED (5s)
  → RUNNING (6s, 25% progress)
  → RUNNING (11s, 75% progress, heartbeat)
  → DONE (15s)
```

### Compilation failure:
```
PENDING (0s)
  → COMPILING (1s)
  → ERROR (3s, error_code: COMPILE_SYNTAX_ERROR, error_details_ref: circuit_fs/job-123/errors/...)
```

### User cancellation:
```
PENDING (0s)
  → COMPILING (1s)
  → CANCELLED (2s, reason: user_requested)
```

### Deadline exceeded:
```
PENDING (0s, deadline: 30s)
  → COMPILING (1s)
  → QUEUED (5s)
  → RUNNING (6s)
  → TIMEOUT (36s, exceeded deadline)
```

---

## 13. Reference Implementation Links

- Proto definitions: `proto/eigen/internal/v1/kernel_gateway.proto`
- Service implementation: `src/services/kernel/` (Rust)
- Tests: `src/services/kernel/tests/` (state machine, transitions, metadata)
- ADR: `docs/adr/0027-wave-2-kernel-gateway-contract.md`

---

## Conclusion

The KernelGatewayService contract matrix and state machine define the authoritative behavior for the internal bridge between System API and QRTX. All implementations **MUST** conform to this specification. Deviations must be resolved through RFC/ADR process.

