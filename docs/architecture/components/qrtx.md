# Kernel (QRTX) – MVP Summary

- **Phase**: MVP (Phase 0)

- **Status**: Core scheduler and pipeline; advanced features deferred to later phases.

## Responsibility

**MVP Scope**: QRTX is the central orchestrator that manages the end-to-end job lifecycle via a **simplified pipeline** (no full DAG support yet).

**Key responsibilities in MVP:**

- Receive jobs from system-api via internal gRPC gateway.

- Manage task state machine: `Pending` → `Validating` → `Compiling` → `Queued` → `Allocating` → `Executing` → `Completing` → `Completed`.

- Coordinate with eigen-compiler (for compilation) and driver-manager (for execution).

- Persist artifacts/results to QFS (CircuitFS).

- Aggregate device status (backend status + scheduler queue info) for system-api.

## Interfaces

- **Internal gRPC API**: `KernelGateway` service (RFC 0004 Appendix A):

    - EnqueueJob, GetJobStatus, CancelJob, GetJobResults, ListDevices

- **Outbound gRPC clients:**

    - To eigen-compiler: `CompilationService` (compile/validate/optimize)

    - To driver-manager: `DriverManagerService` (execute circuit)

- **QFS client**: For storing/retrieving artifacts in `circuit_fs/<job_id>/`.

## Inputs / Outputs

- **Inputs:**

    - `EnqueueJobRequest` from system-api (contains job spec, target, metadata).

    - Device status updates from driver-manager.

- **Outputs:**

    - Job status updates to system-api (polling-based in MVP).

    - Artifacts stored in QFS: `compiled.aqo.json`, `results.json`, etc.

    - Aggregated `DeviceStatus` for public API.


## Storage / State

- **State persistence**: In-memory task state (MVP only; no durable state store).

- **QFS usage**: All artifacts stored in `circuit_fs/<job_id>/` with fixed naming.

- **Device aggregation**: Kernel maintains queue depth and reservation state for each device.

- **Checkpointing**: Not in MVP.

## Failure Modes

- **Compiler failure**: Job transitions to `Failed` with `CompileError`.

- **Driver/backend failure**: Job transitions to `Failed` with `ExecuteError`.

- **QFS unavailable**: Kernel retries; job may stall or fail.

- **Network partition between services**: gRPC timeouts; jobs may be stuck in intermediate states.

## Observability

- **Metrics:**

    - `eigen_kernel_job_state_transitions_total{from,to}`

    - `eigen_kernel_stage_duration_seconds{stage}`

    - `eigen_kernel_queue_depth`

    - `eigen_kernel_active_jobs`

- **Logs**: Include `job_id`, `stage`, `device_id`, `trace_id`.

- **Traces**: Span per pipeline stage; propagated via `traceparent`.

---

**Note**: MVP implements a **linear pipeline** rather than full DAG orchestration. Advanced scheduling (noise-aware, topology-aware, predictive) and checkpointing are planned for Phase 2+.