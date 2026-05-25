# Resource Manager

- **Phase:** MVP → Phase-1 evolution baseline
- **Status snapshot date:** 2026-05-25
- **Implementation state:** Partially implemented through `system-api`, `driver-manager`, and kernel-adjacent runtime logic; no standalone Resource Manager service currently exists.

---

# Responsibility

The Resource Manager subsystem is responsible for hardware resource allocation, reservation lifecycle management, runtime scheduling coordination, and device-capacity visibility across Eigen OS execution environments.

Current implementation provides minimal public device-management APIs and placeholder reservation behavior sufficient for MVP runtime flows.

The long-term architecture target is a deterministic, production-grade resource orchestration layer integrated with QRTX, adaptive runtime systems, and hardware-aware execution policies.

---

# Responsibility Scope

## Implemented now

### Public device APIs

`system-api` currently exposes public `DeviceService` handlers for:

```text id="cax2o7"
ListDevices
GetDeviceDetails
GetDeviceStatus
ReserveDevice
```

### Device visibility

Current responses provide simplified/static runtime information including:

- `sim:local`
- online status
- queue depth = `0`

### Reservation flow

`ReserveDevice` currently:

- validates requests,
- generates `reservation_id`,
- returns reservation timestamps.

Current implementation does not bind reservations to:

- scheduler state,
- runtime capacity,
- execution queues,
- kernel slot accounting.

### Runtime integration

Current device information partially integrates with:

- `driver-manager`
- `system-api`

but is not fully coordinated through kernel runtime state.

### Runtime observability

Structured request logging exists in service handlers.

General runtime observability exists across runtime services.

---

## Required target responsibility (architecture baseline)

The production Resource Manager SHALL provide:

### Deterministic resource allocation

Support for:

- device slot accounting,
- queue-aware scheduling,
- reservation lifecycle enforcement,
- fairness and isolation policies.

### Runtime coordination

The subsystem SHALL coordinate with:

- QRTX,
- Driver Manager,
- future HWE,
- adaptive runtime systems,
- scheduler components.

### Hardware-aware scheduling

Support for:

- queue pressure evaluation,
- calibration freshness,
- topology availability,
- runtime degradation awareness,
- hardware capability constraints.

### Reservation lifecycle ownership

The subsystem SHALL manage:

- reservation creation,
- reservation expiration,
- release/revocation,
- reservation recovery after restart,
- replay-safe reservation auditing.

### Production scheduling guarantees

The subsystem SHALL support:

- deterministic scheduling,
- bounded queue latency,
- reservation isolation,
- replay-safe allocation history,
- multi-tenant policy enforcement.

---

## Architecture Position

Resource Manager is a runtime orchestration subsystem positioned between:

- `system-api`
- `eigen-kernel`
- `driver-manager`
- future `hwe`

It acts as the authoritative runtime resource coordination layer.

The subsystem is required for:

- device scheduling,
- reservation tracking,
- runtime allocation decisions,
- queue-depth visibility,
- execution fairness,
- adaptive runtime coordination.

---

## Interfaces

### 1. Public APIs

#### Implemented now

**DeviceService**

Current public APIs:

```text
ListDevices
GetDeviceDetails
GetDeviceStatus
ReserveDevice
```

**Current behavior**

Current responses are placeholder/runtime-simplified and are not fully backed by:

- kernel scheduling state,
- runtime slot accounting,
- reservation registries.

---

#### Required target public APIs

**Reservation lifecycle APIs**

Future APIs SHALL include:

```text
ReleaseReservation
ExtendReservation
GetReservationStatus
ListReservations
```

**Queue visibility APIs**

Future APIs SHALL expose:

```text
GetQueueDepth
GetEstimatedWaitTime
GetSchedulerPressure
```

**Adaptive-runtime APIs**

Future APIs SHALL support:

```text
RequestAdaptiveAllocation
SubmitHardwareConstraints
AttachExecutionPriority
```

---

### 2. Internal Runtime Interfaces

#### Implemented now

**Driver Manager integration**

Current runtime integrations:

```text
ListDevices
GetDeviceStatus
```

through Driver Manager.

**Kernel integration**

Current kernel integration is limited.

`KernelGatewayService` currently exposes:

```text
Kernel integration

Current kernel integration is limited.

KernelGatewayService currently exposes:
```

and does not expose reservation lifecycle APIs.

---

#### Required target internal interfaces

**Kernel reservation APIs**

Future kernel integrations SHALL include:

```text
ReserveExecutionSlot
ReleaseExecutionSlot
GetAllocationState
SubscribeToQueueUpdates
```

**Runtime aggregation APIs**

Future runtime aggregation SHALL support:

- hardware availability,
- scheduler pressure,
- queue depth,
- adaptive allocation state.

**HWE integration**

Future HWE integration SHALL support:

- hardware adaptation decisions,
- degraded hardware routing,
- reroute recommendations,
- topology-aware allocation.

---

## Inputs / Outputs

### Inputs

#### Implemented now

**Public API requests**

Inputs currently include:

- device queries,
- reservation requests,
- status requests.

**Runtime metadata**

Inputs currently derive partially from:

- driver-manager device visibility,
- runtime request metadata.

---

#### Required target inputs

**Scheduler/runtime metadata**

Future inputs SHALL include:

- queue state,
- reservation pressure,
- execution priority,
- tenant/runtime constraints.

**Hardware telemetry**

Future inputs SHALL include:

- device availability,
- queue pressure,
- topology degradation,
- calibration freshness,
- outage markers.

**Adaptive-runtime metadata**

Future inputs SHALL include:

- optimizer routing hints,
- HWE adaptation requests,
- deterministic replay markers.

---

### Outputs

#### Implemented now

**Device responses**

Current outputs include:

- device metadata,
- online/offline state,
- generated reservation identifiers.

**Reservation responses**

Current reservation responses include:

- reservation ID,
- timestamp.

Current responses are not tied to actual runtime allocation state.

---

#### Required target outputs

**Deterministic allocation responses**

Future outputs SHALL include:

- allocation acceptance/denial,
- reservation expiration,
- queue placement,
- estimated execution timing.

**Runtime coordination metadata**

Future outputs SHALL include:

- scheduler diagnostics,
- runtime pressure indicators,
- adaptive-routing metadata.

**Replay-safe allocation artifacts**

Future outputs SHALL include:

- reservation lineage,
- allocation audit metadata,
- deterministic replay identifiers.

---

## Storage / State

### Internal State

#### Implemented now

**Current reservation behavior**

Current reservation flow is effectively stateless beyond response generation.

No durable reservation registry exists.

---

#### Required target internal state

**Reservation registry**

Future runtime SHALL maintain:

```text
reservation_id
job_id
device_id
expires_at
allocation_state
```

**Scheduler state**

Future runtime SHALL maintain:

- queue depth,
- active allocations,
- pending reservations,
- fairness tracking.

**Replay state**

Future runtime SHALL support:

- deterministic allocation lineage,
- reservation replay validation,
- execution/resource provenance.

---

### External Storage

#### Implemented now

No dedicated persistent Resource Manager storage backend exists.

---

#### Required target storage

**Reservation persistence**

Future runtime SHALL support:

- durable reservation storage,
- restart recovery,
- audit-safe allocation history.

**Runtime analytics storage**

Future runtime SHALL support:

- queue history,
- allocation metrics,
- replay-safe scheduling history.

---

## Failure Modes

### Implemented now

#### Validation and authorization failures

Handled at the `system-api` layer.

#### Runtime limitations

Current implementation does not support:

- stale reservation cleanup,
- offline-device reconciliation,
- queue consistency guarantees,
- runtime partition handling.

---

### Required target failure taxonomy

#### Reservation failures

Future runtime SHALL classify:

- reservation denied,
- reservation expired,
- reservation conflict,
- stale reservation.

#### Hardware/runtime failures

Future runtime SHALL classify:

- device offline,
- queue saturation,
- scheduler overload,
- allocation timeout.

#### Distributed runtime failures

Future runtime SHALL classify:

- network partitions,
- inconsistent queue state,
- replay divergence,
- allocation desynchronization.

---

### Recovery and fallback requirements

The Resource Manager SHALL support:

- reservation expiry sweepers,
- stale cleanup,
- bounded retries,
- degraded scheduling modes,
- replay-safe recovery,
- deterministic fallback allocation policies.

---

## Observability

### Metrics

#### Implemented now

General runtime observability exists across services.

Structured request logging exists in handlers.

---

#### Required target metrics

**Resource allocation metrics**

```text
eigen_kernel_device_slots_total{device_id}
eigen_kernel_device_slots_available{device_id}
eigen_kernel_reservations_active
eigen_kernel_reservation_duration_seconds
```

**Scheduler metrics**

```text
eigen_kernel_queue_depth
eigen_kernel_scheduler_pressure
eigen_kernel_allocation_failures_total
```

**Adaptive-runtime metrics**

```text
eigen_hwe_adaptive_allocations_total
eigen_runtime_reroutes_total
```

---

### Logs

#### Implemented now

Structured request logging exists.

---

#### Required target logging

Future logging SHALL include:

- `device_id`
- `reservation_id`
- `job_id`
- allocation decisions
- queue diagnostics
- adaptive routing decisions
- reservation lifecycle events

---

### Traces

#### Implemented now

General runtime tracing exists across runtime services.

---

#### Required target tracing

Distributed tracing SHALL include:

- reservation lifecycle,
- scheduler decisions,
- queue placement,
- hardware adaptation events,
- deterministic replay lineage.

Required trace metadata:

- device mapping,
- allocation state,
- reservation lineage,
- queue pressure snapshot.

---

### Health Checks

#### Implemented now

General runtime health endpoints exist.

---

#### Required target health model

The subsystem SHALL expose:

- scheduler health,
- queue saturation state,
- reservation consistency validation,
- hardware availability aggregation,
- replay consistency validation.

---

### Dashboards and Alerts

#### Implemented now

Repository-level runtime dashboards/runbooks exist.

---

#### Required target dashboards

**Operational dashboards**

- device availability
- queue depth
- reservation pressure
- scheduler latency
- allocation fairness
- adaptive routing decisions

**Alert categories**

- reservation starvation
- leaked reservations
- queue saturation
- hardware outage
- replay inconsistency
- allocation desynchronization

---

## Security and Isolation

### Required target controls

#### Reservation isolation

The subsystem SHALL enforce:

- tenant isolation,
- allocation ownership validation,
- reservation authorization policies.

#### Runtime auditability

The subsystem SHALL support:

- immutable allocation audit trails,
- replay-safe reservation history,
- allocation provenance tracking.

#### Adaptive-runtime governance

The subsystem SHALL support:

- policy-controlled adaptive allocation,
- deterministic fallback enforcement,
- scheduler override auditability.

---

## Alignment Summary

### Implemented and aligned

The following MVP-aligned functionality is implemented:

- public device APIs,
- placeholder reservation flow,
- driver-manager device visibility,
- structured runtime logging,
- runtime observability baseline.

### Remaining architecture gaps

The following architecture targets remain not fully implemented:

- kernel-backed resource accounting,
- deterministic reservation lifecycle,
- queue-depth aggregation,
- durable reservation persistence,
- scheduler/resource orchestration,
- adaptive-runtime allocation integration,
- replay-safe allocation lineage,
- production-grade fairness/isolation policies.

These gaps remain explicitly preserved as required future work to prevent architecture scope loss.
