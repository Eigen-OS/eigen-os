# GNN Optimizer

**Status:** Normative architecture + contract specification (Eigen OS 1.0 / MVP + approved extensions)
**Subsystem:** Hardware-aware optimization (placement/routing), topology & noise adaptation, deterministic fallback
**Contract namespace:** `eigen.internal.v1` (OptimizerService)
**Applies to:** Compiler, Kernel/QRTX, Driver Manager, Runtime Controller/Scheduler, Model Registry, QFS lineage/telemetry

---

## 1. Purpose

The **GNN Optimizer** is the intelligent hardware optimization subsystem of Eigen OS. It transforms **hardware-agnostic** quantum execution plans (AQO) into **backend-optimized** execution strategies by combining:

- deterministic symbolic optimization passes (always safe, always replayable),
- ML inference (GNN-based recommendations),
- explicit policy constraints (latency/cost/compliance/determinism),
- and a deterministic fallback chain.

The optimizer operates between:

- compiler AQO generation,
- kernel scheduling / dispatch,
- driver-manager backend execution.

Primary objectives:

- maximize predicted fidelity on noisy hardware,
- minimize routing overhead (SWAP insertion / depth),
- respect topology constraints,
- produce deterministic outputs when requested,
- provide explainability artifacts suitable for operators and forensic analysis.

---

## 2. Architectural Role and Boundaries

### 2.1 Position in the System

```text
Eigen-Lang
  ↓
Compiler (Neuro-DPDA / symbolic pipeline)
  ↓
AQO (hardware-agnostic)
  ↓
GNN Optimizer (hardware-aware adaptation)
  ↓
Driver Manager (provider normalization + execution dispatch)
  ↓
Hardware / Simulator / Vendor Cloud
```

---

### 2.2 What the GNN Optimizer is

- a **hardware adaptation engine** (logical→physical placement),
- a **topology-aware routing engine** (routing plan / SWAP strategy),
- a **noise-aware transformation selector** (prefer higher predicted fidelity),
- an **explainable decision system** (reason codes, confidence, traceability),
- a **deterministic contract surface** when determinism mode is enabled.

---

### 2.3 What the GNN Optimizer is not

- not a public API (internal-only),
- not allowed to weaken compiler safety invariants,
- not allowed to introduce nondeterministic behavior in deterministic mode,
- not allowed to bypass policy constraints or security validation,
- not allowed to leak provider secrets or raw provider payloads.

---

## 3. Contract Versioning

### 3.1 Contract Marker

The optimizer service contract is versioned at the **RPC envelope level**.

- Service: `eigen.internal.v1.OptimizerService`
- Request field: `contract_version` (semver string, e.g. "`1.0.0`")

**Rule:** Every Optimize request MUST include `contract_version`. Responses MUST echo the same value.

---

### 3.2 SemVer Policy (Optimizer Contract)

#### MAJOR

Breaking changes:

- request/response rename or removal,
- semantic changes to placement/routing outputs,
- incompatible label/schema changes,
- determinism behavior changes.

#### MINOR

Backward-compatible additions:

- additive optional fields,
- new reason codes,
- new explanation fields,
- new metrics (bounded labels only).

#### PATCH

Implementation fixes and doc clarifications that do not change semantics.

---

## 4. Current Repository State (Truthful Snapshot)

### 4.1 Implemented Adjacent Functionality

The repository includes partial groundwork around optimization, but **not** a production GNN path:

- kernel contains MVP hybrid-loop heuristics (e.g., VQE-like stepping)
- some plugin scaffolding exists (optimizer as a conceptual component)
- architecture references exist in overview and contracts

---

### 4.2 Not Yet Implemented (Production Components Missing)

- dedicated `gnn-optimizer` service daemon
- working gRPC optimizer inference path wired end-to-end
- model registry + model signature verification
- topology feature extraction pipeline
- deterministic replay bundles for optimizer decisions
- placement/routing artifact schemas persisted in QFS as a stable contract
- SLO dashboards + alert pack for optimizer subsystem

---

### 4.3 Internal API Status

- `OptimizerService.OptimizeCircuit` exists in the internal proto surface (per internal contracts)
- In the current codebase it may still be stubbed/unwired depending on deployment profile

---

## 5. Normative Responsibilities

### 5.1 Hardware Topology Optimization

The optimizer MUST:

- compute a **placement plan** (logical qubits → physical qubits),
- minimize routing overhead (SWAP count, depth),
- respect connectivity constraints and forbidden edges,
- maintain execution equivalence (no semantic drift).

---

### 5.2 Noise-Aware Optimization

The optimizer MUST be able to consume a bounded snapshot of backend quality signals, such as:

- readout error rates,
- gate fidelities/error rates,
- coherence times (T1/T2),
- calibration freshness and stability indicators.

The optimizer SHOULD prioritize plans with higher predicted fidelity under the selected policy mode (latency vs fidelity vs cost).

---

### 5.3 Backend Adaptation Across Backend Classes

| **Backend Type** | **Requirement** |
|---|---|
| Superconducting | Required |
| Trapped Ion | Required |
| Photonic | Planned |
| Neutral Atom | Planned |
| Spin Qubit | Future |

**Rule:** If the backend class is unsupported, the optimizer MUST either:

- fall back deterministically to a symbolic/heuristic path, or
- return `UNIMPLEMENTED` (policy-dependent).

---

### 5.4 Graph-Based Circuit Transformation

The optimizer MUST be capable of producing one or more of:

- placement plan
- routing plan (explicit SWAP insertion strategy)
- transformed AQO (still valid AQO schema)
- decomposition hints (backend gate-set adaptation)

Allowed transformations include (policy- and backend-dependent):

- qubit remapping
- routing insertion
- gate decomposition (to native gate set)
- limited reorderings that preserve semantics (subject to validation)
- scheduling hints (parallelism opportunities)

**Constraint:** Any transformation MUST be validated against symbolic correctness checks.

---

### 5.5 Neuro-Symbolic Coordination Safety Boundary

The optimizer is subordinate to symbolic validation:

- ML inference is advisory, not authoritative.
- Symbolic checks MUST reject invalid transformations deterministically.
- In deterministic mode, the optimizer MUST behave replayably given identical inputs.

---

## 6. Determinism and Replay Contract

### 6.1 Determinism Modes

The optimizer MUST support a determinism switch:

- `deterministic = true:` outputs must be replay-stable
- `deterministic = false:` outputs may use nondeterministic exploration, but MUST still be policy-safe and validated

---

### 6.2 Deterministic Input Set

When `deterministic=true`, the optimizer output MUST be a pure function of:

- AQO content hash (canonical AQO bytes)
- `contract_version`
- `optimizer_model_id` (or explicit `fallback_used=true`)
- backend identity + topology snapshot hash
- calibration snapshot hash (or explicit “no calibration” sentinel)
- policy envelope (mode + constraints)
- `seed` (explicit deterministic seed, REQUIRED when deterministic=true)

---

### 6.3 Deterministic Digest

The optimizer MUST output a reproducibility digest:

- `optimizer_digest = sha256(canonical_request_inputs + canonical_outputs)`

This digest MUST be persisted in artifacts and included in response metadata.

---

## 7. Inputs and Outputs

### 7.1 Optimizer Inputs (Normative)

#### Circuit inputs

- AQO payload (or QFS ref to AQO artifact)
- AQO format (AQO JSON / AQO PROTO)
- dependency/structure hints (optional)
- execution constraints (shots, dynamic-circuit flags, etc.)

#### Hardware inputs

- topology graph (connectivity, couplers)
- device capabilities (native gate set, supported operations)
- calibration snapshot (bounded)
- queue/capacity hints (optional, bounded)

#### Runtime/policy inputs

- policy mode: `balanced | latency | cost | availability | deterministic | compliance`
- constraints: max depth, max swaps, forbidden qubits/edges (optional)
- deadlines: feature extraction budget, inference budget, total optimization budget
- determinism: `deterministic` bool + `seed`

---

### 7.2 Optimizer Outputs (Normative)

The optimizer produces:

| **Output** | **Required** | **Notes** |
|---|---|---|
| `optimized_circuit` (AQO) | yes (unless rejected) | May be identical to input when fallback used |
| `placement_plan` | optional | logical→physical mapping; required for many hardware backends |
| `routing_plan` | optional | swap/routing strategy; may be embedded into AQO |
| `fidelity_estimate` | optional | bounded numeric + units |
| `latency_estimate_ms` | optional | bounded numeric |
| `confidence_score` | optional | bounded [0..1] |
| `fallback_used` | required | boolean |
| `fallback_reason` | required if fallback_used | stable reason code |
| `explanation_ref` | optional | QFS reference to explain payload |
| `optimizer_digest` | required | reproducibility hash |

---

## 8. Internal API (gRPC) — Contract Alignment

### 8.1 Service

```text
eigen.internal.v1.OptimizerService
```

---

### 8.2 OptimizeCircuit (Normative Semantics)

#### Request MUST include:

- contract_version
- AQO payload or qfs_ref
- backend identity (device/backend id)
- determinism flag and seed (seed required when deterministic=true)
- objective/policy envelope

#### Response MUST include:

- transformed AQO payload (or QFS ref)
- `fallback_used` + `fallback_reason` if applicable
- timing metrics (latency)
- trace/correlation metadata
- deterministic digest

**Note:** If the optimizer service is not deployed, callers MUST treat it as optional and rely on fallback/heuristic behavior in compiler/kernel (policy-dependent).

---

## 9. Fallback and Degradation Behavior

The optimizer MUST provide a deterministic fallback chain:

```text
GNN inference
  ↓ (failure / confidence below threshold / policy forbids)
Heuristic optimizer (deterministic)
  ↓ (failure)
Static topology mapper (deterministic)
  ↓ (failure)
Reject optimization request
```

---

### 9.1 Confidence Thresholds

If confidence thresholds are used:

- thresholds MUST be versioned and deterministic
- thresholds MUST be frozen per MINOR contract version
- thresholds MUST be observable (exported as config info metric or included in explain payload)

---

## 10. Failure Model (Aligned with Eigen OS Error Model)

The optimizer MUST follow `error-model.md` / `error-mapping.md`:

- Validation failures → `INVALID_ARGUMENT` (+ `BadRequest` details)
- Unsupported backend/features → `UNIMPLEMENTED`
- State-dependent rejection (policy forbids, missing prerequisites) → `FAILED_PRECONDITION`
- Resource pressure (model cache OOM, quota) → `RESOURCE_EXHAUSTED` (+ `RetryInfo`)
- Transient model registry outage → `UNAVAILABLE` (+ `RetryInfo`)
- Deadline budget exceeded → `DEADLINE_EXCEEDED`
- Unexpected invariant violation → `INTERNAL`

---

### 10.1 Stable Failure Reason Codes (Machine-Readable)

The optimizer MUST expose stable reason codes via `google.rpc.ErrorInfo.reason` using an `EIGEN_OPT_*` family, for example:

- EIGEN_OPT_MODEL_LOAD_FAILED
- EIGEN_OPT_INVALID_TOPOLOGY
- EIGEN_OPT_INFERENCE_TIMEOUT
- EIGEN_OPT_NON_DETERMINISTIC_OUTPUT
- EIGEN_OPT_POLICY_REJECTED
- EIGEN_OPT_FEATURE_EXTRACTION_FAILED
- EIGEN_OPT_UNSUPPORTED_BACKEND
- EIGEN_OPT_CONFIDENCE_TOO_LOW

---

## 11. QFS Integration (Artifacts and Layout)

Optimizer artifacts MUST be stored under the job’s QFS namespace (preferred, consistent with QFS v1.0):

```text
qfs://jobs/<job_id>/
  compiled/               # compiler outputs
  results/                # execution outputs
  logs/
  meta/
  optimizer/              # optimizer artifacts (this section)
```

---

### 11.1 Proposed Stable Optimizer Layout

```text
qfs://jobs/<job_id>/optimizer/
  request.json            # normalized optimizer request snapshot (bounded)
  input_aqo.ref           # ref/hash to input AQO
  topology.ref            # ref/hash to topology snapshot
  calibration.ref         # ref/hash to calibration snapshot (optional)
  optimized_aqo.json      # optimized circuit (or ref)
  placement.json          # placement plan (optional)
  routing.json            # routing plan (optional)
  explain.json            # explanation payload (optional; bounded)
  decision.json           # decision summary incl fallback + confidence + digest
```

---

### 11.2 Integrity Rules

- All refs MUST be content-addressed or include checksums.
- Artifacts MUST not include secrets.
- Payload sizes MUST be bounded; large objects should be referenced.

---

## 12. Observability Contract

The optimizer MUST align with the **Intelligent Runtime Observability Contract** principles (bounded labels, deterministic semantics), but it has its own metric namespace.

### 12.1 Required Metrics (Normative)

```text
eigen_optimizer_contract_info{version="1.0.0"} 1

eigen_optimizer_requests_total{result}
eigen_optimizer_latency_seconds_bucket
eigen_optimizer_latency_seconds_sum
eigen_optimizer_latency_seconds_count

eigen_optimizer_fallback_total{reason}
eigen_optimizer_inference_failures_total{reason}
eigen_optimizer_confidence_gauge
eigen_optimizer_improvement_score_gauge
```

Rules:

- Labels MUST be bounded (no `job_id`, no `trace_id`, no raw device_id if unbounded).
- Histograms MUST be exported as complete families (`_bucket/_sum/_count`).

---

### 12.2 Required Tracing

Spans SHOULD include:

- feature extraction span
- inference span
- validation span
- routing/placement generation span
- fallback span (if used)

All spans must propagate `traceparent` and be correlated to `job_id` in logs (not as metric label).

---

## 13. Security and Trust

### 13.1 Model Provenance and Supply Chain

Production models MUST support:

- checksum validation,
- signature verification,
- provenance metadata (who/when built),
- immutable version identifiers (`optimizer_model_id`).

---

## 13.2 Isolation and Resource Quotas

Inference execution MUST support:

- sandboxing (process/container isolation),
- CPU/memory/GPU quotas,
- timeouts per stage,
- safe failure (telemetry must not kill runtime).

---

### 13.3 Tenant Controls (Policy)

Policy MUST allow:

- ML optimization disabled (force heuristic-only)
- deterministic-only mode enforced
- compliance mode (restricted transformations)
- bounded explainability levels (L1/L2/L3) consistent with system observability contracts

---

## 14. Performance Targets (Engineering Targets)

Recommended budgets (not guaranteed SLAs):

| **Stage** | **Target** |
|---|---|
| Feature extraction | < 10 ms |
| Inference | < 50 ms |
| Routing/placement generation | < 100 ms |
| Total optimization | < 200 ms (typical) |


---

## 15. Compliance Status Summary

| **Capability** | **Status** |
|---|---|
| Architecture placement | Implemented in docs |
| Internal service contract existence | Present in internal API surface (may be stub/unwired) |
| Determinism rules | Normative here (implementation pending) |
| Dedicated service + inference path | Not implemented |
| Model registry + signatures | Not implemented |
| QFS artifacts layout | Not implemented |
| Optimizer observability metrics | Defined here (implementation pending) |
| Explainability payloads | Not implemented |
| Fallback chain (deterministic) | Partially present via heuristics elsewhere; formal chain pending |

---

## 16. Conclusion

The GNN Optimizer is a **mandatory** target-architecture component for Eigen OS hardware-aware execution. This document freezes the **normative contract** for:

- inputs/outputs,
- determinism and replay,
- fallback behavior,
- error mapping,
- QFS artifacts,
- observability surface,
- and security requirements.
