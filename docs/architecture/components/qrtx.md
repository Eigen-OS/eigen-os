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
- orchestrates the Product 1.0 DAG and all downstream handoff points,
- enforces lifecycle transitions,
- persists artifacts and durable failure evidence to QFS,
- propagates trace/auth correlation context across services,
- consumes Resource Manager inventory/reservation decisions for scheduling,
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
- `resource-manager` (internal allocation and reservation authority)
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

QRTX orchestrates Product 1.0 as a deterministic control-plane flow:

`validate/enqueue → compile → optimize → schedule → execute → persist  record knowledge/observability → finalize`

Stage boundaries are observable, replay-safe, and carry stable stage IDs so cancellation and deadline fan-out can be reconstructed deterministically.
Scheduling and resource decisions are expected to be sourced from the Resource Manager boundary, not from ad hoc kernel-local placeholders.

Implemented the Product 1.0 orchestration DAG control-plane skeleton in Kernel/QRTX with deterministic stage IDs, replay-safe stage records, explicit downstream adapters, and submit-to-results integration coverage.

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

### 8.3 Retry governance (Wave 2)

Retry behavior MUST be bounded, deterministic, and replay-visible.

- Kernel/QRTX MUST govern retries using canonical retryability axonomy from `docs/reference/error-model.md` and `docs/reference/error-mapping.md`.
- Retry policy input MUST include max attempts, backoff bounds, retryable reasons, non-retryable reasons, and deadline interaction.
- Retry attempt records MUST be persisted in kernel state alongside the final retry termination reason.
- Retry traces/metrics MUST remain bounded and MUST include attempt counts, retry outcome, and final retry reason.
- Non-retryable failures MUST not retry.
- Deadline expiration MUST interrupt any further retries and produce canonical timeout behavior.

---

### 8.4 Cancellation fan-out and deadline normalization

Kernel/QRTX MUST normalize deadline and cancellation intent before downstream dispatch and preserve that control decision across all remaining stages.

- Cancellation MUST fan out to queued, compiling, optimizing, scheduled, executing, persisting, and finalizing work.
- Deadline expiry MUST release or mark reservations as released and must not leave the job in an ambiguous in-flight state.
- The first terminal control decision wins; later cancellation/deadline requests are idempotent no-ops.
- Trace and metric labels MUST remain bounded and MUST NOT encode unbounded cancellation reasons or deadline payloads.

---

### 8.5 Async failure visibility (minimum)

When lifecycle is `ERROR`, status/results surfaces MUST include:

| **Field** | **Purpose** |
|---|---|
| `error_code` | stable machine-readable code |
| `error_summary` | human-readable summary |
| `error_details_ref` | durable QFS reference (e.g., `qfs://jobs/<job_id>/results/error.json`) |

Kernel MUST ensure these fields are consistent with `error-model.md`.

---

## 9. Storage / State (Updated for Product 1.0)

### 9.1 MVP (in-memory, reference implementation)

- In-memory `JobStore` containing:
    - job state,
    - timestamps,
    - runtime metadata,
    - error payload pointers.

Terminalization behavior:

- invalid transitions are rejected,
- terminal transitions are idempotent for matching terminalization events.

---

### 9.2 Product 1.0 (durable event-sourced, normative)

Kernel SHALL implement:

**Durable Event Log (required):**
- Immutable append-only event log per job: `qfs://jobs/<job_id>/state/events.jsonl`
- Each event contains:
  - sequence number (monotonic)
  - from_state → to_state (transition)
  - triggering event (e.g., `StartCompiling`)
  - timestamp and trace correlation
  - optional reason/metadata

**Restart Recovery (required):**
- Load all event logs from QFS on startup
- Replay each job's event sequence
- Reconstruct in-memory job state deterministically
- Detect event log corruption (invalid sequences, bad transitions)

**Deterministic Replay Function (required):**
- Provided: `JobEventLog::replay_to_current_state()`
- Validates all transitions are legal
- Detects sequence gaps, state inconsistencies, determinism violations
- Returns final state or structured error

**Audit Trail (required):**
- All state transitions recorded immutably
- Timestamps enable causality ordering
- Trace IDs enable correlation with distributed traces
- No transition can be "undone" or "rewritten"

**Implementation artifacts:**
- `qrtx::event_log` — event types and replay logic
- `eigen-kernel::durable_job_store` — QFS persistence layer
- Tests in `src/rust/crates/{qrtx,eigen-kernel}/tests/`

---

### 9.3 Future phases (Phase-2+)

Kernel MAY add:

- Database backend (PostgreSQL/SQLite) for event log durability
- Event stream subscriptions (for live job updates)
- Archive/cleanup policies (old events)
- Multi-region replication (distributed event log)
- Scheduler coordination state (resource allocation, fairness)

These do not change the current event log abstraction; they are alternative storage backends.

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

---

## Appendix A. Diagrams (normative)

### A.1 C4 Context — Kernel as orchestration core

![C4 Context](https://i.imgur.com/yNElbh8.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Clients["Clients"]
    SDK[SDK/CLI]
  end

  subgraph Public["Public Edge"]
    API[System API]
  end

  subgraph Runtime["Runtime Core"]
    K[Kernel / QRTX]
    C[Compiler Service]
    DM[Driver Manager]
    QFS[(QFS)]
  end

  SDK --> API --> K
  K --> C
  K --> DM
  K --> QFS
  C --> QFS
  DM --> QFS
```

</details>

---

### A.2 C4 Container — Internal API boundary

![Internal API boundary](https://i.imgur.com/BT7C0Wi.png)

<details>
<summary>code</summary>

```text
flowchart TB
    API["System API\n(public)"] -->|internal gRPC| KG["KernelGatewayService\n(eigen.internal.v1)"]
    KG --> Orchestrator["Orchestrator Core\n(state machine + deadlines)"]
    Orchestrator --> JobStore[(JobStore\nin-memory MVP)]
    Orchestrator -->|gRPC| C[CompilationService]
    Orchestrator -->|gRPC| DM[DriverManagerService]
    Orchestrator -->|store/load| QFS[(QFS)]

    classDef service fill:#e3f2fd,stroke:#1976d2
    classDef store fill:#f0f4c3,stroke:#689f38
    class API,KG,Orchestrator,C,DM service
    class JobStore,QFS store
```

</details>

---

### A.3 State machine — internal states (incl. optional substates)

![internal states](https://i.imgur.com/l6IygS1.png)

<details>
<summary>code</summary>

```text
stateDiagram-v2
  [*] --> PENDING
  PENDING --> COMPILING: start_compile
  PENDING --> CANCELLED: cancel

  COMPILING --> QUEUED: compile_ok
  COMPILING --> ERROR: compile_fail
  COMPILING --> CANCELLED: cancel

  QUEUED --> RUNNING: dispatch
  QUEUED --> CANCELLED: cancel
  QUEUED --> ERROR: dispatch_fail

  RUNNING --> DONE: exec_ok + persist_ok
  RUNNING --> ERROR: exec_fail OR persist_fail
  RUNNING --> CANCELLED: cancel_best_effort
  RUNNING --> TIMEOUT_INTERNAL: deadline_exceeded

  TIMEOUT_INTERNAL --> ERROR: map_to_public_error

  DONE --> [*]
  ERROR --> [*]
  CANCELLED --> [*]

  note right of TIMEOUT_INTERNAL
    Internal-only terminal reason.
    MUST map to public ERROR with DEADLINE_EXCEEDED semantics.
  end note
```

</details>

---

### A.4 Mapping — internal → public lifecycle (visual)

![Mapping — internal → public lifecycle](https://i.imgur.com/l6IygS1.png)

<details>
<summary>code</summary>

```text
flowchart TB
  subgraph Internal["Kernel internal (may include substates)"]
    P[PENDING]
    V[VALIDATING]
    C[COMPILING]
    Q[QUEUED]
    A[ALLOCATING]
    R[RUNNING]
    E1[EXECUTING]
    C2[COMPLETING]
    D[DONE]
    X[ERROR]
    Z[CANCELLED]
    T[TIMEOUT_INTERNAL]
  end

  subgraph Public["Public lifecycle (stable)"]
    pP[PENDING]
    pC[COMPILING]
    pQ[QUEUED]
    pR[RUNNING]
    pD[DONE]
    pX[ERROR]
    pZ[CANCELLED]
  end

  P --> pP
  V --> pP
  C --> pC
  Q --> pQ
  A --> pQ
  R --> pR
  E1 --> pR
  C2 --> pR
  D --> pD
  X --> pX
  Z --> pZ
  T --> pX
```

</details>

---

### A.5 Sequence — EnqueueJob (persist inputs, accept job_id)

![EnqueueJob](https://i.imgur.com/HPGUO39.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant API as System API
  participant K as KernelGatewayService
  participant Q as QFS
  participant S as JobStore

  API->>K: EnqueueJob(JobSpec + source_ref/bytes)\n(traceparent, auth ctx)
  K->>S: create job record (PENDING)
  K->>Q: atomic_write input/job.yaml
  K->>Q: atomic_write source/<program> (or bundle)
  K-->>API: EnqueueJobResponse(job_id, state=PENDING)
```

</details>

---

### A.6 Sequence — Orchestrate compile→execute→persist

![Orchestrate compile→execute→persist](https://i.imgur.com/mTPpfxb.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant K as QRTX Orchestrator
  participant C as CompilationService
  participant DM as DriverManagerService
  participant Q as QFS

  K->>K: transition PENDING→COMPILING
  K->>C: CompileJob(job_id, source_ref/bytes)
  alt compile ok
    C->>Q: atomic_write compiled/compiled.aqo.json
    C->>Q: atomic_write compiled/metadata.json
    C-->>K: compiled_aqo_ref + aqo_digest
    K->>K: transition COMPILING→QUEUED
    K->>K: transition QUEUED→RUNNING
    K->>DM: ExecuteCircuit(job_id, device_id, aqo_ref)
    alt exec ok
      DM-->>K: ExecutionResult
      K->>Q: atomic_write results/results.json
      K->>Q: atomic_write timeline/timeline.json (recommended)
      K->>K: transition RUNNING→DONE
    else exec fail
      DM-->>K: gRPC error + reason
      K->>Q: atomic_write results/error.json
      K->>Q: atomic_write timeline/timeline.json (recommended)
      K->>K: transition RUNNING→ERROR
    end
  else compile fail
    C-->>K: gRPC error + reason
    K->>Q: atomic_write results/error.json
    K->>Q: atomic_write timeline/timeline.json (recommended)
    K->>K: transition COMPILING→ERROR
  end
```

</details>

---

### A.7 Sequence — GetJobResults (precondition vs terminal)

![GetJobResults](https://i.imgur.com/Vl6oJGx.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant API as System API
  participant K as KernelGatewayService
  participant Q as QFS

  API->>K: GetJobResults(job_id)
  alt job state is DONE
    K->>Q: load results/results.json
    Q-->>K: results bytes
    K-->>API: GetJobResultsResponse(results + refs)
  else job state is ERROR
    K->>Q: load results/error.json
    Q-->>K: error artifact
    K-->>API: GetJobResultsResponse(error_code, summary, error_details_ref)
  else non-terminal
    K-->>API: FAILED_PRECONDITION (results not ready)
  end
```

</details>

---

### A.8 Idempotent terminalization rule (race-safe)

![Idempotent terminalization rule](https://i.imgur.com/7szSTNc.png)

<details>
<summary>code</summary>

```text
flowchart TB
    Evt["Terminalization event arrives\n(exec_ok / exec_fail / cancel / timeout)"] --> Read["Read current state"]
    Read --> T{"Is job already terminal?"}
    T -- yes --> Same{"Does event match existing terminal outcome?"}
    Same -- yes --> Noop["No-op (idempotent)\nreturn existing terminal state"]
    Same -- no --> Reject["Reject/ignore conflicting terminalization\nlog + reason code"]
    T -- no --> Apply["Apply terminal transition\npersist required artifacts"]
    Apply --> Freeze["Freeze terminal state\n(DONE/ERROR/CANCELLED)"]

    classDef terminal fill:#e8f5e9,stroke:#2e7d32
    classDef decision fill:#fff3e0,stroke:#f57c00
    class Noop,Freeze terminal
    class T,Same decision
```

</details>

---

### A.9 Sequence — CancelJob (best-effort for RUNNING)

![CancelJob](https://i.imgur.com/rAcDd2r.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant API as System API
  participant K as KernelGatewayService
  participant DM as DriverManagerService
  participant Q as QFS

  API->>K: CancelJob(job_id)
  alt state is PENDING/COMPILING/QUEUED
    K->>K: transition -> CANCELLED (idempotent)
    K->>Q: atomic_write timeline/timeline.json (recommended)
    K-->>API: CancelJobResponse(state=CANCELLED)
  else state is RUNNING
    K->>DM: AbortExecution(job_id, device_id) (if supported)
    Note over DM: If not supported,\nDM may return UNIMPLEMENTED
    K->>K: transition -> CANCELLED (best-effort)
    K->>Q: atomic_write timeline/timeline.json (recommended)
    K-->>API: CancelJobResponse(state=CANCELLED)
  else terminal already
    K-->>API: CancelJobResponse(state=<terminal>) (idempotent)
  end
```

</details>

---

### A.10 Timeout mapping — TIMEOUT_INTERNAL → public ERROR

![Timeout mapping](https://i.imgur.com/ph8mmQe.png)

<details>
<summary>code</summary>

```text
flowchart LR
    Deadline[deadline exceeded] --> T["TIMEOUT_INTERNAL\n(internal reason)"]
    T --> Persist["Persist results/error.json\n+ timeline marker"]
    Persist --> Pub["Public state = ERROR\nAsync error includes EIGEN_TIMEOUT\nSynchronous: DEADLINE_EXCEEDED"]
```

</details>

---

### A.11 Required artifacts by phase (overview)

![Required artifacts by phase](https://i.imgur.com/fIL4MSt.png)

<details>
<summary>code</summary>

```text
flowchart TB
    subgraph Enqueue["On EnqueueJob"]
        A1["input/job.yaml"]
        A2["source/..."]
    end

    subgraph Compile["On compile success"]
        B1["compiled/compiled.aqo.json"]
        B2["compiled/compiled.qasm (optional)"]
        B3["compiled/diagnostics.json (optional)"]
    end

    subgraph Terminal["On terminalization"]
        C1["results/results.json (DONE)"]
        C2["results/error.json (ERROR) — required for async visibility"]
        C3["timeline/timeline.json (recommended)"]
    end

    Enqueue --> Compile --> Terminal

    classDef phase fill:#e3f2fd,stroke:#1976d2,color:#000
    class Enqueue,Compile,Terminal phase
```

</details>

---

### A.12 Trace propagation across orchestration path

![Trace propagation across orchestration path](https://i.imgur.com/BcPSxNg.png)


<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant SDK as SDK/CLI
  participant API as System API
  participant K as Kernel/QRTX
  participant C as Compiler
  participant DM as Driver Manager
  participant Q as QFS

  SDK->>API: SubmitJob (traceparent)
  API->>K: EnqueueJob (same traceparent)
  K->>C: CompileJob (child span)
  C->>Q: store compiled/* (child span)
  K->>DM: ExecuteCircuit (child span)
  K->>Q: store results/* (child span)
  Note over K: Logs include trace_id + job_id\nMetrics exclude job_id/trace_id labels
```

</details>

---

### A.13 Health model (target) — dependencies & readiness

![Health model](https://i.imgur.com/CobiZh5.png)

<details>
<summary>code</summary>

```text
flowchart TB
    Live["/live"] --> Proc["process alive"]
    Ready["/ready"] --> Dep{"deps reachable?"}
    
    Dep --> C["Compiler reachable"]
    Dep --> DM["Driver Manager reachable"]
    Dep --> Q["QFS reachable"]
    Dep --> OK["ready = true"]
    Dep --> NotOK["ready = false"]

    classDef healthCheck fill:#e8f5e9,stroke:#2e7d32
    class Live,Ready,OK healthCheck
```

</details>

---

### A.14 Future scheduling loop (QueueJob / AllocateResources)

![Future scheduling loop](https://i.imgur.com/DSm8Be7.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant K as Kernel/QRTX
  participant RM as Resource Manager (future)
  participant HWE as HWE (future)
  participant DM as Driver Manager

  K->>K: QUEUED
  K->>RM: AllocateResources(job_id, constraints)
  RM-->>K: allocation (device_id/slot) or deny
  alt allocated
    K->>HWE: PlanExecution(job_id, device_snapshot)
    HWE-->>K: plan (may include optimizer refs)
    K->>DM: ExecuteCircuit(job_id, device_id, payload/ref)
  else denied
    K->>K: remain QUEUED or ERROR (policy)
  end
```

</details>
