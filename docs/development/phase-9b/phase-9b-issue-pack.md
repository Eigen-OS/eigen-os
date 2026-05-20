This document is a ready-to-use set of GitHub issues for the **Phase-9B** stage of the roadmap.

**Context Sources:**
- `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md` (Section: "Stage B — Intelligence closure")
- `docs/development/phase-9b/phase-9b-execution-plan.md`
- `docs/development/post-mvp-open-source-roadmap.md` (phase progression context)
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md` (normative versioning constraints)
- `rfcs/0047-phase9b-intelligence-closure-contract-v1.md` (Stage-B normative contract)

---

## Versioning & Compatibility Rules (Mandatory for every Phase-9B issue)

> Include this block in the description of every issue (as "Definition of Done / Constraints").

1. **SemVer is mandatory for stable contracts** across API, protobuf schemas, adapter payloads, and compatibility matrix artifacts.
2. **Breaking behavior requires `MAJOR`** and explicit migration notes.
3. **Backward-compatible additions use `MINOR`** with deterministic defaults and feature flags where relevant.
4. **`PATCH` is non-semantic only** (bug fixes, docs corrections, observability tuning).
5. **Deprecations require a fixed support window:** deprecated interfaces remain supported for 2 minor releases or 90 days, whichever is longer.
6. **Compatibility matrix updates are versioned artifacts** and must be fixture-tested.
7. **CI must fail closed** on undocumented contract drift and conformance regressions.

---

## Milestone

- **Milestone:** `Phase-9B Intelligence Closure`
- **Suggested labels:** `phase-9b`, `kb`, `compiler`, `gnn`, `continuous-learning`, `mlops`, `conformance`

---

## Priority and ownership proposal (requires maintainer confirmation)

| Issue | Priority | Proposed owner group |
| --- | --- | --- |
| P9B-01 KB Immutability + Anonymization + Index Profile Hardening | P0 | Data Platform + Security |
| P9B-02 Pattern Miner Deterministic Service + Recommendation API | P0 | Compiler/ML Platform |
| P9B-03 DPDA Context Injection + Deterministic Recommendation Fallback | P0 | Compiler Runtime |
| P9B-04 GNN Quality Signal Contract + Non-Regression Gates | P0 | Optimizer/Runtime Intelligence |
| P9B-05 Continuous Learning Reproducible Retrain + Model Registry Digests | P0 | MLOps + Platform |
| P9B-06 Canary Rollout + Auto-Rollback on Regression | P0 | MLOps + SRE |
| P9B-07 Phase-9B Evidence Bundle + Docs/RFC Sync | P1 | Architecture/Governance + Tech Writing |

---

## Issues

### P9B-01 — KB Immutability + Anonymization + Index Profile Hardening

**Type:** Data Fabric / Security / Performance  
**Labels:** `phase-9b`, `kb`, `security`, `performance`

**Problem** Stage-B learning cannot be trusted while KB records can be mutated post-ingest or user identity handling remains weakly constrained.

**Scope**
- Enforce append-only immutable records for Circuit/Pattern/Task objects.
- Harden user-id anonymization (salt rotation policy, reversible mapping prohibition in runtime path).
- Publish index profile and latency SLO checks for structural and vector search.

**Acceptance Criteria**
- Post-ingest record mutation is blocked and auditable.
- User identity exposure risk is reduced to documented acceptable level with security sign-off.
- Query latency SLO evidence is attached and required in Phase-9B gates.

**RFC link**
- `rfcs/0034-phase8a-knowledge-base-api-contract-v1.md`
- `rfcs/0047-phase9b-intelligence-closure-contract-v1.md`

---

### P9B-02 — Pattern Miner Deterministic Service + Recommendation API

**Type:** Runtime Intelligence Service  
**Labels:** `phase-9b`, `kb`, `compiler`, `determinism`

**Problem** Pattern extraction exists conceptually but lacks deterministic service behavior and a stable recommendation contract for compiler consumers.

**Scope**
- Define deterministic Pattern Miner cadence and idempotent ingest behavior.
- Implement recommendation API payload contract and provenance fields.
- Add fixture tests proving deterministic outputs on fixed datasets.

**Acceptance Criteria**
- Pattern Miner produces deterministic outputs for identical input snapshots.
- Recommendation payload contract is versioned and fixture-tested.
- Provenance links (pattern -> source records) are queryable and documented.

**RFC link**
- `rfcs/0047-phase9b-intelligence-closure-contract-v1.md`

---

### P9B-03 — DPDA Context Injection + Deterministic Recommendation Fallback

**Type:** Compiler Contract / Reliability  
**Labels:** `phase-9b`, `compiler`, `reliability`, `conformance`

**Problem** DPDA consumption of KB recommendations is not yet strictly governed, risking non-deterministic compile behavior.

**Scope**
- Wire compiler-side context injection from recommendation API.
- Define fallback decision policy for missing/low-confidence recommendations.
- Add deterministic compile fixtures covering no-context, stale-context, and conflict-context scenarios.

**Acceptance Criteria**
- Compile output remains deterministic for fixed seed and fixed recommendation snapshot.
- Fallback path is stable, observable, and fails closed on malformed context payloads.
- Conformance suite enforces recommendation-policy regressions as blocking failures.

**RFC link**
- `rfcs/0035-phase8a-gnn-optimizer-service-contract-v1.md`
- `rfcs/0047-phase9b-intelligence-closure-contract-v1.md`

---

### P9B-04 — GNN Quality Signal Contract + Non-Regression Gates

**Type:** Optimizer Contract / Observability  
**Labels:** `phase-9b`, `gnn`, `quality`, `observability`

**Problem** Quality metrics (SWAP/fidelity/runtime) are not fully standardized for go/no-go model promotion decisions.

**Scope**
- Standardize emitted quality metric schema and confidence fields.
- Define non-regression threshold policy against production baseline.
- Add CI gate checks for metric schema drift and threshold violations.

**Acceptance Criteria**
- Quality signal payload is versioned and backward-compatible.
- Promotion fails closed when thresholds are not met.
- Regression reports are generated and archived as release artifacts.

**RFC link**
- `rfcs/0035-phase8a-gnn-optimizer-service-contract-v1.md`
- `rfcs/0047-phase9b-intelligence-closure-contract-v1.md`

---

### P9B-05 — Continuous Learning Reproducible Retrain + Model Registry Digests

**Type:** MLOps / Reproducibility  
**Labels:** `phase-9b`, `continuous-learning`, `mlops`, `governance`

**Problem** Retraining cannot be audited or reproduced consistently without strict snapshot and digest guarantees.

**Scope**
- Enforce retrain trigger rules (N new records/time cap/manual override) with audit events.
- Store dataset snapshot manifests, config digests, and model artifact hashes.
- Provide one-command reproduction path for a historical training run.

**Acceptance Criteria**
- Historical model can be rebuilt from stored manifests and digests.
- Trigger events are queryable and linked to produced model versions.
- Reproducibility checks are required in CI/release workflow.

**RFC link**
- `rfcs/0036-phase8a-continuous-learning-control-plane-contract-v1.md`
- `rfcs/0047-phase9b-intelligence-closure-contract-v1.md`

---

### P9B-06 — Canary Rollout + Auto-Rollback on Regression

**Type:** Runtime Safety / SRE  
**Labels:** `phase-9b`, `mlops`, `sre`, `rollback`

**Problem** Model rollout remains operationally risky without deterministic canary promotion and automatic rollback controls.

**Scope**
- Define canary cohort selection and evaluation window policy.
- Implement auto-rollback when regression thresholds trigger.
- Publish rollout/rollback runbook and drill evidence requirements.

**Acceptance Criteria**
- Canary decision outcomes are auditable with stable reason codes.
- Auto-rollback restores previous model version within documented SLO window.
- Rollout safety checks are mandatory for Phase-9B release gates.

**RFC link**
- `rfcs/0036-phase8a-continuous-learning-control-plane-contract-v1.md`
- `rfcs/0047-phase9b-intelligence-closure-contract-v1.md`

---

### P9B-07 — Phase-9B Evidence Bundle + Docs/RFC Sync

**Type:** Governance / Documentation  
**Labels:** `phase-9b`, `docs`, `governance`

**Problem** Stage closure is unverifiable without synchronized artifacts linking acceptance criteria to objective evidence.

**Scope**
- Publish Phase-9B compatibility report, release checklist, and exit evidence bundle.
- Synchronize implementation status with Stage-B RFC set.
- Map each issue acceptance criterion to verifiable evidence links.

**Acceptance Criteria**
- Phase-9B planning artifacts are linked from `docs/development/README.md`.
- RFC/ADR gap status is up to date and explicit.
- Exit evidence bundle includes reproducibility, canary, rollback, and non-regression reports.

**RFC link**
- `rfcs/0047-phase9b-intelligence-closure-contract-v1.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`
