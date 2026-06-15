# Neuro-Symbolic Core (NSC)
- **Contract version:** `1.0.0`
- **Phase:** Phase 1+ / Post-MVP strategic runtime capability
- **Status:** Target architecture contract with documented implemented prerequisites; **no standalone NSC service is currently active in the production execution path**
- **Applies to:** (future) `NeuroSymbolicService`, Compiler (Neuro-DPDA path), Kernel/QRTX, HWE, GNN Optimizer, Knowledge Base / OKB, Driver Manager, QFS lineage layer, Telemetry exporters

This document defines the **normative target architecture**, contracts, responsibilities, integration boundaries, and implementation requirements for the Eigen OS **Neuro-Symbolic Core (NSC)**. It is aligned with:

- deterministic compilation and execution invariants,
- DPDA-based semantic admissibility control,
- Knowledge Base / Optimization Knowledge Base (OKB) integration,
- hardware-aware GNN optimization,
- policy execution, explainability, and replay safety.

---

## 0. Contract Marker (Observability)

All NSC telemetry exporters MUST expose:

```text
eigen_nsc_contract_info{version="1.0.0"} 1
```

---

## 1. Purpose

The Neuro-Symbolic Core (NSC) is the central intelligent decision subsystem of Eigen OS responsible for combining:

1. symbolic reasoning,
2. deterministic compiler/runtime constraints,
3. neural inference models,
4. graph-based hardware optimization,
5. adaptive execution policies,
6. knowledge retrieval and reuse,

into a unified decision framework for **compilation and execution optimization**.

NSC operates as a **bounded advisory orchestration layer** above deterministic baseline runtime behavior.

**Deterministic baseline behavior remains authoritative at all times.**

---

## 2. Scope and Non-Goals

### 2.1 In scope

NSC governs:

- semantic enrichment of compiler/runtime decisions,
- symbolic validation and constraint reasoning (DPDA authority),
- optimization strategy scoring and selection recommendations,
- topology-aware backend mapping recommendations,
- orchestration of GNN-based hardware optimization (advisory),
- OKB retrieval and feedback integration (optional dependency),
- explainability and replay bundle generation for NSC decisions,
- deterministic fallback preservation.

---

### 2.2 Out of scope

NSC MUST NOT:

- execute user code,
- bypass compiler AST safety policies,
- bypass deterministic AQO guarantees,
- directly call vendor SDKs or backends,
- own job lifecycle state transitions (Kernel/HWE own lifecycle),
- introduce unbounded nondeterminism into compile/execute paths.

---

## 3. Versioning and Compatibility (SemVer)

This contract follows SemVer.

### MAJOR

Required for:

- RPC method/field removals or renames,
- incompatible response semantics,
- incompatible decision taxonomy changes,
- changes to determinism/replay semantics.

### MINOR

Allowed:

- additive fields and optional RPCs,
- additive reason codes,
- additive explainability levels,
- bounded-cardinality telemetry dimensions.

### PATCH

Allowed:

- documentation corrections,
- observability tuning without semantic changes,
- implementation fixes preserving semantics.

---

## 4. Architectural Role

NSC provides:

- optimization recommendations and rankings,
- semantic legality checks (symbolic/DPDA),
- bounded neural scoring (advisory),
- orchestrated GNN hardware adaptation (advisory),
- OKB-aware reuse hints (optional),
- explainability and replay metadata for all NSC decisions.

NSC never bypasses:

- compiler safety policies,
- deterministic AQO guarantees,
- runtime isolation boundaries,
- policy enforcement layers.

---

## 5. Current Implementation Status (Repository Truth)

### 5.1 Implemented prerequisites (today)

Compiler/runtime baseline:

- deterministic AST-only compilation path,
- AQO canonical lowering pipeline,
- kernel execution orchestration,
- driver-manager execution abstraction,
- structured runtime metadata propagation,
- VQE iterative optimization metadata flow (heuristic).

Ecosystem and governance groundwork:

- plugin architecture includes `optimizer` plugin category,
- governance framework and RFC/ADR workflow exist,
- runtime tracing and structured logging exist.

Intelligent-adjacent behavior:

- simple heuristic optimization loops exist in VQE paths,
- backend capability metadata exists through runtime contracts,
- limited runtime telemetry propagation exists.

---

### 5.2 Not implemented (today)

- standalone `neuro-symbolic-core` service,
- protobuf/gRPC NSC API,
- runtime neural inference engine,
- DPDA semantic engine implementation,
- production GNN optimizer runtime,
- OKB-driven optimization retrieval on the request path,
- explainability engine producing stable NSC decision artifacts,
- model registry + signed model lifecycle,
- confidence-aware policy gating and deterministic rollback controller.

The implemented NSC compiler path MUST still capture an immutable policy snapshot at service start and use that frozen snapshot for all inference requests. Live policy lookups MUST NOT be part of request-time scoring.

**Production execution MUST NOT depend on NSC availability.**

---

## 6. Core Principles (Normative)

### 6.1 Deterministic Baseline First

Deterministic compiler/runtime path remains authoritative.

NSC outputs:

- MAY recommend,
- MAY rank,
- MAY enrich,
- MAY optimize (advisory),

but MUST never invalidate deterministic correctness guarantees.

If uncertainty, timeout, policy violation, untrusted model, or degradation occurs, the system MUST revert to deterministic baseline execution.

---

### 6.2 Bounded Intelligence

NSC operates only inside explicitly defined policy boundaries.

NSC:

- cannot mutate source semantics,
- cannot bypass compiler validation,
- cannot introduce unsafe runtime behavior,
- cannot emit unverifiable transformations,
- cannot violate tenant/runtime policies.

---

### 6.3 Explainability Required

Every accepted NSC recommendation MUST include:

- provenance,
- model version (or “heuristic/symbolic-only”),
- confidence score (bounded numeric),
- feature set summary (bounded and reproducible),
- retrieval references for the scored evidence,
- reasoning metadata (bounded),
- fallback eligibility,
- reproducibility hash (digest),
- policy context summary (bounded).

Opaque decisions are prohibited.

---

### 6.4 Determinism and Replay

NSC MUST support deterministic mode.

When `deterministic=true`, outputs MUST be a pure function of canonical inputs + seed and MUST be replayable byte-for-byte at the decision artifact level (canonical serialization).

The active policy snapshot version used for scoring MUST be included in response metadata and audit logs so replay evidence is bound to the same immutable snapshot.

The audit record MUST also retain the explainability envelope with model version, feature set summary, confidence, and retrieval references so the same inference can be replayed deterministically from immutable artifacts.

The immutable audit trail MUST additionally capture caller identity, tenant, policy snapshot version, model version, retrieval sources, and final decision for every scoring operation.

---

## 7. Major Internal Subsystems (Target Architecture)

### 7.1 Symbolic Reasoning Engine (DPDA authority)

#### Responsibility

Deterministic symbolic reasoning and semantic validation.

#### Responsibilities include

- semantic constraint evaluation,
- optimization legality checks,
- policy validation (hard constraints),
- transformation verification,
- rule enforcement,
- admissibility proof artifacts (or references),
- explainability scaffolding.

#### DPDA integration (mandatory)

NSC symbolic engine SHALL include a deterministic pushdown automaton (DPDA)-based semantic controller responsible for:

- deterministic grammar/state tracking,
- semantic transition validation,
- constrained symbolic reasoning,
- state-safe transformation approval,
- runtime-safe adaptive transition validation.

DPDA is authoritative for:

- semantic admissibility,
- transformation legality,
- deterministic rollback boundaries.

Neural inference MAY propose transformations.
**Only symbolic validation may authorize them.**

---

### 7.2 Neural Inference Layer (advisory)

#### Responsibility

Learned scoring and optimization recommendation capabilities.

#### Responsibilities include

- optimization ranking,
- backend scoring,
- heuristic prediction,
- execution strategy recommendations,
- confidence estimation.

#### Requirements

- inference MUST be side-effect free,
- outputs MUST be reproducible under deterministic mode (seeded),
- decisions MUST be traceable,
- confidence metadata is mandatory,
- deterministic fallback path is mandatory.

---

### 7.3 GNN Hardware Optimizer (advisory, validated)

#### Responsibility

Graph-based hardware adaptation integrated into NSC planning.

Performs:

- qubit placement optimization,
- routing optimization,
- topology-aware transformation scoring,
- noise-aware mapping,
- backend adaptation planning.

#### Inputs

- AQO graph projections,
- backend topology snapshot digest,
- calibration/noise metadata digest,
- coupling maps,
- queue pressure signals (bounded),
- execution policy constraints.

#### Outputs

- placement maps,
- routing plans,
- scored alternatives (bounded),
- confidence metadata,
- explainability metadata,
- deterministic replay hashes.

#### Deterministic safety requirement

GNN outputs are advisory unless explicitly enabled by policy.

If:

- confidence insufficient,
- topology stale,
- inference fails,
- determinism validation fails,

runtime MUST revert to deterministic heuristic routing.

---

### 7.4 Knowledge Base / OKB Integration Layer (optional dependency)

#### Responsibility

Retrieval + writeback integration with Knowledge Base / Optimization Knowledge Base.

Responsibilities:

- historical optimization retrieval,
- reusable transformation lookup,
- feedback ingestion,
- replay trace generation.

**OKB availability MUST NOT block execution.**

---

### 7.5 Explainability Engine

#### Responsibility

Operator-visible reasoning traces and replay bundles.

Outputs MUST include:

- selected decision + why,
- why alternatives rejected,
- model provenance and version,
- policy constraints applied,
- fallback reasons (if any),
- confidence breakdown (bounded),
- deterministic replay identifiers and digests.

---

## 8. Interfaces (Target Contract)

### 8.1 Service identity

NSC SHALL expose a dedicated internal service:

```text
eigen.internal.v1.NeuroSymbolicService
```

The initial contract surface is the internal `ScoreCompilationPlan` RPC. All callers MUST present authenticated internal service identity and a versioned request envelope; public ingress MUST NOT route to this service directly.

---

### 8.2 Required RPC methods (target)

Compilation / optimization:

- `ScoreCompilationPlan`
- `SelectOptimizationStrategy`
- `RecommendBackendMapping`
- `OptimizeHardwareTopology`
- `ValidateAdaptiveTransformation`

Explainability:

- `ExplainDecision`
- `GetDecisionTrace`

Knowledge integration:

- `RetrieveOptimizationCandidates`
- `PublishOptimizationFeedback`

---

### 8.3 Required request metadata

All requests MUST support (as structured fields or standardized metadata):

- `trace_id` (correlation, not as metric label),
- policy context digest,
- determinism mode + `seed` (required when deterministic=true),
- tenant/project context (NOT as metric label; redacted/hashed where applicable),
- internal request metadata MUST carry the same tenant/project binding used by the request context,
- feature schema version,
- timeout budget,
- replay identifier (if present),
- a mandatory preprocessing redaction layer that removes bearer tokens, API keys, tenant-private secrets, credentials, session cookies, and raw auth headers before scoring,
- masking of email addresses, phone numbers, and internal identifiers before model input,
- redacted field paths recorded in audit/log metadata only.

---

### 8.4 Required response metadata

All responses MUST include:

- `confidence` (bounded numeric),
- `provenance` (stable reference or “symbolic-only”),
- `model_version` (or “none”),
- `feature_set` (bounded summary),
- `retrieval_references` (bounded list),
- `deterministic_compatible` (bool),
- `fallback_eligible` (bool),
- explainability payload or reference,
- reproducibility hash (digest),
- stable reason codes for rejection/denial.

---

## 9. Integration Boundaries (Authority Rules)

### 9.1 Compiler integration

Compiler MAY invoke NSC for advisory scoring and hints.

**Compiler validation remains authoritative.**

---

### 9.2 Kernel/QRTX integration

Kernel MAY invoke NSC for advisory backend selection and routing recommendations.

**Kernel lifecycle and orchestration contracts remain authoritative.**

---

### 9.3 Driver Manager integration

NSC MAY consume topology, queue depth summaries, noise data summaries, capability metadata.

NSC MUST NOT directly invoke vendor SDKs.

---

### 9.4 HWE integration

HWE remains authoritative for runtime adaptation and execution lifecycle.
NSC provides recommendations only.

---

## 10. Canonical Inputs and Outputs

### 10.1 Canonical inputs (bounded)

Compiler-side:

- AQO IR digest,
- semantic signatures,
- optimization candidates summary,
- target constraints digest.

Runtime-side:

- backend topology snapshot digest,
- calibration/noise snapshot digest,
- queue metrics summary (bounded),
- execution constraints digest,
- policy envelope digest.

Knowledge-side (optional):

- candidate artifact references,
- historical performance summaries (bounded),
- provenance references.

---

### 10.2 Canonical outputs

- ranked optimization actions (bounded list),
- backend mapping suggestions,
- placement/routing recommendations,
- symbolic validation state + reason codes,
- explainability payload/ref,
- deterministic replay digest.

---

## 11. Storage and State (Target)

### 11.1 Required storage domains

- online inference cache (TTL),
- model registry (signed manifests, version pinning, rollback),
- feature store (bounded normalized features),
- decision trace store (explainability + replay bundles),
- offline training datasets (out of request path).

---

### 11.2 QFS integration (required when NSC influences a job)

When NSC affects compilation/execution decisions, artifacts MUST be persisted under job scope:

```text
qfs://jobs/<job_id>/nsc/
  decision.json
  explain.json
  replay_bundle.json
  inputs_digest.txt
  outputs_digest.txt
```

Artifacts MUST be immutable once the job reaches a terminal state.

---

## 12. Error Semantics (Aligned with Eigen OS error model)

NSC MUST follow “gRPC-status-first” and structured error details rules.

Canonical mapping:

- invalid request / schema mismatch → `INVALID_ARGUMENT` (+ `google.rpc.BadRequest`)
- unsupported feature → `UNIMPLEMENTED`
- state-dependent denial (policy forbids) → `FAILED_PRECONDITION`
- model/registry unavailable (transient) → `UNAVAILABLE` (+ `RetryInfo`)
- quota/capacity exceeded → `RESOURCE_EXHAUSTED` (+ `RetryInfo`)
- internal invariant violation → `INTERNAL`
- deadline exceeded → `DEADLINE_EXCEEDED`

NSC MUST include `google.rpc.ErrorInfo` with stable machine-readable `reason` codes (e.g., `EIGEN_NSC_*`).

---

## 13. Failure Modes and Fallback Policy (Normative)

### 13.1 Mandatory failure classes

NSC SHALL explicitly handle:

- inference timeout,
- low-confidence result,
- model incompatibility,
- stale model / stale topology,
- policy violation,
- invalid topology,
- DPDA semantic rejection,
- OKB miss/unavailable,
- feature-schema mismatch,
- explainability generation failure,
- determinism/replay mismatch.

---

### 13.2 Mandatory fallback chain

Neural failure MUST NEVER block execution.

Fallback chain:

1. symbolic validation (DPDA) only,
2. deterministic heuristic optimizer (no ML),
3. compiler baseline,
5. runtime baseline.

Fallback MUST:

- emit explicit audit markers,
- preserve replay compatibility in deterministic mode,
- never silently degrade.

---

## 14. Observability (Normative)

### 14.1 Required metrics (bounded labels only)

NSC SHALL emit:

- request counts,
- latency histograms,
- fallback rate,
- confidence distribution (bucketed),
- inference failures,
- DPDA rejection counts,
- model registry failures,
- replay consistency violations.

Example metric families (names are normative if adopted; labels must be bounded):

- `eigen_nsc_requests_total{rpc}`
- `eigen_nsc_latency_ms_bucket{rpc}`
- `eigen_nsc_fallbacks_total{reason}`
- `eigen_nsc_inference_failures_total{reason}`
- `eigen_nsc_dpda_rejections_total{reason}`
- `eigen_nsc_replay_mismatches_total`

---

### 14.2 Label cardinality rules

Metric labels MUST NOT include:

- `job_id`, `trace_id`, `tenant_id`, `user_id`,
- freeform error messages,
- arbitrary model output strings.

Correlation identifiers belong in traces/logs and QFS artifacts, not metric labels.

---

### 14.3 Tracing

Tracing MUST correlate:

- compiler phases,
- kernel execution,
- NSC decision points,
- optimizer decisions,
- OKB retrieval,
- replay validation.

---

### 14.4 Explainability logging

Every accepted optimization MUST be auditable.

Logs MUST include:

- model version,
- confidence,
- policy digest,
- DPDA validation outcome,
- replay digest,
- fallback markers (if used).

---

## 15. Security and Governance (Normative)

### 15.1 Model trust

All active models MUST support:

- signature verification,
- provenance validation,
- rollback support,
- compatibility verification.

Unsigned/untrusted models MUST NOT execute in production.

---

### 15.2 Isolation

Inference runtime SHALL support:

- sandboxing,
- resource quotas,
- deterministic execution constraints,
- tenant isolation.

---

### 15.3 Governance controls

Platform SHALL support:

- feature flags,
- advisory-only mode,
- tenant-level disablement,
- deterministic-only mode,
- rollback enforcement,
- emergency “ML-off” switch.

---

### 15.4 Normalized security context propagation


Every NSC request MUST carry a normalized security context with bounded, non-secret fields:

- `tenant_id`
- `project_id`
- `subject_id`
- `workload_id`
- `policy_snapshot_id`
- `authz_decision_id`

These values MUST be validated before inference, included in replay artifacts, and surfaced in audit events. Missing fields MUST fail closed. The inbound `x-eigen-tenant-id` and `x-eigen-project-id` request metadata MUST match the normalized request context exactly; any mismatch MUST fail closed with `PERMISSION_DENIED`. Raw bearer tokens, tenant-private secrets, and unredacted payload fragments MUST NOT be forwarded into NSC logs or model inputs.

---

## 16. CI / Conformance Requirements (Target)

CI MUST validate (when NSC is enabled in any environment):

1. deterministic outputs with fixed seed under deterministic mode,
2. stable reason codes,
3. fallback correctness (no hard dependency),
4. DPDA rejection determinism,
5. replay bundle generation and digest consistency,
6. contract marker metric presence,
7. bounded label enforcement.

Golden tests SHOULD include:

- low confidence → fallback,
- inference timeout → fallback,
- stale topology → fallback,
- DPDA reject → deny or fallback per policy,
- OKB unavailable → baseline,
- replay mismatch → explicit error + artifact persistence.

---

## 17. Compliance Status Snapshot (Truthfulness)

#### Implemented prerequisites

- deterministic compiler/runtime baseline,
- AQO pipeline,
- plugin governance groundwork,
- optimization metadata propagation,
- tracing/logging infrastructure.

#### Implemented contract surface

- `NeuroSymbolicService` internal model-service contract,
- SemVer request/response envelope,
- authenticated internal identity gate,
- mandatory feature-extraction redaction layer for model input,
- fail-closed rejection for unsupported contract versions.

#### Still not implemented

- DPDA semantic engine runtime,
- neural inference runtime,
- GNN optimizer runtime,
- explainability engine + QFS decision artifacts,
- model registry,
- OKB integration on request path,
- adaptive orchestration controller.

---

## 18. Traceability Requirements (Hard Invariants)

Any future implementation MUST preserve:

- deterministic execution guarantees,
- explainability requirements,
- rollback capability,
- policy isolation,
- compiler/kernel/HWE authority boundaries,
- symbolic validation precedence (DPDA authority),
- deterministic fallback behavior,
- auditable and replay-safe decision artifacts.

No implementation may bypass these guarantees.

---

## Appendix A. Diagrams (normative)

### A.1 C4 — System Context (NSC as advisory layer)

![System Context](https://i.imgur.com/Xz1ShOk.png)

<details>
<summary>code</summary>

```text
flowchart LR
    Client[Client SDKs / CLI] --> API[System API]
    API --> K[Kernel / QRTX]

    subgraph Runtime["Eigen OS Runtime"]
        K --> C["Compiler (Neuro-DPDA)"]
        K --> HWE[HWE]
        K --> DM[Driver Manager]

        C -->|"advisory scoring"| NSC["NeuroSymbolicService (NSC)<br/>internal-only"]
        HWE -->|"advisory planning"| NSC

        NSC -->|"optional lookup"| OKB["Optimization Knowledge Base (OKB)<br/>optional dependency"]
        NSC -->|"advisory placement/routing"| OPT["GNN Optimizer<br/>(optional, validated)"]

        OPT -->|"topology/calibration"| DM
        HWE --> DM --> HW["Hardware / Simulator"]
    end

    C --> QFS[(QFS)]
    K --> QFS
    HWE --> QFS
    NSC --> QFS
    OKB --> QFS

    NSC --> OBS[Observability]
    OKB --> OBS
    OPT --> OBS
	style Runtime fill:#FFFFFF
```

</details>

---

### A.2 C4 — Component Diagram (Inside NSC)

![Component Diagram](https://i.imgur.com/kaQj7Vh.png)

<details>
<summary>code</summary>

```text
flowchart TB
  subgraph NSC["NeuroSymbolicService (NSC) — internal"]
    RPC["RPC Layer\nScoreCompilationPlan / SelectOptimizationStrategy /\nRecommendBackendMapping / OptimizeHardwareTopology /\nValidateAdaptiveTransformation /\nExplainDecision / GetDecisionTrace"]
    FEAT["Feature Builder\n(bounded, schema-versioned)"]
    DPDA["Symbolic Engine (DPDA authority)\nallowed_actions + semantic admissibility"]
    NEUR["Neural Scoring\n(seedable, side-effect free)"]
    POL["Policy Gate\n(hard constraints, tenant policy digests)"]
    ORCH["Optimizer Orchestrator\n(call GNN Optimizer advisory)"]
    KB["OKB Adapter (optional)\n(retrieve candidates + feedback)"]
    EXPL["Explainability Engine\n(reason codes + rejected summary)"]
    REPL["Replay Bundle Builder\n(nsc_decision_digest)"]
    ERR["Error Normalizer\n(error-model mapping)"]

    RPC --> FEAT
    FEAT --> DPDA
    FEAT --> NEUR
    FEAT --> KB
    DPDA --> POL
    NEUR --> POL
    KB --> POL
    POL --> ORCH
    ORCH --> EXPL
    EXPL --> REPL
    REPL --> RPC
    ERR --> RPC
  end

  ORCH --> OPT[GNN Optimizer]
  KB --> OKB[OKB]
  RPC --> OBS[(OTel/Prom/Logs)]
  REPL --> QFS[(QFS)]
```

</details>

---

### A.3 NSC Decision Pipeline (DPDA-authoritative)

![NSC Decision Pipeline](https://i.imgur.com/SGpYUOQ.png)

<details>
<summary>code</summary>

```text
flowchart LR
  In["Inputs\n(AQO digest, topology/telemetry digests,\npolicy digest, deterministic?, seed,\nfeature schema v)"] --> FE["Feature build\n(bounded)"]
  FE --> DP["DPDA symbolic\nallowed_actions + admissibility"]
  FE --> NN["Neural scoring\n(rank allowed actions)"]
  FE --> KB["OKB lookup (optional)\n(candidates + provenance)"]

  DP --> Gate["Policy gate\n(hard constraints)"]
  NN --> Gate
  KB --> Gate

  Gate -->|if enabled| OR["Orchestrate GNN Optimizer\n(advisory)"]
  Gate -->|or skip| Dec["Decision selection\n(deterministic tie-break)"]
  OR --> Dec

  Dec --> Expl["Explainability\n(selected + rejected summary)"]
  Expl --> Dig["nsc_decision_digest\n= sha256(inputs + outputs)"]
  Dig --> Out["Outputs\n(recommendation + reason codes\n+ explain ref + replay bundle ref)"]
```

</details>

---

### A.4 DPDA + Neural Scoring Loop (action-selection)

![DPDA + Neural Scoring Loop](https://i.imgur.com/ZsPxOT3.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant Caller as Compiler/Kernel/HWE
  participant NSC as NSC
  participant DPDA as DPDA (symbolic authority)
  participant Model as Neural Scorer

  Caller->>NSC: Score/Select request (deterministic?, seed)
  NSC->>DPDA: allowed_actions(state, context)
  DPDA-->>NSC: allowed_actions (bounded set)
  NSC->>Model: score(allowed_actions, context, seed)
  Model-->>NSC: scores + confidence
  NSC->>DPDA: apply(selected_action) for legality
  DPDA-->>NSC: ok + state update (+ emitted hints)
  NSC-->>Caller: ranked recommendation + reason codes + confidence + digest
```

</details>

---

### A.5 Sequence — Kernel asks NSC for backend mapping (advisory)

![Kernel asks NSC for backend mapping](https://i.imgur.com/NF9Sdel.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant K as Kernel/QRTX
  participant NSC as NSC
  participant HWE as HWE
  participant DM as Driver Manager
  participant QFS as QFS

  K->>DM: GetDeviceStatus / ListDevices (snapshots)
  DM-->>K: topology/capability/health (bounded)
  K->>HWE: PlanExecution(context)
  HWE->>NSC: RecommendBackendMapping(context_digest,\ndeterministic?, seed)
  NSC-->>HWE: recommended backend(s) + reason codes + digest
  HWE->>QFS: persist qfs://jobs/<job_id>/nsc/decision.json\n+ explain.json + replay_bundle.json
  QFS-->>HWE: refs
  HWE-->>K: ExecutionDecision (selected backend + refs)
```

</details>

---

### A.6 Sequence — Compiler uses NSC for optimization strategy (advisory)

![Compiler uses NSC for optimization strategy](https://i.imgur.com/OlqycTz.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant C as Compiler (Neuro-DPDA)
  participant NSC as NSC
  participant OKB as OKB (optional)
  participant QFS as QFS

  C->>NSC: SelectOptimizationStrategy(\nsemantic_hash, aqo_digest,\npolicy_digest, deterministic?, seed)
  opt optional OKB
    NSC->>OKB: RetrieveOptimizationCandidates(signature,\ndeterministic?, seed)
    OKB-->>NSC: candidates + provenance refs
  end
  NSC-->>C: ranked strategy + admissibility notes\n+ explain ref + digest
  C->>QFS: persist job-scoped NSC decision artifacts\n(qfs://jobs/<job_id>/nsc/*)
  QFS-->>C: refs
```

</details>

---

### A.7 Sequence — NSC orchestrates GNN Optimizer (validated advisory)

![NSC orchestrates GNN Optimizer](https://i.imgur.com/pMuvYXk.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
    autonumber

    participant NSC as NSC
    participant Optimizer as GNN Optimizer
    participant DM as Driver Manager
    participant QFS as QFS

    NSC->>DM: GetDeviceStatus (topology+calibration digests)
    DM-->>NSC: bounded snapshots/digests

    NSC->>Optimizer: OptimizeCircuit(AQO digest/ref, topology digest/ref, policy, deterministic?, seed)

    Optimizer-->>NSC: placement/routing + confidence + optimizer_digest + fallback_used?

    NSC->>NSC: symbolic validation + policy gate

    alt accepted
        NSC->>QFS: persist qfs://jobs/<job_id>/nsc/ + optimizer refs (if used)
        NSC-->>Optimizer: (optional) Publish feedback hook
    else rejected
        NSC-->>NSC: emit fallback marker (reason)
    end
```

</details>

---

### A.8 Fallback Chain (mandatory)

![Fallback Chain](https://i.imgur.com/1hNr9mf.png)

<details>
<summary>code</summary>

```text
flowchart TB
  A["NSC advisory decision\n(neural+okb+gnn)"] -->|timeout / low confidence / untrusted / policy deny| B["DPDA symbolic-only\n(deterministic)"]
  B -->|insufficient| C["Deterministic heuristic\n(no ML)"]
  C -->|insufficient| D["Compiler baseline\n(no NSC influence)"]
  D --> E["Runtime baseline execution"]
```

</details>

---

### A.9 Trust Boundary (NSC never blocks baseline)

![Trust Boundary](https://i.imgur.com/2W2gSRu.png)

<details>
<summary>code</summary>

```text
flowchart LR
    subgraph Trusted["Trusted zone (internal mesh, mTLS)"]
        NSC[NSC] --> OPT[GNN Optimizer]
        NSC --> OKB["OKB (optional)"]
        NSC --> QFS[(QFS)]
    end

    subgraph Authority["Authority boundaries (hard)"]
        Comp["Compiler validation<br/>(AST-only, deterministic)"]
        Kern["Kernel/HWE lifecycle authority"]
        Policy["Policy enforcement<br/>(hard constraints)"]
    end

    NSC -. "advisory only" .-> Comp
    NSC -. "advisory only" .-> Kern
    NSC -. "bounded by" .-> Policy

    Note["If NSC unavailable/untrusted:<br/>fall back deterministically.<br/>No hard dependency."]
    Note -.-> NSC
	style Trusted fill:#FFFFFF
	style Authority fill:#FFFFFF
```

</details>


---

### A.10 NSC Job-Scoped QFS Layout (when NSC influences a job)

![NSC Job-Scoped QFS Layout](https://i.imgur.com/1F53uJZ.png)

<details>
<summary>code</summary>

```text
flowchart TB
  root["qfs://jobs/<job_id>/nsc/"] --> dec["decision.json\n(selected action + reason codes)"]
  root --> exp["explain.json\n(bounded)"]
  root --> rep["replay_bundle.json\n(inputs+outputs+digests)"]
  root --> inD["inputs_digest.txt"]
  root --> outD["outputs_digest.txt"]

  dec --> optRefs["optional refs:\nqfs://jobs/<job_id>/optimizer/*\nqfs://jobs/<job_id>/kb/*"]
```

</details>

---

### A.11 NSC Decision Lifecycle State Machine

![NSC Decision Lifecycle State Machine](https://i.imgur.com/riioe7n.png)

<details>
<summary>code</summary>

```text
stateDiagram-v2
  [*] --> Proposed: request received
  Proposed --> Validated: DPDA admissible + policy ok
  Proposed --> Rejected: DPDA reject / policy deny
  Validated --> Enriched: optional OKB/GNN consulted
  Enriched --> Finalized: decision selected + digest computed
  Finalized --> Persisted: artifacts written to QFS
  Persisted --> Verified: replay check passed (optional/CI)
  Persisted --> Diverged: replay mismatch detected
  Rejected --> [*]
  Verified --> [*]
  Diverged --> [*]
```

</details>


---

### A.12 Observability Span Topology (recommended)

![Observability Span Topology](https://i.imgur.com/nP9Maxm.png)

<details>
<summary>code</summary>

```text
flowchart TB
  Req["nsc.request (root span)"] --> Feat["nsc.feature_build"]
  Req --> Dpda["nsc.dpda_allowed_actions"]
  Req --> Neural["nsc.neural_score"]
  Req --> Okb["nsc.okb_lookup (optional)"]
  Req --> Gnn["nsc.gnn_orchestrate (optional)"]
  Req --> Gate["nsc.policy_gate"]
  Req --> Expl["nsc.explainability"]
  Req --> Replay["nsc.replay_bundle_write"]
```

</details>
