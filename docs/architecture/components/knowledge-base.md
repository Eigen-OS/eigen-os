# Knowledge Base

**Contract version:** 1.0.0
**Status:** Stable target-architecture contract with documented implemented baseline
**Last synchronized:** 2026-05-25
**Applies to:** KnowledgeBaseService (public record store), (future) Optimization Knowledge Base (OKB) services, Compiler (Neuro-DPDA path), GNN Optimizer, HWE, Kernel/QRTX, QFS lineage layer, Telemetry exporters

> **Important scope clarification (to avoid contract ambiguity):**
> 
> Eigen OS currently uses the name **KnowledgeBaseService** for a **public record store** API (CRUD/query over KB records).
> This document also specifies the **Optimization Knowledge Base (OKB):** a future, deterministic optimization-memory subsystem used by compiler/runtime/optimizers.
> The OKB is not a generic vector DB and is not yet on the production critical path by default.

---

## 0. Contract Marker (Observability)

All Knowledge Base telemetry exporters MUST expose:

```text
eigen_kb_contract_info{version="1.0.0"} 1
```

---

## 1. Purpose

The Knowledge Base (KB) is the long-term adaptive optimization and reusable intelligence subsystem of Eigen OS.

Its purpose is to provide:

- deterministic reuse of previously validated optimization knowledge,
- semantic pattern matching for compilation/runtime optimization,
- feedback-driven improvement loops,
- explainable optimization provenance,
- reusable execution intelligence across heterogeneous hardware.

The Knowledge Base is not:

- a generic vector database,
- a raw telemetry archive,
- an opaque online-learning system in the request path.

It is a **structured, versioned, deterministic optimization memory system** integrated with:

- the Neuro-DPDA compiler path,
- the GNN hardware optimizer,
- runtime execution telemetry,
- scheduling and adaptation layers (HWE),
- QFS artifact persistence.

---

## 2. Versioning and Compatibility (SemVer)

This contract follows SemVer.

#### MAJOR

Breaking changes:

- record schema changes that are not backward compatible,
- removal/rename of stable APIs,
- incompatible retrieval semantics (deterministic-mode changes),
- incompatible reason-code changes.

#### MINOR

Backward-compatible additions:

- additive fields (optional),
- new query filters,
- new reason codes,
- additional telemetry dimensions with bounded cardinality.

#### PATCH

Non-semantic corrections:

- documentation clarifications,
- exporter fixes,
- alert/dashboard tuning.

---

## 3. Architectural Position

### 3.1 Layer Placement

The Knowledge Base belongs to the **Runtime Intelligence** layer of Eigen OS.

Logical placement (target):

```text
Client SDKs
  ↓
System API
  ↓
Compiler (Neuro-DPDA path)
  ↓
Knowledge Base (OKB)
  ↓
GNN Optimizer / HWE
  ↓
Driver Manager
  ↓
Quantum Hardware
```

---

### 3.2 Responsibility Separation

| **Component** | **Responsibility** |
|---|---|
| Compiler | Deterministic AST → AQO transformation |
| Neuro-DPDA | Semantic optimization and pattern generation (advisory) |
| Knowledge Base (OKB) | Persistent reusable optimization knowledge and deterministic reuse |
| GNN Optimizer | Hardware-aware placement/routing (advisory, validated) |
| HWE | Runtime adaptation/orchestration and replay/audit |
| Driver Manager | Backend abstraction and execution transport |

The Knowledge Base MUST NOT:

- directly execute user workloads,
- replace deterministic compiler behavior,
- mutate AQO semantics independently,
- perform opaque online learning in the request path,
- override explicit runtime policies.

---

## 4. Scope

This contract governs:

1. **Public KnowledgeBaseService (Implemented Baseline)**
    - structured records (CRUD/query),
    - stable API semantics for UpsertRecord, BatchUpsertRecords, QueryRecords, GetRecord.
2. **Optimization Knowledge Base (OKB) (Target, Not Yet Fully Implemented)**
    - deterministic optimization memory,
    - semantic signatures and candidate retrieval,
    - provenance/explainability,
    - replay-safe selection,
    - feedback ingestion.

This contract does not define:

- model training pipelines,
- raw telemetry storage schemas,
- end-user vector similarity search semantics.

---

## 5. Source of Truth

Normative repository artifacts (paths are contractual anchors):

- Public API protobufs: `docs/reference/api/grpc-public.md` (and corresponding `proto/` sources)
- Error model and mapping:
    - `docs/reference/error-model.md`
    - `docs/reference/error-mapping.md`
- QFS contracts and layout: `docs/reference/qfs-layout.md` (or equivalent QFS contract doc)
- Observability contracts (related):
    - `docs/reference/intelligent-runtime-observability-contract.md`
    - `docs/reference/orchestration-observability-contract.md`

Operational assets (when OKB becomes active):

- Alerts: `monitoring/metrics/prometheus/knowledge-base-alerts.yaml`
- Dashboard: `monitoring/dashboards/knowledge_base_dashboard.json`
- Tests: `monitoring/metrics/tests/test_kb_observability.py`
- Runbook: `docs/howto/knowledge-base-runbook.md`

(If some paths don’t exist yet, they are required deliverables for closure; see `§18`.)

---

## 6. Current Implemented Baseline

### 6.1 Implemented Today (Public KB Records)

Implemented APIs (baseline, already present in architecture contracts):

- `UpsertRecord`
- `BatchUpsertRecords`
- `QueryRecords`
- `GetRecord`

These operations provide a stable, queryable record store used by tooling and future intelligence layers.

---

### 6.2 Not Implemented Yet (OKB on Critical Path)

Not implemented as production components:

- OKB candidate retrieval engine for compiler/runtime optimization
- deterministic ranking/selection with replay bundles
- optimization artifact store with compatibility windows
- feedback ingestion tied to optimization reuse
- OKB explainability and replay-selection APIs
- OKB-aware compiler/runtime integration (beyond metadata scaffolding)

Current runtime operates in:

```text
KB records: enabled (public service)
OKB adaptive optimization reuse: disabled baseline mode
```

---

## 7. Strategic Role in Eigen OS

The OKB is the persistent intelligence layer connecting:

- Neuro-DPDA semantic compilation,
- runtime execution feedback,
- GNN hardware optimization,
- adaptive orchestration (HWE),
- historical optimization outcomes.

The objective is improved optimization quality while preserving:

- determinism,
- auditability,
- explainability,
- reproducibility.

---

## 8. Core Responsibilities (OKB Target)

### 8.1 Optimization Knowledge Storage

OKB SHALL store reusable optimization artifacts including:

- compilation patterns,
- AQO transformation recipes,
- routing strategies,
- backend-specific optimizations,
- topology-aware mappings,
- execution heuristics,
- validated optimization templates.

---

### 8.2 Semantic Pattern Matching

OKB SHALL support retrieval keyed by bounded, deterministic signatures:

- program structure signature,
- circuit topology signature,
- optimization objective class,
- backend profile,
- execution constraints,
- workload category,
- compiler metadata versions.

---

### 8.3 Feedback Learning Loop (Audited, Not Opaque Online Learning)

OKB SHALL ingest auditable feedback signals:

- fidelity summaries,
- latency summaries,
- routing quality summaries,
- adaptation outcomes,
- optimizer success/failure signals,
- replay validation outcomes.

Feedback MUST be versioned and traceable to job-scoped artifacts.

---

### 8.4 Explainability

Every optimization candidate returned by OKB MUST include:

- provenance (source references),
- compatibility metadata (versions + windows),
- confidence metadata (bounded),
- deterministic identifiers,
- an explanation payload or reference.

---

### 8.5 Deterministic Reuse

In deterministic mode, OKB retrieval MUST be reproducible:

- stable lookup semantics,
- version-pinned artifacts,
- replay-safe selection outputs,
- deterministic tie-breaking rules.

---

## 9. Determinism and Replay Contract (OKB)

### 9.1 Determinism Modes

OKB MUST support:

- `deterministic=true`: retrieval + ranking + selection MUST be replay-stable
- `deterministic=false`: adaptive ranking MAY be used but MUST remain auditable

---

### 9.2 Required Deterministic Inputs

When `deterministic=true`, OKB decisions MUST be a pure function of:

- `semantic_hash`
- `aqo_hash`
- `backend_profile_id`
- `topology_snapshot_digest` (bounded)
- `policy_envelope_digest`
- `kb_schema_version`, `compiler_version`, `optimizer_version` (if relevant)
- `seed` (REQUIRED when deterministic=true)

---

### 9.3 Output Digest

OKB MUST produce:

- `okb_selection_digest = sha256(canonical_inputs + canonical_outputs)`

This digest MUST be persisted in job-scoped QFS artifacts when OKB affects execution.

---

## 10. Integration with Neuro-DPDA

### 10.1 Compiler → OKB Flow

Compiler SHOULD provide:

- structural signatures,
- semantic fingerprints,
- optimization context,
- target constraints,
- determinism policy,
- optimization outcomes.

---

### 10.2 OKB → Compiler Flow

OKB SHOULD provide:

- reusable transformations,
- optimization candidates,
- historical best-known mappings,
- semantic equivalence references,
- compatibility constraints,
- explainability metadata.

OKB MUST NOT inject transformations that bypass compiler validation.

---

## 11. Integration with GNN Optimizer and HWE

OKB SHOULD persist and retrieve:

- validated routing outcomes,
- topology-specific optimization histories,
- placement quality metrics,
- degradation patterns,
- optimizer confidence histories.

Safety constraints:

- OKB MUST NOT override deterministic fallback policy,
- MUST NOT bypass policy validation,
- MUST NOT inject unverifiable outputs,
- MUST NOT mutate results post-validation.

---

## 12. Interfaces

### 12.1 Public KnowledgeBaseService (Implemented Baseline)

Stable public RPC surface (records):

- `UpsertRecord`
- `BatchUpsertRecords`
- `QueryRecords`
- `GetRecord`

These APIs are part of the stable client-facing surface and MUST remain compatible within MAJOR versions.

---

### 12.2 Target OKB Service Contract (Internal)

A dedicated internal service MAY be introduced to avoid mixing “records KB” with “optimization KB” concerns.

#### Proposed internal service name

```text
eigen.internal.v1.OptimizationKnowledgeBaseService
```

#### Required APIs (Target)

Retrieval:

- `FindOptimizationCandidates`
- `GetOptimizationArtifact`
- `SearchExecutionPatterns`

Ingestion:

- `StoreOptimizationOutcome`
- `StoreExecutionFeedback`
- `StoreTopologyMetrics`

Explainability / replay:

- `ExplainOptimizationDecision`
- `ReplayOptimizationSelection`

---

## 13. Input and Output Contracts (OKB Target)

### 13.1 Inputs

#### Program Signature (bounded, deterministic)

- `source_hash`
- `semantic_hash`
- `aqo_hash`
- `compiler_version`

#### Runtime Context

- `backend_profile_id`
- `topology_snapshot_digest`
- `optimization_goal` (enum)
- `determinism_mode`
- `execution_constraints_digest`

#### Execution Feedback

- `fidelity_summary`
- `latency_summary`
- `routing_quality_summary`
- `adaptation_events_summary`
- `replay_validation_result`

---

### 13.2 Outputs

#### OptimizationCandidate

- `artifact_id`
- `optimization_type` (enum)
- `transformation_ref`
- `confidence` (bounded numeric)
- `provenance_ref`
- `compatibility_window`
- `deterministic_digest`

#### Explainability payload (bounded)

- `candidate_source`
- `selection_reason` (stable code)
- `rejected_candidates_summary`
- `historical_performance_summary`
- `optimizer_origin` (enum)

---

## 14. State and Storage

### 14.1 Public KB Records

Storage model is implementation-defined but MUST preserve:

- stable record IDs,
- schema versioning,
- deterministic query semantics where declared.

---

### 14.2 OKB Target Storage Architecture

OKB SHALL support:

- structured metadata storage (index),
- durable artifact storage,
- replay-safe history retention,
- immutable provenance records.

Proposed layout:

```text
qfs://knowledge-base/
  artifacts/
  signatures/
  topology/
  execution-feedback/
  optimizer-history/
  replay/
```

#### Job-scoped linkage (required when OKB affects a job):

```text
qfs://jobs/<job_id>/kb/
  selection.json
  candidates.json
  explain.json
  replay_bundle.json
```

---

### 14.3 Versioning Rules

All entries MUST include:

- schema version,
- compiler version,
- optimizer version (if relevant),
- hardware profile version,
- compatibility window.

---

## 15. Error Semantics (Aligned with error-model.md)

### 15.1 Canonical gRPC Status Mapping

- invalid request / malformed signature → `INVALID_ARGUMENT` (+ `BadRequest`)
- record/artifact missing → `NOT_FOUND`
- state-dependent restriction (policy forbids reuse) → `FAILED_PRECONDITION`
- storage backend unavailable → `UNAVAILABLE` (+ `RetryInfo`)
- quota/capacity exceeded → `RESOURCE_EXHAUSTED` (+ `RetryInfo`)
- internal invariant violation → `INTERNAL`
- unsupported feature path → `UNIMPLEMENTED`

---

### 15.2 Stable Reason Codes

For public KB record API (existing taxonomy baseline from architecture contracts):

- `KB_INVALID_ARGUMENT`
- `KB_NOT_FOUND`
- `KB_INDEX_UNAVAILABLE`
- `KB_RATE_LIMITED`
- `KB_INTERNAL`

For OKB (target), stable `EIGEN_OKB_*` reasons SHOULD be used via `google.rpc.ErrorInfo.reason`, e.g.:

- `EIGEN_OKB_LOOKUP_MISS`
- `EIGEN_OKB_LOW_CONFIDENCE`
- `EIGEN_OKB_ARTIFACT_CORRUPT`
- `EIGEN_OKB_SCHEMA_INCOMPATIBLE`
- `EIGEN_OKB_KNOWLEDGE_STALE`
- `EIGEN_OKB_REPLAY_MISMATCH`
- `EIGEN_OKB_PROVENANCE_INVALID`
- `EIGEN_OKB_STORAGE_UNAVAILABLE`

---

### 15.3 Mandatory Fallback Policy

When OKB retrieval fails, the system MUST:

- fall back to deterministic baseline execution,
- disable adaptive reuse for that decision point,
- emit explicit observability markers,
- preserve replayability.

OKB MUST NEVER be a hard dependency for baseline execution.

---

## 16. Observability

### 16.1 Design Principles

- bounded cardinality
- deterministic semantics
- no user/tenant IDs as labels by default
- no embedding of freeform text in labels

---

### 16.2 Required Metrics (OKB Target + Public KB Where Applicable)

All are Prometheus-compatible and MUST include # TYPE.

- `eigen_kb_queries_total{kind}` (counter)
- `eigen_kb_hits_total{kind}` (counter)
- `eigen_kb_misses_total{kind}` (counter)
- `eigen_kb_lookup_duration_seconds{kind}` (histogram)
- `eigen_kb_reuse_improvement_total{metric}` (counter or gauge per contract; must be bounded)
- `eigen_kb_fallbacks_total`{reason} (counter)
- `eigen_kb_replay_failures_total` (counter)

Where:

- `kind` is a bounded enum (e.g. `records`, `okb_candidates`, `okb_artifact`)
- `reason` is a stable bounded taxonomy

---

### 16.3 Tracing

KB/OKB SHOULD emit spans for:

- retrieval,
- ranking,
- artifact validation,
- replay validation,
- feedback ingestion.

Trace correlation fields in logs/spans (NOT metric labels):

- `trace_id`
- `job_id` (when relevant)
- `artifact_id` (when relevant)
- `optimizer_id` (when relevant)

---

### 16.4 Auditability

Every OKB-influenced decision MUST be auditable via durable artifacts.

Minimum audit fields:

- selected candidate (or “none”)
- rejected candidates summary
- ranking reason code
- confidence (bounded)
- provenance ref
- compatibility constraints
- selection digest

---

## 17. Security and Trust

### 17.1 Integrity Requirements

All KB/OKB artifacts MUST support:

- checksums,
- provenance chains,
- immutable references,
- signature validation (where applicable).

---

### 17.2 Trust Policy

Untrusted optimization artifacts MUST be rejected.

OKB MUST validate:

- artifact origin,
- schema compatibility,
- replay capability in deterministic mode,
- policy compliance.

---

### 17.3 Data Isolation

Tenant-sensitive metadata MUST remain isolated.

Cross-tenant reuse MUST require:

- explicit policy enablement,
- anonymization,
- compatibility validation.

---

## 18. CI / Conformance Requirements (Target)

CI MUST validate (once OKB is enabled in any environment):

1. deterministic retrieval under `deterministic=true` + fixed seed
2. stable reason codes
3. artifact integrity verification (checksums)
4. fallback behavior correctness (no hard dependency)
5. contract marker metric presence
6. label boundedness
7. dashboard/alert queries reference valid metrics (when assets exist)

Required golden tests (target):

- lookup miss
- low confidence
- corrupt artifact
- schema incompatible
- storage unavailable
- replay mismatch
- fallback correctness

---

## 19. Architectural Invariants

- Determinism: Knowledge reuse preserves deterministic replay semantics when requested.
- Explainability: Every optimization decision is explainable and auditable.
- Safety: No artifact bypasses policy validation or compiler/runtime safety checks.
- Compatibility: All artifacts and schemas are versioned and evolve under SemVer.
- Isolation: KB/OKB must not be a mandatory dependency for baseline execution.

---

## Strategic Direction

The Knowledge Base is Eigen OS’s persistent intelligence layer: reusable optimization memory connecting Neuro-DPDA compilation, GNN hardware optimization, HWE adaptation, and deterministic replay/audit infrastructure—without compromising baseline safety or determinism.
