This document is a ready-to-use set of GitHub issues for the **Phase-4** stage of the roadmap.

**Context Sources:**
- `docs/roadmap.md` (Section: "Phase-4: Intelligent Runtime")
- `docs/development/post-mvp-open-source-roadmap.md` (Section: "Phase-4: Intelligent Runtime")
- `docs/development/phase-4-intelligent-runtime.md`
- `docs/development/phase-4-rfc-adr-gap-analysis.md`

---

## Versioning Rules (Mandatory for every Phase-4 issue)

> Include this block in the description of every issue (as "Definition of Done / Constraints").

1. **SemVer for stable intelligent-runtime contracts:**
   - Scoring profile schemas, policy bundle schemas, and explanation API DTOs use `MAJOR.MINOR.PATCH`.
2. **Breaking changes only via `MAJOR`:**
   - Any incompatible decision semantic, explanation envelope, or policy resolution change requires `MAJOR`.
3. **Backward-compatible additions via `MINOR`:**
   - Optional fields and additive explainability metadata use `MINOR`.
4. **`PATCH` for fixes only:**
   - No public decision semantic changes in `PATCH` releases.
5. **Mandatory version markers in decision artifacts:**
   - Decision outputs and explain responses include explicit version fields.
6. **Deprecation policy:**
   - Fields cannot be removed before at least one `MINOR` release marks them deprecated.
7. **Changelog discipline:**
   - Every Phase-4 PR includes:
     - `Version impact`
     - `Compatibility`
     - `Migration notes` (if applicable).

---

## Milestone

- **Milestone:** `Phase-4 Intelligent Runtime`
- **Suggested labels:** `phase-4`, `intelligent-runtime`, `scheduling`, `api`, `observability`, `eigen-lang`, `quality`, `rfc`

---

## Issues

### P4-01 — Backend Scoring Module Core v1

**Type:** Feature  
**Labels:** `phase-4`, `intelligent-runtime`, `runtime`

**Problem** Runtime backend selection needs deterministic and inspectable scoring instead of ad-hoc heuristics.

**Scope**
- Feature extraction schema for backend and workload descriptors.
- Deterministic weighted scoring contract with stable tie-break behavior.
- Versioned scoring profile persistence.

**Acceptance Criteria**
- Identical input descriptors yield identical score vectors.
- Tie-break policy is explicit and test-covered.
- Score output includes contract and profile version markers.

**RFC link**
- `rfcs/0023-phase4-backend-selection-scoring-contract-v1.md`

---

### P4-02 — Scheduling Policy Engine and Policy Bundles

**Type:** Feature  
**Labels:** `phase-4`, `scheduling`, `runtime`

**Problem** Operators need explicit, configurable policies (`latency`, `throughput`, `cost`, `balanced`) with deterministic conflict handling.

**Scope**
- Policy bundle schema + validation.
- Priority/override resolution rules.
- Fallback behavior when policy inputs are missing or invalid.

**Acceptance Criteria**
- Policy bundles are versioned and schema-validated.
- Conflict-resolution outcomes are deterministic and reproducible.
- Safe fallback behavior is documented and tested.

**RFC link**
- `rfcs/0025-phase4-scheduling-policy-engine-contract-v1.md`

---

### P4-03 — Explain API: Backend Selection (`/explain/backend-selection`)

**Type:** API  
**Labels:** `phase-4`, `api`, `intelligent-runtime`

**Problem** Users and operators need clear explanations for backend selection decisions.

**Scope**
- Request/response schema for backend selection explanations.
- Explanation envelope with factor contributions and confidence metadata.
- Conformance fixtures and compatibility gate.

**Acceptance Criteria**
- Explain responses are stable for identical decision artifacts.
- API schema is documented in `docs/reference/`.
- Contract tests block incompatible changes.

**RFC link**
- `rfcs/0024-phase4-explainability-api-contract-v1.md`

---

### P4-04 — Explain API: Execution Decisions (`/explain/execution`)

**Type:** API  
**Labels:** `phase-4`, `api`, `intelligent-runtime`

**Problem** Runtime behavior changes (queueing, fallback, retry path) must be explainable and auditable.

**Scope**
- Execution explanation DTO including policy branch, fallback reason, and timing annotations.
- Error model alignment with public API conventions.
- Compatibility fixtures for explanation envelope.

**Acceptance Criteria**
- Execution explanation payload includes deterministic decision lineage.
- Structured errors map consistently to invalid requests/artifacts.
- Golden fixtures protect explain output compatibility.

**RFC link**
- `rfcs/0024-phase4-explainability-api-contract-v1.md`

---

### P4-05 — Eigen-Lang Runtime-Intelligence Hints and Diagnostics

**Type:** Compiler / Language  
**Labels:** `phase-4`, `eigen-lang`, `compiler`

**Problem** Developers need visibility into runtime-intelligence decisions directly from Eigen-Lang workflows.

**Scope**
- Compile-time diagnostics for unsupported targets/policy conflicts.
- Runtime-intelligence hint metadata in compiler outputs.
- Execution annotations linking to explainability artifacts.

**Acceptance Criteria**
- Diagnostics are deterministic and fixture-tested.
- Hint metadata version is explicit and documented.
- Workflow annotations reference explainability identifiers.

**RFC link**
- `rfcs/0023-phase4-backend-selection-scoring-contract-v1.md`
- `rfcs/0024-phase4-explainability-api-contract-v1.md`

---

### P4-06 — Observability Pack for Intelligent Runtime

**Type:** Observability  
**Labels:** `phase-4`, `observability`, `sre`

**Problem** Decision quality, fallback rates, and explain endpoint health must be observable in production-like environments.

**Scope**
- Metrics for scoring latency/errors, policy branches, fallback frequency.
- Dashboards for decision behavior and drift indicators.
- Alerts + runbook entries for explain API error spikes and scoring failures.

**Acceptance Criteria**
- Dashboards show end-to-end intelligent-runtime decision flow.
- Alerts fire for scoring failures and explain endpoint SLO breaches.
- Runbook contains concrete triage and rollback procedures.

**RFC link**
- `rfcs/0024-phase4-explainability-api-contract-v1.md`
- `rfcs/0025-phase4-scheduling-policy-engine-contract-v1.md`

---

### P4-07 — Determinism and Reproducibility Gate for Runtime Decisions

**Type:** Quality  
**Labels:** `phase-4`, `quality`, `intelligent-runtime`

**Problem** Intelligent runtime decisions are only trustworthy if identical inputs reproduce identical outputs.

**Scope**
- Determinism suite for scoring + policy resolution + explanation output.
- Drift-detection fixtures for decision-regression scenarios.
- CI gate for deterministic replay.

**Acceptance Criteria**
- Replay of recorded decision artifacts yields stable outputs.
- Drift gate blocks uncontrolled changes in scoring or policy results.
- Failure diagnostics identify non-deterministic input or branch.

**RFC link**
- `rfcs/0023-phase4-backend-selection-scoring-contract-v1.md`
- `rfcs/0025-phase4-scheduling-policy-engine-contract-v1.md`

---

### P4-08 — RFC Package for Phase-4 Contracts

**Type:** Architecture / Governance  
**Labels:** `phase-4`, `rfc`, `architecture`

**Problem** Phase-4 implementation cannot be stabilized without formal contract RFCs.

**Scope**
- Create/accept RFCs for:
  1. backend scoring contract,
  2. explainability API contract,
  3. scheduling policy engine contract.
- Link RFCs from roadmap/development docs.

**Acceptance Criteria**
- Required Phase-4 RFC set is merged and indexed.
- Each RFC includes compatibility and test plan sections.
- RFC statuses are explicit (`Draft`/`Accepted`/`Implemented`).

**RFC link**
- `rfcs/0023-phase4-backend-selection-scoring-contract-v1.md`
- `rfcs/0024-phase4-explainability-api-contract-v1.md`
- `rfcs/0025-phase4-scheduling-policy-engine-contract-v1.md`

---

### P4-09 — ADR Synchronization and Phase-4 Release Meta

**Type:** Meta / Release  
**Labels:** `phase-4`, `adr`, `release`, `quality`

**Problem** Implemented RFC outcomes must be mirrored in ADRs before Phase-4 release closure.

**Scope**
- Add ADRs synchronized to implemented Phase-4 RFCs.
- Publish Phase-4 release readiness checklist and compatibility report.
- Update ADR index and RFC pointer docs.

**Acceptance Criteria**
- Every implemented Phase-4 RFC has synchronized ADR coverage.
- `docs/adr/README.md` and `docs/rfcs-pointer.md` are updated.
- Release package docs are linked from `docs/development/README.md`.

**RFC link**
- `rfcs/0023-phase4-backend-selection-scoring-contract-v1.md`
- `rfcs/0024-phase4-explainability-api-contract-v1.md`
- `rfcs/0025-phase4-scheduling-policy-engine-contract-v1.md`

---

## Open data required before issue execution

To keep Phase-4 implementation deterministic and auditable, maintainers must finalize:

1. scoring feature allowlist for v1;
2. default policy priority map per deployment profile;
3. explainability payload depth visible to end users vs operators;
4. SLO thresholds for explain APIs and decision-fallback alerting.
