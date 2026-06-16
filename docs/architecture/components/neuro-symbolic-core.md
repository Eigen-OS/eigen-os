# Neuro-Symbolic Core (NSC)
- **Contract version:** `1.0.0`
- **Phase:** Phase 1+ / Post-MVP strategic runtime capability
- **Status:** Target architecture contract with documented implemented prerequisites; **no standalone NSC service is currently active in the production execution path**
- **Applies to:** `src/services/neuro-symbolic-service/` (deployable internal service), Compiler (Neuro-DPDA path), Kernel/QRTX, HWE, GNN Optimizer, Knowledge Base / OKB, Driver Manager, QFS lineage layer, Telemetry exporters

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

**Implementation note:** the repository’s deployable NSC boundary is the internal `src/services/neuro-symbolic-service/` package. Compiler-side use remains advisory-only and must not expose a public ingress path.

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
- runtime tracing and structured logging exist,
- internal model registry activation uses signed artifact verification and frozen policy snapshot binding.

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
- semantic stack discipline,
- admissibility gating,
- bounded replay evidence generation,
- fallback-safe rejection on ambiguity or policy mismatch.

---

### 7.2 Neural Scoring Subsystem

#### Responsibility

Provide bounded advisory scoring for compiler/runtime optimization proposals.

#### Requirements

- scoring must be bounded and reproducible,
- all model use must be tied to an immutable model/version contract,
- no request-time model discovery from untrusted sources,
- model outputs are advisory only.

---

### 7.3 Knowledge Retrieval Subsystem

#### Responsibility

Lookup reusable evidence from OKB / KB.

#### Requirements

- retrieval must be bounded,
- evidence references must be recorded in audit logs,
- retrieval failures fall back to deterministic baseline,
- live policy lookups are prohibited on the request path.

---

### 7.4 Explainability and Replay Subsystem

#### Responsibility

Capture stable decision artifacts for audit and replay.

#### Requirements

- include reasoning summaries,
- include feature provenance,
- include model/version references,
- include policy snapshot version,
- include reproducibility digest,
- support offline reconstruction.

---

### 7.5 Internal model registry and signed loading contract

#### Responsibility

Publish, verify, activate, and roll back internal Neuro-DPDA model artifacts inside the deployable NSC service boundary.

#### Requirements

- model artifacts MUST have stable version identifiers, digests, and signature metadata,
- model activation MUST be bound to the frozen policy snapshot version and internal service identity,
- loading MUST verify the artifact digest before activation,
- loading MUST verify the registry signature before activation,
- missing artifact, missing policy snapshot, bad signature, or identity mismatch MUST fail closed,
- rollback MUST be auditable and MUST preserve deterministic baseline behavior when activation cannot be verified.

---

## 8. Integration Boundaries

### 8.1 Compiler integration

Compiler MAY call NSC for bounded advisory scoring only.

Compiler MUST:

- preserve deterministic baseline semantics,
- keep NSC optional,
- capture frozen policy snapshot,
- degrade safely when NSC is unavailable.

### 8.2 Kernel/QRTX integration

Kernel/QRTX MAY call NSC for routing or optimization advice where appropriate.

Kernel/QRTX remains authoritative for execution and lifecycle decisions.

### 8.3 Public ingress restriction

NSC MUST NOT be exposed through public ingress.

Requests from public API boundaries must never reach NSC directly.

---

### 8.4 Mandatory preprocessing redaction layer

All data that can enter model loading, knowledge retrieval, decision logging, or replay packaging paths MUST pass through a mandatory preprocessing redaction layer before persistence or external emission.

---

### 8.5 Deployment shape

The implementation boundary for NSC is a **standalone internal service** packaged as `src/services/neuro-symbolic-service/`.

This service boundary is intentionally separate from `src/services/system-api/`:

- `system-api` remains the sole public ingress.
- `eigen-kernel` / QRTX is the primary runtime caller.
- `eigen-compiler` may call the service only through the bounded advisory scoring path.
- Internal offline workflows such as model loading, dataset ingestion, and privacy-governed training remain inside the same internal service boundary and must not be exposed through public ingress.

---

### 8.6 Offline training dataset ingestion

The internal Neuro-Symbolic Service MAY expose a CLI-only ingestion path for KB-backed training datasets.

That workflow MUST:

- remain inside `src/services/neuro-symbolic-service/`,
- require a stable manifest with dataset version and record schema version,
- validate ownership, provenance, redaction, approval, replay identifiers, and policy snapshot evidence,
- fail closed on missing or mismatched integrity digests,
- preserve replay-safe dataset records for later training runs,
- avoid public ingress and live model discovery on the request path.

---

### 8.7 Privacy-safe production-trace retraining

Production execution traces MAY feed the training corpus only after an offline governance bundle has been selected and approved.

The bundle MUST be tenant-scoped and MUST include:

- tenant/project binding,
- record-level provenance digests,
- replay identifiers,
- explicit selection metadata,
- explicit approval metadata,
- redaction validation evidence,
- policy snapshot version.

Cross-tenant mixing is prohibited. Any missing or mismatched provenance, approval, replay, or redaction evidence MUST fail closed before a dataset manifest is emitted.
