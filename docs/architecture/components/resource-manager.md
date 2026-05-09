# Resource Manager – Current State (May 2026)

- **Phase**: MVP line (Phase 0 → MVP-3 hardening in adjacent components)
- **Status**: **No dedicated Resource Manager service is implemented yet.** The public device API exists, but resource allocation/reservation logic from RFC 0004 / RFC 0007 is mostly not implemented end-to-end.

## Responsibility

**What is implemented now:**

- Public `DeviceService` handlers exist in `system-api` for `ListDevices`, `GetDeviceDetails`, `GetDeviceStatus`, and `ReserveDevice`.
- Device responses are currently static/simplified (`sim:local`, status online, queue depth 0).
- `ReserveDevice` currently returns a generated `reservation_id` and timestamp, without binding to scheduler/kernel state.

**TODO (not implemented yet):**

- TODO: Implement real resource manager ownership inside Kernel (QRTX) for slot accounting (`device_id -> available slots`).
- TODO: Implement reservation registry (`reservation_id -> job_id, expires_at, device_id`) in kernel state.
- TODO: Implement queue-depth and ETA derivation from real scheduler/runtime queues.
- TODO: Implement logical isolation policy enforcement beyond input validation/auth checks.
- TODO: Define whether Resource Manager remains embedded in kernel or becomes a standalone service in Phase 2+.

## Interfaces

**What is implemented now:**

- Public API contract includes `DeviceService.ReserveDevice` (`proto/eigen/api/v1/device_service.proto`).
- Internal kernel gateway (`KernelGatewayService`) currently covers only job lifecycle (`EnqueueJob`, `GetJobStatus`, `CancelJob`, `GetJobResults`) and does **not** expose device reservation RPCs.
- Driver Manager has internal `ListDevices` / `GetDeviceStatus`, but System API device handlers are currently not wired to Kernel Resource Manager state.

**TODO (not implemented yet):**

- TODO: Add/approve internal interface between system-api and kernel for device status aggregation and reservation lifecycle.
- TODO: Wire `DeviceService` methods to kernel/driver-manager-backed runtime data instead of static responses.
- TODO: Freeze and test the internal reservation contract in RFC/ADR once implemented.

## Inputs / Outputs

**What is implemented now:**

- Inputs: external `DeviceService` calls reach `system-api` handlers.
- Outputs: `system-api` returns immediate responses for status/reservation.
- Current outputs are not coupled to real kernel scheduler capacity or reservation tables.

**TODO (not implemented yet):**

- TODO: Consume driver-manager device status as one source of truth for hardware availability.
- TODO: Combine hardware status + scheduler pressure into aggregated `DeviceStatus` response (as required by RFC 0007).
- TODO: On reservation, return deterministic acceptance/denial based on actual slot availability and policy.
- TODO: Add explicit reservation release/expiry feedback into API and logs/metrics.

## Storage / State

**What is implemented now:**

- Reservation data is not persisted and no durable reservation store exists.
- Current `ReserveDevice` behavior is effectively stateless beyond response generation.

**TODO (not implemented yet):**

- TODO: Implement in-memory kernel reservation state for MVP behavior.
- TODO: Define restart behavior for active reservations (loss/rehydration policy).
- TODO: Decide if/when QFS or another durable store is needed for reservation auditing/history.

## Failure Modes

**What is implemented now:**

- Validation/auth errors are handled at `system-api` layer.
- There is no implemented kernel reservation state machine to reconcile offline devices, stale reservations, or partitions.

**TODO (not implemented yet):**

- TODO: Implement device-offline handling that invalidates or reassigns active reservations consistently.
- TODO: Implement reservation expiry sweeper and stale-cleanup strategy.
- TODO: Implement explicit degraded behavior for network partitions and partial backend outages.
- TODO: Add conformance tests for failure transitions in reservation lifecycle.

## Observability

**What is implemented now:**

- General runtime observability exists across services, but Resource Manager-specific metrics from the original MVP summary are not fully implemented as a coherent set.
- Structured request logging exists in service handlers.

**TODO (not implemented yet):**

- TODO: Implement/finalize metrics for slot totals/availability, active reservations, and reservation durations:
  - `eigen_kernel_device_slots_total{device_id}`
  - `eigen_kernel_device_slots_available{device_id}`
  - `eigen_kernel_reservations_active`
  - `eigen_kernel_reservation_duration_seconds`
- TODO: Enforce reservation lifecycle log schema with `device_id`, `reservation_id`, `job_id`, `action`.
- TODO: Add alerting/SLOs for reservation starvation, leaked reservations, and stale queue-depth reporting.

---

## RFC/ADR Reconciliation Notes

- **RFC 0004 (Public gRPC API):** Public `ReserveDevice` shape exists, but current implementation is a thin placeholder and is not yet backed by kernel resource accounting.
- **RFC 0007 (QRTX MVP):** Expected kernel resource-manager scheduler state (queue depth, reservation status, ETA aggregation) is documented but not fully implemented end-to-end.
- **ADR set (`docs/adr/*`):** Later ADRs focus on phases 3+ (benchmarks, policy engine, plugins, DX/versioning). They do not supersede the need to complete MVP resource-manager wiring; gaps remain in runtime reservation/state integration.

This document intentionally records the **as-is state** and keeps all missing pieces as explicit TODO items so phase work can continue without losing requirements.
