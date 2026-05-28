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
- reasoning metadata (bounded),
- fallback eligibility,
- reproducibility hash (digest),
- policy context summary (bounded).

Opaque decisions are prohibited.

---

### 6.4 Determinism and Replay

NSC MUST support deterministic mode.

When `deterministic=true`, outputs MUST be a pure function of canonical inputs + seed and MUST be replayable byte-for-byte at the decision artifact level (canonical serialization).

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
- tenant context (NOT as metric label; redacted/hashed where applicable),
- feature schema version,
- timeout budget,
- replay identifier (if present).

---

### 8.4 Required response metadata

All responses MUST include:

- `confidence` (bounded numeric),
- `provenance` (stable reference or “symbolic-only”),
- `model_version` (or “none”),
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

#### Defined but not implemented

- DPDA semantic engine runtime,
- neural inference runtime,
- GNN optimizer runtime,
- `NeuroSymbolicService` API,
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
