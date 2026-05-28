# Resource Manager

- **Document status:** Normative architecture + contract specification (device capacity, reservation lifecycle, allocation coordination)
- **Contract version:** `1.0.0`
- **Snapshot date:** 2026-05-25
- **Implementation state:** Partially implemented through system-api, driver-manager, and kernel-adjacent runtime logic; no standalone Resource Manager service currently exists.

---

## 1. Purpose

The Resource Manager subsystem is responsible for:

- hardware resource visibility (devices, capabilities, health),
- allocation and reservation lifecycle management,
- runtime scheduling coordination inputs (capacity, queue pressure),
- deterministic resource decisioning surfaces that other components can rely on,
- multi-tenant isolation and fairness enforcement (Phase-1+).

**MVP reality:** the repository currently exposes minimal device APIs and a **placeholder reservation flow** sufficient for MVP runtime flows, but does not yet implement:

- slot accounting,
- enforced reservations,
- kernel-backed allocation state,
- durable reservation registry,
- queue-aware scheduling integration.

This document freezes:

1. what exists today and its semantics, and
2. the required target architecture for TЗ compliance, without pretending it is already implemented.

---

## 2. Contract Versioning

### 2.1 Contract marker (recommended)

Conformant implementations SHOULD export:

```text
eigen_resource_contract_info{version="1.0.0"} 1
```

---

### 2.2 SemVer policy

#### MAJOR

- reservation semantics change incompatibly (e.g., placeholder → enforced changes without compatibility mode),
- label meaning changes incompatibly,
- required APIs removed or renamed,
- allocation invariants change.

#### MINOR

- new optional fields / labels (bounded),
- additive reservation lifecycle APIs,
- additional device/queue visibility endpoints,
- additive allocation metadata.

#### PATCH

- documentation fixes,
- bug fixes without semantic change,
- dashboard/alert tuning.

---

## 3. Responsibility

### 3.1 What Resource Manager owns (target)

Resource Manager SHALL be the authoritative coordination layer for:

- device slot/capacity accounting,
- enforced reservation lifecycle,
- queue pressure and estimated wait visibility,
- allocation fairness and isolation,
- replay-safe allocation audit lineage,
- coordination with kernel scheduler and (future) HWE/adaptive routing.

---

### 3.2 What Resource Manager does NOT own

Resource Manager MUST NOT:

- execute workloads (that is Kernel + Driver Manager),
- compile programs (Compiler),
- bypass backend normalization (Driver Manager),
- leak provider-native semantics to public contracts,
- encode transport failures in response bodies (must use gRPC status + structured details).

---

## 4. Architecture Position

Resource Manager sits between:

```text
Client SDKs / CLI
    ↓
System API (public)
    ↓
QRTX Kernel (orchestration, scheduler)
    ↓
Resource Manager (allocation & reservations)
    ↓
Driver Manager (execution abstraction)
    ↓
Backends / Simulators / Hardware
```

**Current MVP wiring reality:** there is **no dedicated Resource Manager service**; parts of the surface exist in System API and Driver Manager, with limited kernel coordination.

Resource Manager is required (target) for:

- device scheduling,
- reservation tracking,
- runtime allocation decisions,
- queue depth visibility,
- execution fairness,
- adaptive runtime coordination (Phase-1+).

---

## 5. Current Implemented Baseline (Repository Truth)

### 5.1 Public device APIs (implemented in `system-api`)

System API exposes public `DeviceService` handlers for:

```text
ListDevices
GetDeviceDetails
GetDeviceStatus
ReserveDevice
```

---

### 5.2 Device visibility (current behavior)

Current responses provide simplified/static runtime info (MVP-safe baseline), typically including:

- a small set of known devices (e.g., `sim:local`),
- online/offline status,
- queue depth often reported as `0` (placeholder).

---

### 5.3 Reservation flow (placeholder semantics)

`ReserveDevice` currently:

- validates request shape,
- generates `reservation_id`,
- returns timestamps / expiry-like metadata (deployment-dependent).

#### Normative clarification (important):

- The current reservation is **NOT enforced** against scheduler/kernel capacity.
- The current reservation does **NOT** guarantee exclusive access, slot ownership, or priority.
- The reservation MUST be treated as a **client-visible token** only, suitable for future compatibility, not a hard allocation.

If a client requests enforced reservation semantics (Phase-1 features) against an MVP deployment, the system SHOULD return:

- `UNIMPLEMENTED` (preferred) or `FAILED_PRECONDITION`,
with structured details indicating “reservations not enforced in this deployment”.

---

### 5.4 Runtime integration (partial)

- Device inventory and status are partially sourced from `driver-manager`.
- Kernel does not currently own reservation lifecycle or slot accounting.

---

### 5.5 Observability baseline (implemented)

- Structured request logging exists in service handlers.
- Trace context propagation exists across the runtime (see `observability.md`).

---

## 6. Target Responsibilities

### 6.1 Deterministic resource allocation

Resource Manager SHALL implement:

- device slot accounting,
- queue-aware placement decisions,
- deterministic allocation under deterministic mode,
- fairness/isolation policies (tenant/project),
- bounded, replay-safe scheduling inputs.

---

### 6.2 Reservation lifecycle ownership

Resource Manager SHALL own:

- reservation creation,
- reservation expiry and sweeps,
- release/revocation,
- extension (where allowed),
- restart recovery,
- audit-safe history retention,
- replay-safe reservation lineage.

---

### 6.3 Hardware-aware scheduling inputs

Resource Manager SHALL expose normalized signals:

- queue pressure,
- calibration freshness,
- topology availability,
- maintenance state,
- device capability constraints,
- outage markers / degradation states.

---

### 6.4 Coordination with runtime components

Resource Manager SHALL coordinate with:

- **QRTX Kernel** (scheduler and lifecycle owner),
- **Driver Manager** (device truth + execution abstraction),
- future **HWE** (adaptation/reroute),
- future intelligent runtime (policy/scoring).

---

## 7. Interfaces

### 7.1 Public APIs (DeviceService)

#### Implemented now

```text
ListDevices
GetDeviceDetails
GetDeviceStatus
ReserveDevice
```

#### Required target public APIs (additive)

**Reservation lifecycle**

```text
ReleaseReservation
ExtendReservation
GetReservationStatus
ListReservations
```

**Queue visibility**

```text
GetQueueDepth
GetEstimatedWaitTime
GetSchedulerPressure
```

**Adaptive-runtime allocation (Phase-1+)**

```text
RequestAdaptiveAllocation
SubmitHardwareConstraints
AttachExecutionPriority
```

---

### 7.2 Internal runtime interfaces (target)

#### Driver Manager integration (exists partially)

Current internal sources include:

- `DriverManagerService.ListDevices`
- `DriverManagerService.GetDeviceStatus`

#### Kernel integration (current limitation)

Kernel currently exposes `KernelGatewayService` for job lifecycle:

- `EnqueueJob`
- `GetJobStatus`
- `CancelJob`
- `GetJobResults`

Kernel does not currently expose reservation or allocation lifecycle APIs.

#### Required target internal interfaces

**Kernel ↔ Resource Manager (Phase-1+)**

```text
ReserveExecutionSlot
ReleaseExecutionSlot
GetAllocationState
SubscribeToQueueUpdates
```

#### Aggregation / telemetry inputs

- hardware availability,
- scheduler pressure,
- queue depth,
- allocation state.

#### HWE integration (Phase-1+)

- reroute / substitution requests,
- topology-aware allocation,
- degraded-mode routing coordination.

---

## 8. Inputs / Outputs

### 8.1 Inputs

#### Implemented now

- device queries,
- reservation requests,
- status requests,
- limited device inventory/status pulled from driver-manager.

#### Required target inputs

- queue state and allocation pressure,
- execution priority and fairness context,
- tenant/project constraints,
- topology + calibration snapshots,
- outage/degradation markers,
- deterministic replay markers (when enabled),
- optimizer/HWE hints (Phase-1+).

---

### 8.2 Outputs

#### Implemented now

- device metadata and status,
- generated reservation identifiers (placeholder tokens).

#### Required target outputs

- allocation accept/deny decisions,
- reservation expiration and enforced ownership semantics,
- queue placement and estimated wait,
- scheduler diagnostics and pressure indicators,
- replay-safe allocation artifacts and lineage references.

---

## 9. State and Storage

### 9.1 Implemented now

Reservation behavior is effectively **stateless** beyond response generation.
No durable reservation registry exists.

---

### 9.2 Required target internal state

Resource Manager SHALL maintain:

- `reservation_id`, `device_id`, `owner`, `expires_at`, `state`, `constraints`,
- active allocations and slots,
- fairness tracking,
- queue history window (bounded),
- replay lineage for deterministic mode.

---

### 9.3 Required target external storage

- durable reservation store (DB),
- audit-safe allocation history,
- queue/allocation analytics history (bounded retention),
- replay-safe scheduling history.

---

## 10. Error Semantics (Normative)

All failures MUST follow the Eigen OS error model (`error-model.md`):

- **gRPC status-first**
- structured details (e.g., `google.rpc.ErrorInfo`, `RetryInfo`, `ResourceInfo`)
- deterministic mapping.

---

### 10.1 Common mappings

- Invalid request / invalid identifiers: `INVALID_ARGUMENT` (+ `google.rpc.BadRequest`)
- Unsupported reservation semantics in MVP deployment: `UNIMPLEMENTED` (+ `ErrorInfo.reason`)
- Device not found: `NOT_FOUND` (+ `ResourceInfo`)
- Capacity/quota exceeded: `RESOURCE_EXHAUSTED` (+ `RetryInfo`)
- Temporary subsystem outage: `UNAVAILABLE` (+ `RetryInfo`)
- Unauthorized: `UNAUTHENTICATED` / `PERMISSION_DENIED`

---

### 10.2 Retryability

- `UNAVAILABLE`, `RESOURCE_EXHAUSTED`, `ABORTED`, `DEADLINE_EXCEEDED` are typically retryable.
- `FAILED_PRECONDITION` / `NOT_FOUND` are conditionally retryable depending on eventual consistency / state.
- `INVALID_ARGUMENT` is non-retryable.

---

## 11. Failure Modes (Target Taxonomy)

### 11.1 Reservation failures

- `reservation_denied`
- `reservation_expired`
- `reservation_conflict`
- `stale_reservation`
- `reservation_leak_detected`

---

### 11.2 Hardware/runtime failures

- `device_offline`
- `queue_saturated`
- `scheduler_overloaded`
- `allocation_timeout`

---

### 11.3 Distributed coordination failures

- `network_partition`
- `inconsistent_queue_state`
- `allocation_desync`
- `replay_divergence` (deterministic mode)

---

### 11.4 Recovery and fallback (required)

- expiry sweepers,
- stale cleanup,
- bounded retries + backoff,
- degraded scheduling modes,
- deterministic fallback allocation policies,
- replay-safe recovery when deterministic mode is enabled.

---

## 12. Observability

Resource Manager observability MUST remain compatible with:

- `observability.md` (global)
- orchestration observability contract for scheduler/control-plane (`orchestration-observability-contract.md`) where applicable.

---

### 12.1 Label cardinality rules (mandatory)

Metric labels MUST be bounded and MUST NOT include:

- `job_id`, `trace_id`, `request_id`, `user_id`,
- arbitrary freeform strings.

**Note on** `device_id`:

- Allowed only if the device catalog is **bounded and enumerable** for the deployment.
- If device IDs are highly dynamic/unbounded, metrics MUST use bounded dimensions instead (e.g., `backend_type`, `region`, `queue`, `class`).

---

### 12.2 Implemented now

- structured request logs,
- trace propagation across runtime services.

---

### 12.3 Required target metrics (namespaced)

#### Reservation and allocation

```text
eigen_resource_reservations_active
eigen_resource_reservations_total{result}
eigen_resource_reservation_duration_seconds_bucket
eigen_resource_allocation_attempts_total{result,reason}
eigen_resource_allocation_latency_seconds_bucket
```

#### Capacity and queue

```text
eigen_resource_device_slots_total{device_class}
eigen_resource_device_slots_available{device_class}
eigen_resource_queue_depth{queue}
eigen_resource_scheduler_pressure{queue}
```

#### Consistency / replay (when enabled)

```text
eigen_resource_allocation_desync_total{reason}
eigen_resource_replay_mismatch_total{reason}
```

---

### 12.4 Required target logging (structured)

Logs SHOULD include fields (as log attributes, not metric labels):

- `device_id`, `reservation_id`, `job_id` (when relevant),
- allocation decision, denial reason,
- queue snapshot summary,
- adaptive routing markers (Phase-1+).

---

### 12.5 Required target tracing

Distributed tracing SHALL cover:

- reservation lifecycle,
- allocation decisions,
- queue placement,
- HWE adaptation events (Phase-1+),
- replay lineage spans (deterministic mode).

---

## 13. Security and Isolation (Target)

### 13.1 Reservation isolation

Resource Manager SHALL enforce:

- tenant/project isolation,
- ownership validation on reservation operations,
- authorization for reservation and allocation actions.

---

### 13.2 Auditability

Resource Manager SHALL support:

- immutable allocation audit trails,
- replay-safe reservation history,
- provenance tracking for overrides and degraded modes.

---

### 13.3 Adaptive-runtime governance

Resource Manager SHALL support:

- policy-controlled adaptive allocation,
- deterministic fallback enforcement,
- auditable manual overrides.

---

## 14. Alignment Summary

#### Implemented and aligned (MVP baseline)

- public device APIs,
- placeholder reservation token flow (non-enforced),
- driver-manager device visibility inputs,
- structured logging and trace propagation baseline.

#### Remaining architecture gaps (explicit)

- kernel-backed resource accounting,
- enforced reservation lifecycle,
- queue-depth aggregation + estimated wait,
- durable reservation persistence + recovery,
- fairness/isolation enforcement,
- adaptive-runtime allocation integration (HWE),
- replay-safe allocation lineage and determinism controls,
- production-grade scheduling coordination.

These gaps are intentionally preserved as required Phase-1+ work to prevent architecture scope loss.
