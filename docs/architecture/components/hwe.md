# Hardware Workflow Engine (HWE)

**Contract status:** Stable target architecture contract with documented implemented baseline (Eigen OS 1.0 / MVP + approved extensions)
**Subsystem:** Hardware-aware execution orchestration and adaptation
Contract version: 1.0.0
**Applies to:** Kernel/QRTX, Runtime Controller/Scheduler, Driver Manager, (future) OptimizerService (GNN), QFS lineage layer, Observability exporters
**Last synchronized:** 2026-05-25

## 1. Purpose

The **Hardware Workflow Engine (HWE)** is the hardware-aware orchestration subsystem of Eigen OS responsible for transforming **abstract execution intent** into **reliable, policy-conformant execution behavior** across heterogeneous quantum backends.

HWE is the control layer positioned between:

- the deterministic orchestration pipeline of `eigen-kernel` (QRTX),
- the provider abstraction layer of `driver-manager`,
- future live-resource semantics (QFS Level-1),
- and adaptive optimization systems including the Neuro-DPDA compiler path and the GNN hardware optimizer.

HWE exists to ensure that:

1. quantum workloads execute on the most suitable hardware under policy constraints,
2. runtime adaptation decisions remain **deterministic and auditable** when determinism is requested,
3. hardware telemetry is normalized and actionable,
4. backend instability is isolated from user-facing semantics,
5. adaptive execution remains reproducible (replay-safe) under declared policy.

---

## 2. Architectural Position

### 2.1 Layer Placement

HWE belongs to the **Runtime Services** layer of Eigen OS and acts as the **hardware-execution orchestration boundary**.

Logical placement:

```text
Client SDKs
  ↓
System API
  ↓
Eigen Kernel (QRTX)
  ↓
HWE (logical subsystem; may be embedded initially)
  ↓
Driver Manager
  ↓
Quantum Providers / Simulators
```

---

### 2.2 Responsibility Separation

| **Component** | **Responsibility** |
|---|---|
| Eigen Compiler | Deterministic compilation into AQO |
| Neuro-DPDA Compiler Path | Semantic optimization and compilation heuristics (advisory) |
| GNN Optimizer | Hardware-aware placement/routing optimization (advisory, validated) |
| HWE | Runtime execution planning, adaptation, telemetry normalization, replay/audit |
| Driver Manager | Provider adapter lifecycle and normalized backend access |
| Drivers | Vendor-specific execution transport |

HWE MUST NOT:

- compile or execute user source programs,
- manage vendor SDK internals directly,
- replace kernel ownership of job lifecycle state,
- violate deterministic replay guarantees or safety policies.

---

## 3. Current Implemented Baseline (Repository Truth)

### 3.1 Implemented Runtime Boundary

There is **no standalone** `hwe` **service/crate** in the current repository. HWE behavior is currently split across kernel and driver-manager, but the following baseline is implemented:

- `eigen-kernel → driver-manager` gRPC execution flow
- driver capability handshake
- device discovery and health queries
- simulator-first backend execution
- structured execution error normalization
- observability propagation (`trace_id`, `job_id`)
- basic backend abstraction via `QDriver` / `BaseDriver`

Current execution ownership:

```text
Kernel
  └── DriverManagerService
        └── Driver
              └── Provider SDK
```

---

### 3.2 Existing Hardware-Aware Behavior (Fragmented)

Implemented today (not yet centralized as a single subsystem):

- runtime execution selection (kernel/driver-manager level)
- capability negotiation (driver handshake)
- backend status inspection (`ListDevices`, `GetDeviceStatus`, healthcheck flows)
- optimization groundwork (plugin contracts, metadata propagation, limited hybrid loops)

---

## 4. Target Responsibilities (Normative)

### 4.1 Hardware Telemetry Ingestion and Normalization

HWE MUST ingest and normalize bounded telemetry signals such as:

- calibration freshness and validity windows
- topology and coupling maps
- queue depth / scheduling pressure
- provider availability / maintenance state
- latency signals (bounded aggregates)
- noise models / fidelity summaries (bounded)
- quota and capacity signals (bounded)

Telemetry MUST be:

- versioned,
- timestamped,
- associated with a backend snapshot identifier,
- treated as **untrusted input** (validated/sanitized).

---

### 4.2 Runtime Execution Planning and Adaptation

HWE MUST support runtime decisions including:

- reroute to alternative backend
- retry under retry budget
- defer (delay scheduling) under policy
- abort when policy forbids execution
- backend substitution (when allowed)
- degraded-mode operation (reduced intelligence, deterministic fallback)

All adaptation decisions MUST:

- preserve semantic correctness,
- preserve determinism policy when requested,
- emit explainability metadata,
- emit audit records durable via QFS artifacts.

---

### 4.3 Live Qubit Lifecycle (QFS Level-1, Post-MVP)

HWE MAY eventually own:

- live qubit allocation and reservation lifecycle
- feed-forward coordination
- real-time execution sessions
- control-channel coordination

This capability is **NOT part of MVP baseline** and MUST NOT be assumed available unless explicitly enabled by a versioned contract.

---

### 4.4 Integration with GNN Optimizer (Advisory + Validated)

HWE MUST integrate with the future GNN optimizer contract (see `gnn-optimizer.md`), where the optimizer is responsible for:

- placement (logical→physical mapping)
- routing optimization (SWAP strategy)
- topology-aware transformations
- noise-aware execution scoring

HWE MUST:

- provide runtime telemetry and constraints to the optimizer,
- validate optimizer outputs against policy and symbolic safety,
- enforce deterministic fallback behavior,
- reject unsafe or unverifiable optimizer decisions.

---

### 4.5 Integration with Neuro-DPDA Compiler Path

HWE MUST be able to consume compiler-produced metadata such as:

- placement hints (optional)
- execution affinity constraints
- routing constraints / forbidden edges (optional)
- latency vs fidelity priorities
- determinism policy markers

HWE MUST NOT mutate AQO semantics beyond explicitly allowed runtime adaptation policies and validated transformations.

---

## 5. Determinism and Replay Contract

### 5.1 Determinism Modes

HWE MUST support a determinism policy:

- `deterministic = true`: planning/adaptation decisions MUST be replay-stable
- `deterministic = false`: decisions MAY be adaptive, but MUST remain policy-safe and auditable

---

### 5.2 Deterministic Input Set

When `deterministic=true`, HWE decisions MUST be a pure function of:

- canonical AQO digest (content hash)
- backend snapshot digest (topology + capability snapshot hash)
- telemetry snapshot digest (calibration/noise summaries, bounded)
- policy envelope (mode, constraints, retry budgets)
- contract version identifiers of HWE/optimizer involved
- explicit deterministic `seed` (REQUIRED for deterministic=true)

---

### Reproducibility Digest

HWE MUST output:

- `hwe_decision_digest = sha256(canonical_inputs + canonical_outputs)`

This digest MUST be persisted in job-scoped QFS artifacts and surfaced to operator-level explainability (L2/L3).

---

## 6. Interfaces

### 6.1 Current Implemented Interfaces

#### DriverManagerService (Internal)

Implemented internal gRPC methods:

- `ListDevices`
- `GetDeviceStatus`
- `ExecuteCircuit`
- `CalibrateDevice` (defined; currently returns `UNIMPLEMENTED`)

#### Driver Contract

Implemented driver methods:

- `initialize(config)`
- `capability_handshake()`
- `healthcheck()`
- `get_devices()`
- `get_device_status(device_id)`
- `execute_circuit(device_id, circuit, shots, options)`
- `calibrate_device(device_id, options)`

---

### 6.2 Target HWE Interface (Internal Contract)

HWE SHOULD be introduced as an internal control-plane API (whether as a standalone service or embedded module behind an internal RPC boundary).

#### Proposed service

```text
eigen.internal.v1.HWEControlService
```

#### Required APIs (target)

**Hardware Snapshot API**

- `GetHardwareSnapshot`
- `StreamHardwareTelemetry`

**Execution Decision API**

- `PlanExecution`
- `AdaptExecution`
- `ReplayExecutionDecision`

**Live Resources API (post-MVP)**

- `AllocateLiveResources`
- `ReleaseLiveResources`
- `PushFeedForwardSignal`

---

## 7. Input and Output Contracts

### 7.1 Inputs

Implemented now:

- AQO payloads (via kernel→driver-manager path)
- `device_id`
- runtime options
- backend capability metadata
- driver health snapshots

**Future: HardwareExecutionContext (Normative Object)**

HWE SHOULD standardize a canonical context object:

```text
HardwareExecutionContext:
  - job_id
  - aqo_digest
  - backend_constraints
  - backend_snapshot_ref (topology+capabilities)
  - telemetry_snapshot_ref (calibration/noise, bounded)
  - scheduling_priority
  - determinism_mode
  - seed (required if determinism_mode=true)
  - tenant_policy_ref (optional)
  - compiler_hints (optional, bounded)
  - optimizer_hints (optional, bounded)
```

---

### 7.2 Outputs

#### Implemented Now

- execution counts
- execution metadata
- normalized errors
- backend status

#### Future Outputs (Normative)

**ExecutionDecision**

```text
- selected_backend
- placement_plan_ref (optional)
- routing_plan_ref (optional)
- adaptation_actions (bounded list)
- optimizer_source (none | heuristic | gnn)
- confidence_score (optional, bounded)
- hwe_decision_digest (required)
- explanation_ref (optional)
```

**ExecutionOutcome**

```text
- execution_result_ref
- adaptation_history_ref
- fallback_events_ref
- telemetry_snapshot_ref
- replay_reference_ref
```

---

## 8. QFS Integration (Job-Scoped Persistence)

HWE artifacts MUST be persisted under the job’s QFS namespace to remain consistent with `qfs-layout.md` v1.0.

### 8.1 Canonical Job-Scoped Layout

```text
qfs://jobs/<job_id>/
  input/
  compiled/
  results/
  logs/
  meta/
  hwe/                      # HWE artifacts (this section)
```

---

### 8.2 Proposed HWE Artifact Set

```text
qfs://jobs/<job_id>/hwe/
  hardware_snapshot.json            # bounded normalized snapshot
  telemetry_snapshot.json           # bounded normalized telemetry
  execution_plan.json               # selected backend + plan summary
  adaptation_history.json           # bounded actions + reasons
  replay_bundle.json                # deterministic inputs/outputs + digests
  explain.json                      # optional explain payload (bounded)
```

---

### 8.3 Persistence Rules

| **Data type** | **Persistence** |
|---|---|
| Live telemetry | TTL cache (runtime) + bounded snapshot persisted on decision |
| Adaptation history | Durable (job-scoped) |
| Replay bundles | Durable (job-scoped) |
| Optimizer traces | Durable (job-scoped) if used |
| Feed-forward state | Runtime-only unless explicitly checkpointed by a future contract |

---

## 9. Failure Model (Aligned with Eigen OS Error Model)

HWE MUST follow `error-model.md` / `error-mapping.md` conventions:

- invalid inputs / malformed context → `INVALID_ARGUMENT`
- state-dependent rejections (policy forbids, missing prerequisite artifacts) → `FAILED_PRECONDITION`
- unsupported features (live qubits, unsupported backend class) → `UNIMPLEMENTED`
- quota/capacity pressure → `RESOURCE_EXHAUSTED` (+ `RetryInfo`)
- transient telemetry/registry outage → `UNAVAILABLE` (+ `RetryInfo`)
- planning/adaptation timeout → `DEADLINE_EXCEEDED`
- invariant violation → `INTERNAL`
- coordination/lease conflicts (distributed) → `ABORTED` where applicable

### 9.1 Standard HWE Failure Taxonomy (Stable Reason Codes)

HWE MUST expose stable machine-readable reasons using `google.rpc.ErrorInfo.reason` with `EIGEN_HWE_*` codes, e.g.:

- `EIGEN_HWE_TELEMETRY_STALE`
- `EIGEN_HWE_ADAPTATION_CONFLICT`
- `EIGEN_HWE_FALLBACK_EXHAUSTED`
- `EIGEN_HWE_POLICY_DENIED`
- `EIGEN_HWE_OPTIMIZER_TIMEOUT`
- `EIGEN_HWE_OPTIMIZER_UNTRUSTED`
- `EIGEN_HWE_TOPOLOGY_INVALID`
- `EIGEN_HWE_REPLAY_MISMATCH`

---

### 9.2 Deterministic Fallback Policy

When:

- optimizer is unavailable,
- telemetry confidence is insufficient,
- inference exceeds timeout,
- optimizer output fails validation,

HWE MUST fall back to a **deterministic heuristic** decision path.

Fallback decisions MUST:

- emit explicit audit markers,
- preserve replay compatibility in deterministic mode,
- preserve AQO semantics (unless a validated transformation is explicitly allowed).

---

## 10. Observability Contract

### 10.1 Contract Marker Metric

HWE exporters MUST expose: `eigen_hwe_contract_info{version="1.0.0"} 1`

---

### 10.2 Required Metrics (Normative)

All metrics MUST have bounded labels and deterministic semantics.

Required families:

- `eigen_hwe_decisions_total{result}`
- `eigen_hwe_decision_duration_seconds` (histogram family)
- `eigen_hwe_adaptations_total{action}`
- `eigen_hwe_fallbacks_total{reason}`
- `eigen_hwe_telemetry_age_seconds` (gauge)
- `eigen_hwe_optimizer_errors_total{reason}`
- `eigen_hwe_replay_mismatches_total`

---

### 10.3 Label Cardinality Rules

Labels MUST NOT include:

- `job_id`
- `trace_id`
- `tenant_id` (unless a strictly bounded configured set; default: forbidden)
- `user_id`
- freeform strings / error messages

Allowed bounded labels SHOULD include only:

- `result` (finite enum)
- `action` (finite enum)
- `reason` (stable taxonomy)
- `policy_mode` (finite enum)

---

### 10.4 Tracing

HWE MUST emit OpenTelemetry spans for:

- telemetry ingestion snapshotting
- backend selection
- optimizer invocation
- adaptation execution
- replay validation

Trace correlation MUST propagate `traceparent` and link to `job_id` in logs (not as metric labels).

---

### 10.5 Explainability

Every adaptive runtime decision MUST produce structured explainability metadata (stored as QFS artifact and optionally surfaced via dispatch rationale APIs):

Required fields:

```text
- selected_backend
- rejected_candidates (bounded list or summary)
- decision_reason (stable code)
- topology_summary (bounded)
- optimizer_confidence (optional)
- policy_constraints (bounded summary)
- fallback_reason (if fallback used)
- hwe_decision_digest
```

---

## 11. Security and Trust

### 11.1 Runtime Isolation

HWE MUST enforce:

- no server-side user code execution
- policy validation before adaptation
- strict input validation for telemetry and optimizer outputs
- isolation boundaries for any ML inference runtime (when present)

---

### 11.2 Optimizer Trust Policy

Before accepting optimizer decisions, HWE MUST validate:

- model signature/provenance (when model registry exists),
- compatibility versions,
- determinism policy compliance (if deterministic mode),
- explainability availability (at least L2 operator metadata),
- symbolic safety checks pass.

---

### 11.3 Data Minimization

Telemetry sent to adaptive systems MUST be minimized to operational signals only:

- topology
- calibration/noise summaries
- queue/capacity signals
- execution constraints

Secrets and provider credentials MUST NOT be included in telemetry or artifacts.

---

## 12. Conformance, CI, and Closure Criteria

### 12.1 CI Requirements (Target)

CI MUST validate:

1. deterministic decision output when deterministic=true
2. stable reason codes (`EIGEN_HWE_*`)
3. QFS job-scoped artifact persistence for decisions/adaptations
4. bounded-label enforcement for metrics
5. contract marker metric presence
6. alert/dashboard query compatibility (when monitoring assets exist)

---

### 12.2 Minimum Closure Criteria (Target)

HWE is considered fully realized when:

1. planning and adaptation are centralized (service or module boundary),
2. deterministic replay bundles are produced and validated,
3. optimizer integration supports validated advisory outputs + deterministic fallback,
4. decision and adaptation artifacts are durable in QFS per job,
5. metrics + tracing are wired end-to-end with bounded labels,
6. error mapping conforms to `error-model.md` / `error-mapping.md`.

---

## 13. Architectural Invariants

1. **Determinism:** Adaptive decisions are replayable under deterministic mode.
2. **Safety:** Runtime adaptation MUST NOT change quantum semantics beyond explicitly permitted and validated transformations.
3. **Explainability:** Every decision/adaptation MUST be explainable and auditable.
4. **Isolation:** Provider failures MUST be normalized and must not leak raw provider payloads to public contracts.
5. **Compatibility:** HWE APIs, artifacts, and telemetry schemas MUST be versioned and evolve under SemVer discipline.

---

## 14. Final Status Summary

#### Implemented Today (Baseline)

- kernel-to-driver execution boundary
- driver capability negotiation
- backend abstraction
- execution normalization
- structured logging + trace propagation
- simulator execution baseline

#### Planned / Not Yet Implemented (Required for Full Target)

- standalone or clearly bounded HWE module/service
- centralized adaptation engine + replay bundles
- hardware telemetry snapshot normalization and persistence
- validated GNN optimizer integration
- live qubit lifecycle (post-MVP)
- conformance suite and SRE monitoring assets aligned to this contract

HWE is the long-term hardware-aware runtime intelligence layer connecting deterministic AQO execution with adaptive optimization, while preserving strict reproducibility, safety, and observability contracts across heterogeneous quantum backends.
