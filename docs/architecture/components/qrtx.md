# Kernel (QRTX)

- **Phase:** MVP → Phase-1 evolution baseline
- **Status snapshot date:** 2026-05-25
- **Implementation state:** Partially implemented as the active runtime orchestration kernel in `src/rust/crates/eigen-kernel`.

---

# Responsibility

QRTX (Kernel) is the core runtime orchestration layer responsible for deterministic execution lifecycle management across compilation, execution, artifact persistence, and runtime coordination.

The current implementation provides a reduced but functional orchestration pipeline for MVP runtime execution.

The long-term architecture target extends QRTX into a production-grade orchestration runtime with durable state, adaptive scheduling, queue/resource semantics, deterministic replay support, and hardware-aware execution coordination.

---

# Responsibility Scope

## Implemented now

### Runtime orchestration

QRTX currently orchestrates the execution lifecycle:

```text
compile → execute → persist artifacts/results
```

The kernel coordinates with:

- `CompilationService`
- `DriverManagerService`
- QFS (`CircuitFsLocal`)

---

### Job lifecycle management

Current implemented lifecycle states:

```text
Pending
Compiling
Running
Done
Error
Cancelled
Timeout
```

---

### Artifact persistence

Kernel integrates with QFS for:

- compiled artifacts,
- runtime metadata,
- execution results,
- error payload persistence.

---

### Runtime coordination

Kernel manages:

- compilation invocation,
- backend execution invocation,
- terminalization handling,
- structured runtime errors,
- request correlation propagation.

---

### Internal orchestration API

Implemented gRPC service:

```text
KernelGatewayService
```

Methods:

- `EnqueueJob`
- `GetJobStatus`
- `CancelJob`
- `GetJobResults`

---

### Runtime observability

Kernel emits:

- structured tracing spans,
- correlated runtime logs,
- propagated `traceparent` / `trace_id`,
- stage-level runtime diagnostics.

---

## Required target responsibility (architecture baseline)

The production QRTX runtime SHALL provide:

### Full lifecycle orchestration

Expanded lifecycle chain:

```text
Pending
Validating
Compiling
Queued
Allocating
Executing
Completing
Completed
Cancelled
Timeout
Error
```

Including documented sub-states and transition semantics.

---

### Queue and scheduling semantics

The kernel SHALL support:

- queue depth management,
- resource reservation,
- allocation strategies,
- scheduling priority,
- fairness policies,
- deterministic queue replay.

---

### Durable orchestration state

The kernel SHALL support:

- persistent job state,
- restart recovery,
- checkpointing,
- replay-safe recovery,
- resumable orchestration.

---

### Adaptive runtime coordination

The kernel SHALL integrate with:

- future HWE,
- future GNN optimizer,
- future neuro-symbolic runtime,
- future Knowledge Base.

---

### Deterministic replay

The kernel SHALL preserve:

- replay-safe execution lineage,
- deterministic transition logs,
- runtime provenance,
- audit-safe orchestration metadata.

---

### Production orchestration guarantees

The kernel SHALL support:

- timeout enforcement,
- retry policies,
- circuit breakers,
- graceful degradation,
- failure isolation,
- runtime SLO enforcement.

---

## Architecture Position

QRTX is the central runtime orchestration component.

It integrates with:

- `system-api`
- `eigen-compiler`
- `driver-manager`
- `qfs`
- future `hwe`
- future `gnn-optimizer`
- future `knowledge-base`
- future `neuro-symbolic-core`

QRTX acts as the authoritative runtime execution coordinator.

---

## Interfaces

### 1. gRPC Interfaces

#### Implemented now

**KernelGatewayService**

Current implemented methods:

```text
EnqueueJob
GetJobStatus
CancelJob
GetJobResults
```

---

#### Outbound runtime integrations

Kernel uses outbound gRPC clients for:

**CompilationService**

Used for:

- compile requests,
- validation paths.

**DriverManagerService**

Used for:

- device status retrieval,
- execution requests,
- calibration requests.

---

#### Required target gRPC interfaces

**KernelGatewayService extensions**

Future required methods:

```text
ListDevices
StreamJobEvents
SubscribeToJobUpdates
ReplayExecution
QueryExecutionLineage
```

**Scheduler/runtime coordination APIs**

Required future interfaces:

```text
AllocateResources
QueueJob
PauseJob
ResumeJob
AbortExecution
```

**Adaptive-runtime integration APIs**

Required future integrations:

```text
RequestHardwareAdaptation
SubmitOptimizerHints
AttachReplayMetadata
```

**Deterministic replay APIs**

Required future support for:

```text
ExportReplayBundle
VerifyReplayConsistency
```

---

### 2. Runtime Integration Interfaces

#### Implemented now

**QFS integration**

Kernel integrates with:

```text
CircuitFsLocal
```

for:

- artifact persistence,
- result persistence,
- metadata persistence,
- error persistence.

**Compiler integration**

Current integration supports:

- compile invocation,
- validation invocation.

**Driver Manager integration**

Current integration supports:

- device status retrieval,
- execution dispatch,
- backend execution lifecycle.

---

#### Required future integrations

**HWE integration**

Kernel SHALL integrate with future HWE for:

- hardware adaptation,
- runtime rerouting,
- telemetry-aware execution decisions.

**GNN optimizer integration**

Kernel SHALL support:

- routing hints,
- placement recommendations,
- topology-aware optimization metadata.

**Neuro-symbolic integration**

Kernel SHALL support:

- advisory optimization decisions,
- explainability metadata,
- deterministic fallback handling.

**Knowledge Base integration**

Kernel SHALL support:

- reusable execution heuristics,
- replay-aware optimization retrieval,
- runtime feedback ingestion.

---

## Inputs / Outputs

### Inputs

#### Implemented now

**Runtime requests**

Current inputs include:

EnqueueJobRequest

**Fields include:**

- program,
- target backend,
- runtime options,
- metadata.

**Status and control requests**

- `GetJobStatusRequest`
- `CancelJobRequest`
- `GetJobResultsRequest`

**Runtime service responses**

Inputs from:

- compiler responses,
- driver execution responses,
- QFS persistence responses.

---

#### Required target inputs

**Scheduler/runtime metadata**

Future inputs SHALL include:

- queue metadata,
- reservation policies,
- execution priorities,
- tenant/runtime constraints.

**Hardware telemetry**

Future inputs SHALL include:

- topology snapshots,
- noise metrics,
- queue pressure,
- calibration freshness.

**Adaptive-runtime metadata**

Future inputs SHALL include:

- optimizer recommendations,
- neuro-symbolic advisories,
- deterministic replay metadata,
- fallback markers.

---

### Outputs

#### Implemented now

**Runtime responses**

Kernel emits:

- job status,
- terminal result payloads,
- structured error payloads.

**QFS artifacts**

Persisted outputs include:

- compiled AQO,
- compiled QASM,
- execution results,
- counts,
- metadata,
- error artifacts.

**Runtime tracing/logging**

Outputs include:

- stage traces,
- correlated runtime logs,
- request lineage metadata.

---

#### Required target outputs

**Replay artifacts**

Future outputs SHALL include:

- deterministic replay bundles,
- orchestration lineage,
- scheduler replay metadata.

**Adaptive-runtime telemetry**

Future outputs SHALL include:

- optimizer decision traces,
- adaptation history,
- replay-safe fallback metadata.

**Runtime analytics**

Future outputs SHALL include:

- execution timelines,
- queue diagnostics,
- orchestration SLO telemetry.

---

## Storage / State

### Internal State

#### Implemented now

**JobStore**

Current implementation uses:

```text
in-memory JobStore
```

containing:

- job state,
- timestamps,
- counts,
- runtime metadata,
- error payloads.

**Terminalization semantics**

Implemented behavior:

- terminal states reject invalid transitions,
- idempotent re-terminalization is supported for matching events.

---

#### Required target internal state

**Durable orchestration state**

Future runtime SHALL support:

- persistent state backend,
- recovery-safe orchestration state,
- distributed coordination state.

**Scheduler state**

Required future state:

- queue depth,
- reservations,
- allocation state,
- fairness tracking.

**Replay state**

Required future state:

- replay lineage,
- deterministic checkpoints,
- execution provenance indexes.

---

### External Storage

#### Implemented now

**QFS persistence**

Kernel persists runtime artifacts under:

```text
jobs/<job_id>/
```

using canonical QFS layouts.

---

#### Required target storage

**Durable orchestration persistence**

Future runtime SHALL support:

- DB-backed state,
- event-log persistence,
- replay-safe storage.

**Distributed runtime storage**

Future runtime SHALL support:

- clustered coordination state,
- failover-safe orchestration persistence,
- distributed replay lineage.

---

## Failure Modes

### Implemented now

#### Compiler failures

Compiler errors transition jobs to:

```text
Error
```

with structured error payloads.

#### Driver execution failures

Execution/connectivity failures transition jobs to:

```text
Error
```

#### QFS failures

Persistence/layout failures result in:

- runtime error propagation,
- terminal error state.

#### Cancellation support

Non-terminal jobs may be cancelled.

#### Timeout state

`Timeout` exists in current state model.

---

### Required target failure taxonomy

#### Scheduling failures

Future runtime SHALL classify:

- allocation failure,
- queue starvation,
- reservation timeout.

#### Distributed runtime failures

Future runtime SHALL classify:

- network partitions,
- orchestration split-brain,
- replay divergence.

#### Adaptive-runtime failures

Future runtime SHALL classify:

- optimizer timeout,
- adaptation conflict,
- replay inconsistency,
- deterministic safety violation.

#### Persistence failures

Future runtime SHALL classify:

- durable state corruption,
- replay checkpoint mismatch,
- storage exhaustion.

---

### Recovery and fallback requirements

The kernel SHALL support:

- bounded retries,
- backoff policies,
- circuit breakers,
- replay-safe recovery,
- deterministic fallback execution,
- degraded execution modes.

---

## Observability

### Metrics

#### Implemented now

Kernel currently emits:

- runtime traces,
- structured logs,
- stage-oriented spans.

---

#### Required target metrics

**Runtime lifecycle metrics**

```text
eigen_kernel_job_state_transitions_total
eigen_kernel_stage_duration_seconds
eigen_kernel_queue_depth
eigen_kernel_active_jobs
```

**Scheduler metrics**

```text
eigen_kernel_scheduler_latency_seconds
eigen_kernel_resource_allocations_total
eigen_kernel_queue_wait_seconds
```

**Replay metrics**

```text
eigen_kernel_replay_requests_total
eigen_kernel_replay_divergence_total
```

**Adaptive-runtime metrics**

```text
eigen_kernel_adaptive_fallback_total
eigen_kernel_optimizer_hint_usage_total
```

---

### Logs

#### Implemented now

Structured runtime logging exists with:

- trace correlation,
- request lineage metadata,
- stage-oriented diagnostics.

---

#### Required target logging

Future logging SHALL include:

- scheduler decisions,
- allocation diagnostics,
- replay lineage,
- adaptation decisions,
- optimizer advisory traces,
- deterministic fallback events.

---

### Traces

#### Implemented now

Trace propagation exists through:

- runtime pipeline spans,
- `traceparent`,
- `trace_id`.

---

#### Required target tracing

Distributed tracing SHALL cover:

- System API,
- Compiler,
- Kernel,
- Driver Manager,
- HWE,
- optimizer,
- neuro-symbolic runtime,
- QFS persistence.

Required trace metadata:

- job lineage,
- scheduling decisions,
- backend mapping,
- replay identifiers,
- optimizer confidence metadata.

---

## Health Checks

### Implemented now

Runtime health visibility exists through service-level health endpoints.

---

### Required target health model

Kernel SHALL expose:

- orchestration health,
- scheduler health,
- queue saturation state,
- replay consistency validation,
- persistence backend health.

---

## Alignment Summary

### Implemented and aligned

The following runtime capabilities are implemented and aligned with MVP baseline requirements:

- internal orchestration pipeline,
- compiler and driver-manager integration,
- QFS artifact persistence,
- runtime tracing/logging,
- terminal error handling,
- structured runtime lifecycle APIs.

### Remaining architecture gaps

The following architecture targets remain not fully implemented:

- durable orchestration state,
- full RFC lifecycle state machine,
- scheduler/resource allocation subsystem,
- deterministic replay infrastructure,
- distributed orchestration recovery,
- adaptive-runtime integrations,
- replay-safe recovery semantics,
- production-grade queue/resource coordination.

These gaps remain explicitly preserved as required future work to prevent architecture scope loss.
