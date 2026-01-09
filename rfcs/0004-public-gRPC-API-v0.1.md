# RFC 0004: Public gRPC API v0.1 (JobService, DeviceService, CompilationService)

- **Status:** Discussion
- **Authors:** NYankovich
- **Created:** 2026-01-08
- **Target milestone:** Phase 0 (MVP)
- **Tracking issue:** (TBD)
- **Supersedes / Related:** 0003,0006,0007

## Summary

Locks down the MVP gRPC surface used by CLI/SDKs, and defines a minimal internal kernel gateway API.

## Motivation

Stable RPC is required for a multi-language CLI/SDK ecosystem. In MVP, we keep the surface small and evolvable.

## Goals

- Define service and method names, request/response fields.
- Define streaming updates semantics.
- Define API versioning and error envelope at boundary.

## Non-Goals

- Full production-ready authn mechanisms.
- Backwards compatibility guarantees beyond MVP freeze window.

## Guide-level explanation


### MVP decision: keep public surface minimal (and move monitoring/auth out)

For **Phase 0 (MVP)**, the **only public gRPC surface** is:

- `JobService` (submit/status/updates/results)
- `DeviceService` (list/status/details/reserve)
- `CompilationService` (optional/advanced; implemented as a thin proxy from System API to Compiler)

**Not public in MVP**:
- `monitoring.proto`: metrics are exposed via HTTP `/metrics` (Prometheus scrape), not via public gRPC
- `auth.proto`: authentication/authorization is enforced by System API interceptors; no public auth RPC in MVP

**Repo layout rule (source of truth):**
- Protobuf sources live under a single root `proto/` (not nested under a service),
- generated SDKs consume the same module,
- CI runs lint + breaking checks (see RFC 0001 + tooling note below).

### Streaming semantics: StreamJobUpdates (MVP)

`StreamJobUpdates` MUST follow these rules:

- Events are **ordered** per `job_id`.
- Each `JobUpdate` includes:
  - `job_id`
  - `state` (client-visible)
  - `stage` (optional string)
  - `progress` (0..1 optional)
  - `message` (optional)
  - `event_seq` (monotonic uint64, starts at 1)
  - `timestamp`
- A terminal event is emitted exactly once: `DONE | ERROR | CANCELLED | TIMEOUT`.
- Heartbeat: while `RUNNING`, server MAY emit periodic updates (e.g., every 5–15s) even if state unchanged.
- Reconnect: client may resume from `last_event_seq` (best effort in MVP; mandatory in Phase 1).

### ReserveDevice semantics (MVP)

`ReserveDevice` reserves a **scheduler slot in Kernel Resource Manager**, not a hardware-wide exclusive lock:

- Request: `device_id`, `ttl_seconds`, optional `purpose`
- Response: `reservation_id`, `expires_at`
- Errors:
  - `FAILED_PRECONDITION` if device is offline/unavailable
  - `RESOURCE_EXHAUSTED` if no slots/quota
  - `NOT_FOUND` if unknown device_id

### Error model (public boundary)

- Success: gRPC status `OK`
- Failure: **non-OK gRPC status code**, optional structured details using `google.rpc.Status` + error details

Do not encode errors via `success=false` fields in responses.

**Client-facing services (as per `service.proto`):**
- `JobService`: SubmitJob, GetJobStatus, CancelJob, StreamJobUpdates, GetJobResults
- `DeviceService`: ListDevices, GetDeviceDetails, GetDeviceStatus, ReserveDevice
- `CompilationService`: CompileCircuit, OptimizeCircuit, ValidateCircuit

**Call pattern:**
1) client `SubmitJob` → gets `job_id`
2) client polls `GetJobStatus` OR subscribes `StreamJobUpdates`
3) when DONE, client calls `GetJobResults`.

**CompilationService** can be used either directly by clients (advanced) or internally by kernel.

## Reference-level design

### Interfaces / APIs

### service.proto (client-facing)

```proto
service JobService {
  rpc SubmitJob(SubmitJobRequest) returns (JobResponse);
  rpc GetJobStatus(JobStatusRequest) returns (JobStatusResponse);
  rpc CancelJob(CancelJobRequest) returns (CancelJobResponse);
  rpc StreamJobUpdates(JobUpdatesRequest) returns (stream JobUpdate);
  rpc GetJobResults(JobResultsRequest) returns (JobResultsResponse);
}

service DeviceService {
  rpc ListDevices(ListDevicesRequest) returns (ListDevicesResponse);
  rpc GetDeviceDetails(DeviceDetailsRequest) returns (DeviceDetailsResponse);
  rpc GetDeviceStatus(DeviceStatusRequest) returns (DeviceStatusResponse);
  rpc ReserveDevice(ReserveDeviceRequest) returns (ReserveDeviceResponse);
}

service CompilationService {
  rpc CompileCircuit(CompileCircuitRequest) returns (CompileCircuitResponse);
  rpc OptimizeCircuit(OptimizeCircuitRequest) returns (OptimizeCircuitResponse);
  rpc ValidateCircuit(ValidateCircuitRequest) returns (ValidateCircuitResponse);
}
```

### Appendix A: kernel_api.v0.1 (internal gateway)

To keep system-api thin, it forwards public requests to the kernel via an internal gateway:

- `KernelGateway.EnqueueJob(EnqueueJobRequest) -> EnqueueJobResponse`
- `KernelGateway.GetJobStatus(GetJobStatusRequest) -> GetJobStatusResponse`
- `KernelGateway.CancelJob(CancelJobRequest) -> CancelJobResponse`
- `KernelGateway.GetJobResults(GetJobResultsRequest) -> GetJobResultsResponse`
- `KernelGateway.ListDevices(...) -> ...` (optional; can be proxied to driver-manager)

This internal API is not exposed publicly and may change more freely during MVP.


### Data model

`SubmitJobRequest` MUST include: `name`, `program`, `target`.
`compiler_options`, `metadata`, `dependencies` are string maps/lists for MVP.

**Status model:** client-visible `JobStatus` maps from kernel `TaskState`:
- Pending/Validating/Compiling → COMPILING
- Queued/Allocating → QUEUED
- Executing/* → RUNNING
- Completed → DONE
- Failed → ERROR
- Cancelled → CANCELLED
- Timeout → TIMEOUT

### Error model

API boundary uses a standard error mapping:
- gRPC status code + `message`
- optional `google.protobuf.Any details` (e.g., validation errors)
Internal services may use richer errors but MUST map at boundary.

### Security & privacy

Authn/authz handled in system-api.
Auth context propagated to kernel via request metadata.
All internal services are on private network; mTLS optional for MVP.

### Observability

All requests attach `trace_id` and `job_id` in logs.
StreamJobUpdates emits periodic heartbeats while RUNNING (optional).

### Performance notes

Streaming updates reduce polling load.
Keep protobuf messages small; large artifacts are referenced via QFS refs.

## Testing plan


- Protobuf linting and breaking-change checks MUST run in CI (recommended: Buf).
- Add contract tests for StreamJobUpdates ordering and terminal events.

Protobuf contract tests; CLI integration test hits system-api in docker.
Golden mapping tests for JobStatus ↔ TaskState.

## Rollout / Migration

Freeze `eigen_api.v1` method names for MVP.
Add new fields as optional; never change semantics without a new major version.

## Alternatives considered

- Expose kernel directly as public API (rejected for now).
- Use REST only (rejected: gRPC better for streaming and typed clients).

## Open questions

- Should `CompilationService` be client-facing long-term or internal-only?
- Should we adopt `google.rpc.Status` details formally?
