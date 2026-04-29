This document is a ready-to-use set of GitHub issues for the **Phase-7** stage of the roadmap.

**Context Sources:**
- `docs/roadmap.md` (Section: "Phase-7: Stability & Developer Experience")
- `docs/development/post-mvp-open-source-roadmap.md` (Section: "Phase-7: Stability & Developer Experience")
- `docs/development/phase-7-stability-and-developer-experience.md`
- `docs/development/phase-7-rfc-adr-gap-analysis.md`

---

## Versioning & Compatibility Rules (Mandatory for every Phase-7 issue)

> Include this block in the description of every issue (as "Definition of Done / Constraints").

1. **SemVer is mandatory for stable contracts** across public API, CLI payloads, and plugin-facing envelopes.
2. **Breaking behavior requires `MAJOR`** and explicit migration notes.
3. **Backward-compatible additions use `MINOR`** with deterministic defaults.
4. **`PATCH` is non-semantic only** (bug fixes, docs fixes, observability tuning).
5. **Deprecations require a fixed support window:** deprecated interfaces remain supported for 2 minor releases or 90 days, whichever is longer; removals then require explicit RFC/ADR update + migration notes.
6. **Compatibility matrix updates are versioned artifacts** and must be fixture-tested.
7. **CI must fail closed** on undocumented contract drift.

---

## Milestone

- **Milestone:** `Phase-7 Stability & Developer Experience`
- **Suggested labels:** `phase-7`, `stability`, `dx`, `quality`, `rfc`

---

## Priority and ownership proposal (requires maintainer confirmation)

| Issue | Priority | Proposed owner group |
| --- | --- | --- |
| P7-01 API and Contract Versioning Policy v1 | P0 | Architecture/Governance |
| P7-02 Compatibility Matrix and Support Window Publication | P0 | Runtime/Core + Release Engineering |
| P7-03 Developer Onboarding and Tutorial Refresh Pack | P1 | Developer Experience / Docs |
| P7-04 Conformance and CI Gate Expansion | P0 | QA/CI Infrastructure |
| P7-05 Tooling Baseline: Formatter/Lint/Scaffold Integration | P1 | Developer Experience / Tooling |
| P7-06 Phase-7 RFC Package and ADR Synchronization | P0 | Architecture/Governance + Tech Writing |

> Confirmation required from maintainers for final DRI assignments and sequencing.

---

## Issues

### P7-01 — API and Contract Versioning Policy v1

**Type:** Governance / API  
**Labels:** `phase-7`, `stability`, `rfc`

**Problem** Versioning behavior is not centralized across API/CLI/plugin contracts.

**Scope**
- Define unified SemVer policy for public and internal contracts.
- Define deprecation lifecycle (announce -> warn -> remove) with minimum support window.
- Define release-note/migration-note requirements for breaking changes.

**Acceptance Criteria**
- Policy is documented and linked from dev and RFC pointers.
- Contract PRs include explicit version impact section.
- CI guard verifies migration-note presence on breaking markers.

**RFC link**
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`

---

### P7-02 — Compatibility Matrix and Support Window Publication

**Type:** Platform / Quality  
**Labels:** `phase-7`, `stability`, `quality`

**Problem** Operators and developers need explicit support windows and valid version combinations.

**Scope**
- Publish matrix for runtime, CLI, plugin API, and Eigen-Lang versions.
- Add machine-readable compatibility manifest for CI checks.
- Add deterministic rejection diagnostics for unsupported combinations.

**Acceptance Criteria**
- Compatibility matrix is versioned and test-fixture backed.
- Unsupported combinations fail with stable reason codes + hints.
- Docs include upgrade order for multi-component deployments.

**RFC link**
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`

---

### P7-03 — Developer Onboarding and Tutorial Refresh Pack

**Type:** Documentation / DX  
**Labels:** `phase-7`, `dx`, `docs`

**Problem** New contributors lack a single deterministic onboarding path.

**Scope**
- Refresh quickstart, local dev setup, and contribution workflow docs.
- Add canonical examples for runtime, plugin, and observability flows.
- Validate every tutorial via executable smoke checks.

**Acceptance Criteria**
- New contributor path from clone -> first successful run is documented.
- Tutorials map directly to maintained fixtures/examples.
- CI includes docs smoke checks for critical tutorials.

**RFC link**
- `rfcs/0033-phase7-developer-experience-and-conformance-toolchain-baseline-v1.md`

---

### P7-04 — Conformance and CI Gate Expansion

**Type:** Quality / CI  
**Labels:** `phase-7`, `quality`, `ci`

**Problem** Existing gates do not fully cover compatibility drift and migration-policy compliance.

**Scope**
- Add contract-drift checks for API schemas and version manifests.
- Add migration-note gate for breaking markers.
- Expand conformance suite for backward-compatibility paths.

**Acceptance Criteria**
- Contract drift is blocked before merge.
- Breaking changes without migration notes are blocked.
- Conformance suite covers previous supported minor baseline.

**RFC link**
- `rfcs/0033-phase7-developer-experience-and-conformance-toolchain-baseline-v1.md`

---

### P7-05 — Tooling Baseline: Formatter/Lint/Scaffold Integration

**Type:** DX / Tooling  
**Labels:** `phase-7`, `dx`, `tooling`

**Problem** Inconsistent local tooling increases review churn.

**Scope**
- Standardize formatter + linter execution in local scripts and CI.
- Add scaffold templates for common extension and test patterns.
- Align generated templates with current contract fixtures.

**Acceptance Criteria**
- Single documented command runs formatter/lint/test baseline.
- Scaffold outputs pass lint and contract checks by default.
- Tooling docs include minimal and full workflows.

**RFC link**
- `rfcs/0033-phase7-developer-experience-and-conformance-toolchain-baseline-v1.md`

---

### P7-06 — Phase-7 RFC Package and ADR Synchronization

**Type:** Architecture / Governance  
**Labels:** `phase-7`, `rfc`, `architecture`

**Problem** Phase-7 closure requires accepted RFCs and synchronized ADRs.

**Scope**
- Create/accept RFCs 0032 and 0033.
- Create corresponding ADRs at implementation checkpoint.
- Keep `docs/rfcs-pointer.md` and `docs/development/README.md` synchronized.

**Acceptance Criteria**
- Phase-7 RFC package is accepted and indexed.
- ADR synchronization checklist is complete.
- Readiness checklist and compatibility report are linked.

**RFC link**
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`
- `rfcs/0033-phase7-developer-experience-and-conformance-toolchain-baseline-v1.md`
