# Resource Manager – MVP Summary

- **Phase**: MVP (Phase 0)

- **Status**: Resource management is part of the Kernel (QRTX) in MVP; no separate service. Advanced features deferred to Phase 2.

## Responsibility

**MVP Scope**: Resource management in MVP is a **simplified allocation and reservation system** embedded within the Kernel (QRTX).

**Key responsibilities in MVP:**

- Track available devices and their status (via driver-manager).

- Manage device reservations (`ReserveDevice` → scheduler slot).

- Provide aggregated device status to system-api (combining backend status + queue depth).

- Enforce simple logical isolation (no hardware-level isolation in MVP).

## Interfaces

- **Internal API**: Part of Kernel’s internal state; no separate gRPC service.

- **Public API**: Device reservation is exposed via `DeviceService.ReserveDevice` (RFC 0004).

- **Kernel integration**: Kernel’s resource manager tracks:

    - `device_id → available slots`

    - `reservation_id → job_id, expires_at`

    - Queue depth and estimated wait time per device.

## Inputs / Outputs

- **Inputs:**

    - Device status updates from driver-manager.

    - Reservation requests from system-api (`ReserveDevice`).

- **Outputs:**

    - Aggregated `DeviceStatus` for public API.

    - Reservation confirmation/denial.

## Storage / State

- **State persistence**: In-memory reservations (volatile; lost on restart).

- **QFS usage**: None for resource management in MVP.

- **Checkpointing**: Not needed; reservations are short-lived.

## Failure Modes

- **Device goes offline**: Kernel marks device unavailable; existing reservations fail.

- **Reservation expiry**: Kernel automatically cleans up expired slots.

- **Network partition**: Reservations may become stale; best-effort cleanup.

## Observability

- **Metrics:**

    - `eigen_kernel_device_slots_total{device_id}`

    - `eigen_kernel_device_slots_available{device_id}`

    - `eigen_kernel_reservations_active`

    - `eigen_kernel_reservation_duration_seconds`

- **Logs**: Include `device_id`, `reservation_id`, `job_id`, `action` (reserve/release).

---

**Note**: MVP implements **logical resource management** only (slots, queue depth). Advanced features like topology-aware allocation, hardware isolation, load balancing, and predictive allocation are planned for Phase 2+. The Resource Manager will likely evolve into a separate service in later phases.