# Kernel (QRTX)

- **Document status:** Normative architecture + runtime orchestration contract (MVP → Phase-1 baseline)
- **Snapshot date:** 2026-05-25
- **Contract version:** 1.0.0
- **Implementation state:** Partially implemented as the active runtime orchestration kernel in src/rust/crates/eigen-kernel

QRTX (Kernel) is the core runtime orchestration layer responsible for deterministic execution lifecycle management across compilation, execution, artifact persistence, and runtime coordination.

This document is **normative** for:

- kernel lifecycle semantics exposed via internal APIs,
- mapping between kernel state and **public** lifecycle states,
- kernel persistence obligations to QFS,
- kernel failure/timeout semantics and async failure visibility,
- kernel observability requirements and conformance expectations.

---

## 1. Contract Versioning

### 1.1 Contract marker

Kernel implementations SHOULD export a marker metric:

```text
eigen_kernel_contract_info{version="1.0.0"} 1
```

---

### 1.2 SemVer policy

#### MAJOR

- changes to public lifecycle mapping,
- changes to terminalization semantics,
- changes to QFS required artifacts produced by kernel,
- incompatible change to internal orchestration API semantics.

#### MINOR

- additive internal substates,
- additive kernel metrics,
- additive QFS artifacts,
- additive orchestration metadata (bounded).

#### PATCH

- implementation fixes and documentation corrections without semantic change.

---

## 2. Responsibility

QRTX is the authoritative coordinator for a job’s runtime lifecycle. It:

- validates/normalizes internal execution requests (after System API validation),
- orchestrates compilation and execution calls,
- enforces lifecycle transitions,
- persists artifacts and durable failure evidence to QFS,
- propagates trace/auth correlation context across services,
- surfaces status/results consistently through internal APIs (and therefore public APIs).

QRTX MUST NOT:

- expose internal substates as new public lifecycle states,
- bypass deterministic compiler safety policies,
- bypass Driver Manager backend normalization,
- encode transport failures in response bodies (must use gRPC status + details),
- invent results without QFS-backed persistence for terminal outcomes.

---

## 3. Architecture Position

QRTX is the central orchestration component.

It integrates with:

- `system-api` (public gateway; forwards to kernel)
- `eigen-compiler` (CompilationService)
- `driver-manager` (DriverManagerService)
- `qfs` (CircuitFS / QFSStore facade)
- future: `hwe`, `gnn-optimizer`, `knowledge-base`, `neuro-symbolic-core`

Canonical runtime pipeline:

```text
System API
  ↓
QRTX (Kernel)
  ├──► CompilationService
  ├──► DriverManagerService
  └──► QFS
```

---

## 4. Lifecycle Contract

### 4.1 Canonical public lifecycle (MUST remain stable)

Client-visible lifecycle states are:

```text
PENDING → COMPILING → QUEUED → RUNNING → DONE | ERROR | CANCELLED
```

---

### 4.2 Kernel internal states (allowed)

Kernel MAY use internal substates for orchestration, but MUST map them deterministically to the public lifecycle.

#### Allowed internal state set (recommended baseline):

```text
PENDING
COMPILING
QUEUED
RUNNING
DONE
ERROR
CANCELLED
```

#### Optional internal substates (internal-only, additive):

- `VALIDATING`
- `ALLOCATING`
- `EXECUTING` (substate of RUNNING)
- `COMPLETING` (substate of RUNNING)
- `TIMEOUT_INTERNAL` (internal terminal reason, not a public lifecycle state)

---

### 4.3 Mapping rules (normative)

| **Kernel internal** | **Public lifecycle** | **Notes** |
|---|---|---|
| `PENDING` | `PENDING` | accepted, not yet compiling |
| `VALIDATING` | `PENDING` | internal-only; never exposed |
| `COMPILING` | `COMPILING` | compilation in progress |
| `QUEUED` | `QUEUED` | awaiting execution scheduling/dispatch |
| `ALLOCATING` | `QUEUED` | internal-only; never exposed |
| `RUNNING` / `EXECUTING` / `COMPLETING` | `RUNNING` | execution active |
| `DONE` | `DONE` | terminal success |
| `CANCELLED` | `CANCELLED` | terminal cancellation |
| `ERROR` | `ERROR` | terminal failure |
| `TIMEOUT_INTERNAL` | `ERROR` | MUST surface as `ERROR` with `DEADLINE_EXCEEDED` semantics |

---

### 4.4 Terminalization invariants (MUST)

1. Terminal states are immutable:
    - `DONE`, `ERROR`, `CANCELLED` MUST NOT transition to any other state.
2. Terminalization MUST be idempotent:
    - repeated terminalization requests/events MUST produce the same terminal outcome.
3. Public lifecycle MUST be monotonic:
    - no backwards public transitions (e.g., `RUNNING → QUEUED`) are allowed.
4. Timeouts are failures:
    - any timeout MUST become `ERROR` (public) with canonical timeout semantics (see `§8`).

---

## 5. Implemented Baseline (Current Repository)

### 5.1 Runtime orchestration (implemented)

QRTX orchestrates: `compile → execute → persist artifacts/results`

Coordinates with:

- `CompilationService`
- `DriverManagerService`
- QFS (`CircuitFsLocal` / QFS facade)

---

### 5.2 Job lifecycle (implemented but MUST align to public mapping)

Repository snapshot indicates internal states include:

```text
Pending, Compiling, Running, Done, Error, Cancelled, Timeout
```

Contract correction (normative):

- `Timeout` MUST NOT be exposed as a public lifecycle state.
- Internally, represent timeout as `TIMEOUT_INTERNAL` (reason) and map to public `ERROR` with `DEADLINE_EXCEEDED`.

---

### 5.3 Internal orchestration API (implemented)

Implemented gRPC service: `KernelGatewayService`

Methods (implemented):

- `EnqueueJob`
- `GetJobStatus`
- `CancelJob`
- `GetJobResults`

---

## 6. Interfaces

### 6.1 Inbound gRPC: KernelGatewayService (normative behavior)

#### EnqueueJob

- creates job record and stable `job_id`
- persists required submission artifacts to QFS
- returns accepted response with `job_id`
- MUST propagate trace context

#### GetJobStatus

returns public lifecycle state + timestamps + optional progress fields
MUST NOT expose internal-only substates as new public states

#### CancelJob

- allowed for non-terminal jobs
- best-effort for RUNNING
- MUST be idempotent

#### GetJobResults

- for `DONE`: returns results + QFS refs
- for `ERROR`: returns async failure visibility fields + QFS error ref
- for non-terminal: MUST use `FAILED_PRECONDITION` (results not ready)

---

### 6.2 Outbound gRPC integrations (implemented)

#### CompilationService

- compile invocation
- validation paths (where present)

#### DriverManagerService

- device status retrieval
- execution dispatch
- calibration request (may be UNIMPLEMENTED)

---

### 6.3 Required future kernel API extensions (target)

KernelGatewayService MAY add (MINOR):

- `StreamJobEvents` / `SubscribeToJobUpdates` (true streaming)
- `QueryExecutionLineage`
- `ExportReplayBundle` / `VerifyReplayConsistency`

Scheduler/runtime coordination APIs (Phase-1+):

- `QueueJob`
- `AllocateResources`
- `PauseJob` / `ResumeJob`
- `AbortExecution`

Adaptive-runtime integration APIs (Phase-1+):

- `RequestHardwareAdaptation`
- `SubmitOptimizerHints`
- `AttachReplayMetadata`

---

## 7. QFS Persistence Contract (Kernel Obligations)

QRTX is responsible for ensuring that terminal outcomes are **durably inspectable** via QFS.

### 7.1 Canonical job namespace

Kernel MUST persist under: `qfs://jobs/<job_id>/`

---

### 7.2 Required artifacts (minimum)

On enqueue:

- `qfs://jobs/<job_id>/input/job.yaml` (or canonical JobSpec payload)
- `qfs://jobs/<job_id>/source/...` (source bundle or resolved program content)

On successful compile:

- `qfs://jobs/<job_id>/compiled/compiled.aqo.json`
- `qfs://jobs/<job_id>/compiled/compiled.qasm` (optional)

On success:

- `qfs://jobs/<job_id>/results/results.json`

On failure:

- `qfs://jobs/<job_id>/results/error.json` (**SHOULD**; treated as required for async failure visibility)

Recommended:

- `qfs://jobs/<job_id>/timeline/timeline.json`
- `qfs://jobs/<job_id>/logs/run.log` (deployment dependent)

---

## 8. Failure and Timeout Semantics

### 8.1 Canonical error model

Kernel MUST follow the system error model:

- gRPC-status-first
- structured-details-first
- deterministic mapping

Kernel MUST NOT encode “success=false” transport wrappers in payloads.

---

### 8.2 Timeout semantics (normative)

If execution or orchestration exceeds the configured deadline:

- public lifecycle MUST become `ERROR`
- gRPC status MUST be `DEADLINE_EXCEEDED` for synchronous surfaces
- async error artifact MUST include a stable error code (e.g., `EIGEN_TIMEOUT`) and reference

---

### 8.3 Async failure visibility (minimum)

When lifecycle is `ERROR`, status/results surfaces MUST include:

| **Field** | **Purpose** |
|---|---|
| `error_code` | stable machine-readable code |
| `error_summary` | human-readable summary |
| `error_details_ref` | durable QFS reference (e.g., `qfs://jobs/<job_id>/results/error.json`) |

Kernel MUST ensure these fields are consistent with `error-model.md`.

---

## 9. Storage / State

### 9.1 Implemented now

- In-memory `JobStore` containing:
    - job state,
    - timestamps,
    - runtime metadata,
    - error payload pointers.

Terminalization behavior:

- invalid transitions are rejected,
- terminal transitions are idempotent for matching terminalization events.

---

### 9.2 Required target state (Phase-1+)

Kernel SHALL add:

- durable state backend (DB/event log),
- restart recovery,
- replay-safe orchestration recovery,
- scheduler coordination state (queue depth, reservations, fairness),
- replay lineage indexes and checkpoints.

---

## 10. Observability

Kernel observability MUST align with:

- orchestration observability contract (`orchestration-observability-contract.md`) for control-plane scheduling metrics where applicable,
- global observability expectations (`observability.md`),
- intelligent runtime observability where decisioning is involved (`intelligent-runtime-observability-contract.md`) once integrated.

---

### 10.1 Implemented now

- structured logs with correlation
- trace propagation (`traceparent`, `trace_id`)
- stage-oriented spans (where instrumented)

---

### 10.2 Required target metrics (normative names)

Kernel SHOULD export:

#### Lifecycle

```text
eigen_kernel_job_state_transitions_total{from,to}
eigen_kernel_active_jobs{state}
eigen_kernel_stage_duration_seconds_bucket{stage}
eigen_kernel_stage_duration_seconds_sum{stage}
eigen_kernel_stage_duration_seconds_count{stage}
```

#### Queue / scheduling (when implemented)

```text
eigen_kernel_queue_depth{queue}
eigen_kernel_queue_wait_seconds_bucket{queue}
eigen_kernel_scheduler_latency_seconds_bucket
```

#### Replay (when implemented)

```text
eigen_kernel_replay_requests_total{mode}
eigen_kernel_replay_divergence_total{reason}
```

Label rules:

- MUST be bounded/enumerable.
- MUST NOT include `job_id`, `trace_id`, tenant/user identifiers.

---

### 10.3 Logging requirements (target)

Logs SHOULD include:

- `trace_id`, `job_id`, `stage`, `state`
- terminal outcomes with stable error codes
- QFS refs for results/error artifacts (as log fields, not metric labels)

---

### 10.4 Tracing requirements (target)

Distributed tracing SHOULD cover:

- System API → Kernel → Compiler → Driver Manager → QFS

Spans SHOULD include:

- stage timing,
- backend selection (when applicable),
- persistence actions,
- deterministic fallback events (future).

---

## 11. Health

### 11.1 Implemented now

Service-level health endpoints exist (deployment dependent).

---

### 11.2 Required target health model

Kernel SHOULD expose:

- orchestration health,
- dependency health (compiler/driver/qfs reachability),
- queue saturation (when applicable),
- persistence backend health,
- replay consistency checks (when applicable).

---

## 12. Conformance Requirements

An implementation is conformant if it:

1. Preserves the stable public lifecycle mapping:
    - no public `TIMEOUT` state; timeouts map to public `ERROR`.
2. Enforces terminal immutability and idempotent terminalization.
3. Persists required QFS artifacts for:
    - submission inputs,
    - compile outputs,
    - results or durable error artifacts.
4. Uses canonical gRPC status semantics and structured error details.
5. Provides async failure visibility fields for terminal `ERROR`.
6. Preserves trace propagation across kernel-managed calls.
7. Exports bounded-cardinality metrics (no correlation IDs as labels).

Minimum required tests:

- invalid transition rejection,
- terminal idempotency,
- results-before-ready → `FAILED_PRECONDITION`,
- timeout → public `ERROR` + `DEADLINE_EXCEEDED` semantics + `results/error.json`,
- QFS missing artifact handling → `NOT_FOUND`,
- trace propagation smoke test.

---

## 13. Alignment Summary

#### Implemented and aligned (MVP baseline)

- orchestration pipeline (compile → execute → persist),
- compiler and driver-manager integration,
- QFS artifact persistence baseline,
- runtime tracing/logging foundations,
- terminal error handling,
- internal lifecycle/status/results APIs.

#### Remaining architecture gaps (explicit)

- durable orchestration state,
- full queue/scheduler/resource allocation subsystem,
- deterministic replay infrastructure,
- distributed orchestration recovery,
- adaptive runtime integrations (HWE/NSC/GNN/KB),
- production-grade retries/circuit breakers and degraded modes.

These gaps are intentionally preserved as required Phase-1+ work and MUST NOT be erased by documentation drift.
