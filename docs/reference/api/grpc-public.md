# Public gRPC API — `eigen.api.v1`

## Purpose

This document fixes the **current public gRPC contract state** for Eigen OS and highlights what is missing relative to the target architecture.

**Normative source of truth:** `proto/eigen/api/v1/*.proto`.

---

## Package and proto layout

- Proto package: `eigen.api.v1`.
- Public API files:
  - `proto/eigen/api/v1/job_service.proto`
  - `proto/eigen/api/v1/device_service.proto`
  - `proto/eigen/api/v1/types.proto`

> Note: older references to `eigen_api.v1` are stale; the current package name in proto is `eigen.api.v1`.

---

## Public services (implemented contract surface)

### 1) `JobService`

```proto
service JobService {
  rpc SubmitJob(SubmitJobRequest) returns (SubmitJobResponse);
  rpc GetJobStatus(GetJobStatusRequest) returns (GetJobStatusResponse);
  rpc CancelJob(CancelJobRequest) returns (CancelJobResponse);
  rpc StreamJobUpdates(StreamJobUpdatesRequest) returns (stream StreamJobUpdatesResponse);
  rpc GetJobResults(GetJobResultsRequest) returns (GetJobResultsResponse);
  rpc GetDispatchRationale(GetDispatchRationaleRequest) returns (GetDispatchRationaleResponse);
}
```

### 2) `DeviceService`

```proto
service DeviceService {
  rpc ListDevices(ListDevicesRequest) returns (ListDevicesResponse);
  rpc GetDeviceDetails(GetDeviceDetailsRequest) returns (GetDeviceDetailsResponse);
  rpc GetDeviceStatus(GetDeviceStatusRequest) returns (GetDeviceStatusResponse);
  rpc ReserveDevice(ReserveDeviceRequest) returns (ReserveDeviceResponse);
}
```

### 3) Compilation API status

Compilation is **not** part of the public frozen contract for `eigen.api.v1` and remains an internal surface.

---

## Key request/response shapes (current)

### `SubmitJobRequest`

```proto
message SubmitJobRequest {
  string name = 1;
  oneof program {
    EigenLangSource eigen_lang = 2;
    QasmSource qasm = 3;
    AqoRef aqo_ref = 4;
  }
  string target = 5;
  int32 priority = 6;
  map<string, string> compiler_options = 7;
  map<string, string> metadata = 8;
  repeated string dependencies = 9;
}
```

### `SubmitJobResponse`

```proto
message SubmitJobResponse {
  string job_id = 1;
  JobStatus status = 2;
}
```

### `JobStatus` and `JobUpdate`

- `JobStatus` contains lifecycle fields (`state`, `stage`, `progress`, `message`), timestamps, error envelope fields (`error_code`, `error_summary`, `error_details_ref`) and topology lineage (`topology`).
- `JobUpdate` carries streaming event data with `event_seq`, `timestamp`, and `topology`.

### Enums (important naming detail)

In proto, enum values are prefixed and include explicit UNSPECIFIED variants:

- `JobState`: `JOB_STATE_UNSPECIFIED`, `JOB_STATE_PENDING`, …, `JOB_STATE_TIMEOUT`
- `DeviceStatus`: `DEVICE_STATUS_UNSPECIFIED`, `DEVICE_STATUS_ONLINE`, …, `DEVICE_STATUS_ERROR_STATUS`

> Any docs/SDK examples using short forms like `PENDING` or `ONLINE` should treat them as display aliases, not canonical wire names.

---

## Behavioral contract (MVP)

## 1) Job lifecycle

1. `SubmitJob` returns `job_id` and initial `status`.
2. Client either polls `GetJobStatus` or subscribes to `StreamJobUpdates`.
3. On terminal success state, client fetches payload via `GetJobResults`.
4. `CancelJob` is accepted only for cancellable states.

## 2) Streaming semantics

- Ordering is per `job_id`.
- `last_event_seq` is a **best-effort resume point**.
- Terminal transition should be emitted once in stream semantics.

## 3) Device reservation

- `ReserveDevice` reserves scheduling capacity, not global hardware lock.
- Response contains `reservation_id` and `expires_at`.

## 4) Error signaling

- Success = gRPC `OK`.
- Failure = non-`OK` status (optionally enriched with structured details).
- Response bodies should not introduce ad-hoc `success=false` wrappers.

---

## Authentication and authorization (MVP)

- Bearer token expected in metadata header: `authorization: Bearer <token>`.
- No public auth management RPC is part of `eigen.api.v1`.

Permission model by method group:

- Jobs: `jobs:submit`, `jobs:read`, `jobs:cancel`
- Devices: `devices:list`, `devices:reserve`

---

## Versioning and compatibility

- Product/API line: MVP `0.1`.
- gRPC transport namespace: `eigen.api.v1`.
- JobSpec YAML/API versioning remains `eigen.os/v0.1` for the spec side.
- Additive changes only inside v1 (new optional fields, new RPC methods).
- Breaking changes require v2.

---

## Current gaps and missing pieces (we fix what's missing)

The proto contract is present, but several system-level guarantees are still underspecified or intentionally MVP-limited.

### A) Contract clarity gaps

1. **Idempotency key contract is not explicit in proto fields**
   - Convention exists via metadata (`client_request_id`) and source hash fallback, but not encoded as first-class field.
2. **Terminal-state matrix for `CancelJob` is not formalized in proto comments**
   - Needs explicit allowed/forbidden state table in API contract tests/docs.
3. **`GetDispatchRationale` availability conditions are not normalized**
   - Need clear behavior when rationale is unavailable (`NOT_FOUND` vs empty payload policy).

### B) Interoperability gaps

1. **Public error detail schema is not pinned in this document**
   - Need fixed mapping to `docs/reference/error-model.md` + examples per RPC.
2. **Streaming replay durability bounds are not specified**
   - `last_event_seq` is best-effort, but retention window/replay guarantees are missing.
3. **Reservation-to-submit binding is not standardized**
   - `reservation_id` is returned, but public submit path does not yet define a canonical request field for hard binding.

### C) Operational readiness gaps

1. **No documented SLA/SLO by RPC**
   - Timeouts, expected latency bands, and retry budgets are not fixed in public contract.
2. **Auth claims/roles schema is not documented as a stable contract**
   - Header format is defined, claim semantics are not.
3. **No public conformance profile for SDK generators**
   - Need a minimal compliance matrix for CLI/Python/Go clients.

---

## Required follow-up artifacts

1. Add API conformance examples for each RPC (request/response + error cases).
2. Add an explicit “state machine and cancellation legality” appendix.
3. Add a replay/retention policy note for `StreamJobUpdates`.
4. Add dispatch rationale error behavior matrix.
5. Add security appendix for token claim requirements.

These follow-ups should be tracked as contract hardening tasks before any post-MVP freeze widening of public API.
    
