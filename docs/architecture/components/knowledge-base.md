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
- QFS contracts and layout: `docs/reference/formats/qfs-layout.md` (or equivalent QFS contract doc)
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
- `AppendDecisionLog`
- `QueryDecisionLogs`

These operations provide a stable, queryable record store used by tooling and future intelligence layers. The implemented public baseline persists provenance metadata, replay metadata, and tenant-scoped decision lineage with deterministic pagination semantics.

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
- deterministic query semantics where declared,
- replay-safe cursor behavior for repeatable queries,
- persisted provenance and replay bundle references,
- anonymized storage of privacy-sensitive attributes when exposed at the public boundary.

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

---

## Appendix A. Diagrams (normative)

### A.1 C4 — Service Context (Public KB Records vs OKB)

![Service Context](https://i.imgur.com/zDXMZbN.png)

<details>
<summary>code</summary>

```text
flowchart LR
    Client[Client SDKs / CLI] -->|"public gRPC"| API[System API]

    subgraph Runtime["Eigen OS Runtime"]
        API -->|"public records CRUD/query"| KB["KnowledgeBaseService<br/>(public record store)"]
        
        C["Compiler (Neuro-DPDA)"] -->|"optional OKB retrieval"| OKB["Optimization Knowledge Base (OKB)<br/>(internal service)"]
        
        OPT[GNN Optimizer] -->|"optional OKB lookup"| OKB
        HWE[HWE] -->|"optional OKB lookup"| OKB
        K[Kernel/QRTX] -->|"job lineage + feedback refs"| OKB

        KB --> QFS[(QFS)]
        OKB --> QFS
        C --> QFS
        OPT --> QFS
        HWE --> QFS
    end

    KB --> OBS[Observability]
    OKB --> OBS
	style Runtime fill:#FFFFFF
```

</details>

---

### A.2 C4 — Component Diagram (Inside OKB)

![Component Diagram](https://i.imgur.com/VlqBD0E.png)

<details>
<summary>code</summary>

```text
flowchart TB
  subgraph OKB["Optimization Knowledge Base (OKB) — internal"]
    API["Internal RPC\nFindOptimizationCandidates / GetOptimizationArtifact\nStoreExecutionFeedback / ReplayOptimizationSelection"]
    Sig["Signature Builder\n(semantic_hash/aqo_hash/topology_digest/policy_digest)"]
    Index["Metadata Index\n(deterministic lookup, version windows)"]
    Rank["Ranker\n(deterministic mode + seed)\n(policy-aware scoring)"]
    Validate["Artifact Validator\n(checksums, schema, provenance,\ncompatibility window)"]
    Replay["Replay Bundle Builder\n(selection_digest + inputs/outputs)"]
    Store["Artifact Store\n(immutable objects + refs)"]
    Audit["Audit Emitter\n(explain refs + decision summary)"]
    Err["Error Normalizer\n(error-model mapping)"]

    API --> Sig --> Index --> Rank --> Validate --> Replay --> Audit
    Validate --> Store
    Audit --> Store
    Err --> Store
  end

  Store --> QFS[(QFS)]
  API --> OBS[(OTel/Prom/Logs)]
```

</details>

---

### A.3 Deterministic Selection Key + Digest

![Deterministic Selection Key](https://i.imgur.com/GJGKqKB.png)

<details>
<summary>code</summary>

```text
flowchart LR
  Sem["semantic_hash"] --> KEY["okb_selection_key"]
  AQO["aqo_hash"] --> KEY
  BP["backend_profile_id"] --> KEY
  Topo["topology_snapshot_digest"] --> KEY
  Policy["policy_envelope_digest"] --> KEY
  Versions["kb_schema/compiler/optimizer versions"] --> KEY
  Seed["seed (required if deterministic=true)"] --> KEY

  KEY --> Sel["Selection outputs\n(selected candidate, rejected summary, refs)"]
  Sel --> Digest["okb_selection_digest\n= sha256(inputs + outputs)"]
```

</details>

---

### A.4 OKB Retrieval Dataflow (Signatures → Candidates → Selection)

![OKB Retrieval Dataflow](https://i.imgur.com/mldMGdd.png)

<details>
<summary>code</summary>

```text
flowchart LR
  In["Inputs\n(semantic_hash, aqo_hash,\nbackend_profile, topology_digest,\npolicy_digest, deterministic?, seed)"] --> Sig["Build deterministic signature"]
  Sig --> Q["Query index\n(version/compatibility filters)"]
  Q --> Cand["Candidate set\n(bounded list)"]
  Cand --> Val["Validate candidates\n(checksum/provenance/schema/window)"]
  Val --> Rank["Rank (policy-aware)\n deterministic tie-break"]
  Rank --> Out["Selection\n(selected + rejected summary)\n+ okb_selection_digest"]
  Out --> Art["Persist job linkage\nqfs://jobs/<job_id>/kb/* (if used)"]
```

</details>

---

### A.5 Sequence — Compiler uses OKB during compile (advisory)

![Compiler uses OKB during compile](https://i.imgur.com/bwqKUKc.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant C as Compiler (Neuro-DPDA)
  participant OKB as OKB (internal)
  participant QFS as QFS

  C->>OKB: FindOptimizationCandidates(signature,\npolicy, deterministic?, seed)
  OKB->>OKB: deterministic lookup + compatibility filter
  OKB-->>C: candidates (bounded) + explain refs
  C->>C: apply only validated candidates\n(symbolic checks remain authoritative)
  opt persist linkage (if OKB influenced output)
    C->>QFS: write qfs://jobs/<job_id>/kb/selection.json\n+ candidates.json + explain.json + replay_bundle.json
    QFS-->>C: refs
  end
```

</details>

---

### A.6 Sequence — HWE/GNN Optimizer uses OKB for reuse hints

![HWE/GNN Optimizer](https://i.imgur.com/AtXOf5O.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant H as HWE / GNN Optimizer
  participant OKB as OKB (internal)
  participant QFS as QFS

  H->>OKB: FindOptimizationCandidates(signature,\npolicy, deterministic?, seed)
  OKB-->>H: candidates + confidence + provenance refs
  H->>H: validate against policy + symbolic safety
  H->>QFS: persist kb linkage under job scope\n(qfs://jobs/<job_id>/kb/*)
  QFS-->>H: refs
```

</details>

---

### A.7 Sequence — Feedback ingestion (post-execution, audited)

![Feedback ingestion](https://i.imgur.com/HZkEaNY.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant K as Kernel/QRTX
  participant OKB as OKB (internal)
  participant QFS as QFS

  K->>QFS: persist execution results + summaries
  K->>OKB: StoreExecutionFeedback(\njob_id, feedback_summary,\nrefs to results/telemetry,\nreplay_validation_result)
  OKB->>OKB: validate + version + attach provenance
  OKB->>QFS: write qfs://knowledge-base/execution-feedback/*\n(immutable, checksummed)
  QFS-->>OKB: refs
  OKB-->>K: ack + stored refs
```

</details>

---

### A.8 Sequence — ReplayOptimizationSelection (deterministic verification)

![ReplayOptimizationSelection](https://i.imgur.com/6BnuVM6.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant Ops as Operator/CI
  participant OKB as OKB (internal)
  participant QFS as QFS

  Ops->>OKB: ReplayOptimizationSelection(job_id, selection_ref)
  OKB->>QFS: load replay_bundle.json + referenced artifacts
  QFS-->>OKB: bundle + artifacts
  OKB->>OKB: recompute selection under deterministic=true\n(same seed + versions)
  alt match
    OKB-->>Ops: OK (replay verified)
  else mismatch
    OKB-->>Ops: FAILED (EIGEN_OKB_REPLAY_MISMATCH)
  end
```

</details>

---

### A.9 Global OKB Layout in QFS

![Global OKB Layout in QFS](https://i.imgur.com/BS9dpJ9.png)

<details>
<summary>code</summary>

```text
flowchart TB
  root["qfs://knowledge-base/"] --> art["artifacts/\n(transformation refs, templates)"]
  root --> sig["signatures/\n(indexable keys)"]
  root --> topo["topology/\n(bounded snapshots + digests)"]
  root --> fb["execution-feedback/\n(fidelity/latency/routing summaries)"]
  root --> hist["optimizer-history/\n(confidence + outcomes)"]
  root --> rep["replay/\n(selection bundles)"]
```

</details>

---

### A.10 Job-Scoped Linkage when OKB influences a job

![Job-Scoped Linkage when OKB influences a job](https://i.imgur.com/IVXxHtP.png)

<details>
<summary>code</summary>

```text
flowchart TB
  job["qfs://jobs/<job_id>/kb/"] --> sel["selection.json\n(selected candidate + digest)"]
  job --> cand["candidates.json\n(bounded list)"]
  job --> exp["explain.json\n(bounded)"]
  job --> rep["replay_bundle.json\n(inputs+outputs+okb_selection_digest)"]
  sel --> refs["refs to qfs://knowledge-base/artifacts/*"]
```

</details>

---

### A.11 Optimization Artifact Lifecycle State Machine

![Optimization Artifact Lifecycle State Machine](https://i.imgur.com/qWptsw1.png)

<details>
<summary>code</summary>

```text
stateDiagram-v2
  [*] --> Proposed: generated by compiler/optimizer
  Proposed --> Validated: checksum + schema + provenance ok
  Validated --> Active: within compatibility window
  Active --> Deprecated: superseded or confidence decays
  Active --> Stale: topology/calibration drift detected
  Deprecated --> Archived: retained immutable history
  Stale --> Archived
  Validated --> Rejected: policy/provenance invalid
  Rejected --> [*]
  Archived --> [*]
```

</details>


---

### A.12 Trust Boundary (OKB is advisory; never blocks baseline)

![Trust Boundary](https://i.imgur.com/EyR0sMF.png)

<details>
<summary>code</summary>

```text
flowchart LR
    subgraph Trusted["Trusted Zone (Eigen OS internal mesh, mTLS)"]
        C[Compiler] -->|"optional"| OKB[OKB]
        HWE[HWE] -->|"optional"| OKB
        OPT[GNN Optimizer] -->|"optional"| OKB
        OKB --> QFS[(QFS)]
    end

    subgraph Baseline["Baseline Safety Rule"]
        Rule["If OKB unavailable/miss/low confidence:<br/>fall back to deterministic baseline<br/>(compiler/kernel/hwe)"]
    end

    Rule --- C
    Rule --- HWE
    Rule --- OPT

    Note["OKB artifacts must be validated<br/>(checksum/provenance/schema/window)<br/>No secrets in artifacts."]
    Note -.-> OKB
	style Baseline fill:#FFFFFF
	style Trusted fill:#FFFFFF
```

</details>

