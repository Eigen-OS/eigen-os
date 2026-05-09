# Internal gRPC APIs (MVP snapshot)

- **Phase**: MVP
- **Snapshot date**: 2026-05-09
- **Proto source of truth**: `proto/eigen/internal/v1/*`

This document fixes the **actual current internal gRPC contract** and explicitly marks what is still missing relative to architecture/RFC intent.

## Package and service map

Implemented package:
- `eigen.internal.v1`

Implemented services:
- `KernelGatewayService` (`kernel_gateway.proto`)
- `CompilationService` (`compilation_service.proto`)
- `DriverManagerService` (`driver_manager_service.proto`)

Common shared types:
- `CircuitPayload`, `CircuitFormat`, `DeviceInfo`, `DeviceStatus` (`types.proto`)

## 1) KernelGatewayService (System API ↔ Kernel)

### Implemented RPCs
- `EnqueueJob`
- `GetJobStatus`
- `CancelJob`
- `GetJobResults`

### Implemented contract details
- Package/name in code is `KernelGatewayService` (not legacy `KernelGateway`).
- `EnqueueJobRequest` accepts normalized program bytes: `program` + `program_format`.
- `EnqueueJobResponse` returns `job_id`, `state`, `created_at`.
- `GetJobStatusResponse` includes lifecycle fields plus error payload fields (`error_code`, `error_summary`, `error_details_ref`).
- `GetJobResultsResponse` returns `counts`, `metadata`, completion timestamp, and optional error payload fields.
- Internal task enum includes: `PENDING`, `COMPILING`, `QUEUED`, `RUNNING`, `DONE`, `ERROR`, `CANCELLED`, `TIMEOUT`.

### Missing / gaps
- `PollJobUpdates` is **not** part of this internal proto; streaming/poll adaptation is implemented in public API flow.
- Explicit auth-context fields (`subject/roles/tenant`) are not encoded as request fields in this proto; propagation is expected via metadata/pipeline policy.
- Contract-level documentation for idempotency keys on internal submit path is still missing.

## 2) CompilationService (Kernel ↔ Compiler)

### Implemented RPCs
- `CompileCircuit`
- `CompileJob`
- `OptimizeCircuit`
- `ValidateCircuit`

### Implemented contract details
- Supports direct source bytes or QFS-like `source_ref` via oneof input.
- `CompileCircuitResponse`/`CompileJobResponse` return `CircuitPayload` + metadata map.
- `CircuitPayload.format` comes from shared `CircuitFormat` enum (`AQO_JSON`, `AQO_PROTO`, `QASM3_TEXT`, `BACKEND_NATIVE`).

### Missing / gaps
- Runtime behavior currently keeps `OptimizeCircuit` and `ValidateCircuit` as `UNIMPLEMENTED` in compiler service implementation (API surface exists, production behavior incomplete).
- No frozen schema yet for compiler `options` map keys/values (currently open-ended).
- Source dereference lifecycle for `source_ref` is not fully standardized in this document (ownership/timeouts/error mapping still needs freeze).

## 3) DriverManagerService (Kernel ↔ Driver Manager)

### Implemented RPCs
- `ListDevices`
- `GetDeviceStatus`
- `ExecuteCircuit`
- `CalibrateDevice`

### Implemented contract details
- `ExecuteCircuitRequest` includes `job_id`, `device_id`, `payload`, `shots`, `options`.
- `ExecuteCircuitResponse` normalizes backend output into `counts`, `execution_time_sec`, `metadata`.
- Device discovery/status uses shared `DeviceInfo`/`DeviceStatus` types.

### Missing / gaps
- Service method `CalibrateDevice` exists in proto, but current MVP runtime behavior is documented as `UNIMPLEMENTED` in component status docs.
- Async/long-running execution interface is not present yet (single unary execute RPC in MVP).
- Standardized cross-driver metadata keys for execution diagnostics are not frozen.

## 4) Shared enums/types alignment notes

### Implemented now
- Internal enums are prefixed and explicit (`TASK_STATE_*`, `DEVICE_STATUS_*`, `CIRCUIT_FORMAT_*`).
- `DEVICE_STATUS_ERROR_STATUS` naming differs from historical shorthand (`ERROR`) used in earlier docs.

### Missing / gaps
- Some architecture text still uses legacy service/version labels (`kernel_api.v1`, etc.) and non-prefixed enum examples; full doc harmonization is still required.

## 5) Error model and cross-cutting behavior

### Implemented direction
- Internal APIs use canonical gRPC status model (not `success=false` payload flags).
- Validation/state/backend failures are expected to map to standard status codes.

Recommended canonical set for MVP operations:
- `INVALID_ARGUMENT`
- `NOT_FOUND`
- `FAILED_PRECONDITION`
- `RESOURCE_EXHAUSTED`
- `UNAVAILABLE`
- `UNIMPLEMENTED`
- `DEADLINE_EXCEEDED`

### Missing / gaps
- A single normative table that maps **every RPC + failure class → exact gRPC code + details type** is still absent.
- Retry/deadline budgets are not frozen in one reference doc for all internal callers.

## 6) Security and observability contract status

### Implemented/active baseline
- Internal APIs are intended for private service-to-service use only.
- Trace propagation uses metadata (`traceparent` / trace id context in runtime).
- Service-level metrics/logging endpoints exist across components.

### Missing / gaps
- mTLS is not yet mandatory end-to-end in MVP baseline.
- No conformance test matrix is frozen yet for mandatory propagation of `x-eigen-*` security headers on every internal hop.
- Metric names/labels for internal RPCs are not yet frozen as a reference API contract.

## 7) Architecture drift checklist (to keep docs/code synchronized)

Open items to close after this snapshot:
1. Replace residual legacy names in docs with concrete proto names:
   - `KernelGatewayService`, `CompilationService`, `DriverManagerService`
   - package `eigen.internal.v1`
2. Add explicit per-RPC behavior matrix: implemented vs stub vs planned.
3. Add conformance checks in CI for:
   - internal proto breaking changes,
   - required metadata propagation,
   - canonical error mapping consistency.
4. Freeze internal options/metadata key dictionaries where interoperability is required.

---

## References

- `proto/eigen/internal/v1/kernel_gateway.proto`
- `proto/eigen/internal/v1/compilation_service.proto`
- `proto/eigen/internal/v1/driver_manager_service.proto`
- `proto/eigen/internal/v1/types.proto`
- `docs/architecture/contract-map.md`
- `docs/architecture/components/system-api.md`
- `docs/architecture/components/compiler.md`
- `docs/architecture/components/driver-manager.md`
- `docs/architecture/components/hwe.md`
