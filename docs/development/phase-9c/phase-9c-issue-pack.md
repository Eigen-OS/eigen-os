This document is a ready-to-use set of GitHub issues for the **Phase-9C** stage of the roadmap.

**Context Sources:**
- `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md` (Section: "Stage C — Multi-tenant policy + plugin-first expansion")
- `docs/development/phase-9c/phase-9c-rfc-adr-gap-analysis.md`
- `docs/development/post-mvp-open-source-roadmap.md` (phase progression context)
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md` (normative versioning constraints)
- `rfcs/0048-phase9c-multitenant-plugin-boundary-contract-v1.md` (Stage-C normative contract)

---

## Versioning & Compatibility Rules (Mandatory for every Phase-9C issue)

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

- **Milestone:** `Phase-9C Multi-tenant Plugin Boundary`
- **Suggested labels:** `phase-9c`, `multitenancy`, `scheduler`, `plugin-sdk`, `explainability`, `conformance`, `security`

---

## Priority and ownership proposal (requires maintainer confirmation)

| Issue | Priority | Proposed owner group |
| --- | --- | --- |
| P9C-01 Core Tenant Envelope + Baseline Quotas Contract | P0 | Kernel Runtime + API Platform |
| P9C-02 Deterministic Fair Queueing Primitives + Fixture Locks | P0 | QRTX Runtime + SRE |
| P9C-03 Plugin-Only Advanced Scheduling Boundary Extraction | P0 | Runtime Platform + Plugin SDK |
| P9C-04 Plugin Failure Isolation + Kernel Fallback Reason Codes | P0 | Runtime Reliability + Security |
| P9C-05 Explain API v2 for Multi-Tenant Decision Evidence | P1 | System API + Observability |
| P9C-06 Plugin SDK Policy Templates + Conformance Harness Update | P1 | Developer Experience + Plugin Platform |
| P9C-07 Phase-9C Compatibility Matrix + Migration Notes + Evidence Bundle | P1 | Architecture/Governance + Tech Writing |

---

## Issues

### P9C-01 — Core Tenant Envelope + Baseline Quotas Contract

**Type:** API Contract / Runtime Governance  
**Labels:** `phase-9c`, `multitenancy`, `api`, `quotas`

**Problem** Stage-C requires first-class tenant/project controls in open core, but current contracts do not define strict canonical fields and deterministic defaults.

**Scope**
- Add canonical `tenant_id`, `project_id`, and quota envelope fields to job submission/runtime payload surfaces.
- Define deterministic defaults for missing optional tenant metadata.
- Add authz and policy checks ensuring quota evaluation occurs in kernel path.

**Acceptance Criteria**
- Tenant envelope schema is versioned and fixture-tested across API and runtime paths.
- Quota checks execute deterministically with stable reason codes.
- Migration notes document all new required/optional fields and defaults.

**RFC link**
- `rfcs/0048-phase9c-multitenant-plugin-boundary-contract-v1.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`

---

### P9C-02 — Deterministic Fair Queueing Primitives + Fixture Locks

**Type:** Scheduler Baseline / Determinism  
**Labels:** `phase-9c`, `scheduler`, `determinism`, `conformance`

**Problem** Fair queueing exists conceptually, but no Stage-C locked primitive set guarantees deterministic scheduler baseline when plugins are disabled.

**Scope**
- Implement baseline fair queueing primitives in QRTX core (tenant/project aware).
- Freeze deterministic tie-break and starvation-protection semantics.
- Add golden fixtures for admission ordering under fixed seeds and workload snapshots.

**Acceptance Criteria**
- Scheduler outputs are deterministic for fixed inputs and seed.
- Fairness primitives operate with plugins fully disabled.
- Conformance suite blocks regressions in admission ordering and reason codes.

**RFC link**
- `rfcs/0048-phase9c-multitenant-plugin-boundary-contract-v1.md`

---

### P9C-03 — Plugin-Only Advanced Scheduling Boundary Extraction

**Type:** Architecture Boundary / Pluginization  
**Labels:** `phase-9c`, `scheduler`, `plugins`, `architecture`

**Problem** Non-baseline policies (batch/preemption/backfill/drift-aware scoring) risk leaking into core and violating Stage-C open-core boundary rules.

**Scope**
- Extract advanced scheduling strategies into plugin interfaces only.
- Keep baseline fair scheduling in core with no dependency on optional policy plugins.
- Provide at least one reference policy plugin implementation per extracted surface.

**Acceptance Criteria**
- Core scheduler remains functional and deterministic without policy plugins.
- All advanced policies are invoked only via versioned plugin contract.
- Compatibility matrix explicitly marks core vs plugin-owned policy capabilities.

**RFC link**
- `rfcs/0048-phase9c-multitenant-plugin-boundary-contract-v1.md`
- `rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md`

---

### P9C-04 — Plugin Failure Isolation + Kernel Fallback Reason Codes

**Type:** Runtime Safety / Reliability  
**Labels:** `phase-9c`, `plugins`, `reliability`, `security`

**Problem** Plugin execution failures can currently introduce ambiguity in lifecycle behavior unless kernel fallback semantics are fixed and auditable.

**Scope**
- Define fail-open/fail-closed policy by plugin category (policy plugins default fail-isolated).
- Implement deterministic kernel fallback path for plugin timeouts, crashes, malformed outputs.
- Add structured reason-code taxonomy and alert hooks for isolation events.

**Acceptance Criteria**
- Plugin failures cannot crash or deadlock kernel lifecycle state machine.
- Fallback behavior is deterministic and fixture-tested.
- Security/ops telemetry includes stable reason codes and plugin identity provenance.

**RFC link**
- `rfcs/0048-phase9c-multitenant-plugin-boundary-contract-v1.md`
- `rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md`

---

### P9C-05 — Explain API v2 for Multi-Tenant Decision Evidence

**Type:** API/Observability Contract  
**Labels:** `phase-9c`, `explainability`, `api`, `observability`

**Problem** `/explain` outputs do not yet guarantee complete evidence for tenant-aware backend/scheduler decisions.

**Scope**
- Extend explain payload with tenant/project decision context and quota/policy trace.
- Normalize evidence identifiers and reason-code hierarchy across scheduler/backend decisions.
- Add deterministic snapshots for explain responses under fixed execution traces.

**Acceptance Criteria**
- `/explain` responses include end-to-end decision provenance without leaking sensitive fields.
- Explain schema is versioned and backward-compatible.
- Observability docs include query recipes for tenant incident analysis.

**RFC link**
- `rfcs/0048-phase9c-multitenant-plugin-boundary-contract-v1.md`
- `rfcs/0024-phase4-explainability-api-contract-v1.md`

---

### P9C-06 — Plugin SDK Policy Templates + Conformance Harness Update

**Type:** DX / SDK / Governance  
**Labels:** `phase-9c`, `plugin-sdk`, `dx`, `conformance`

**Problem** Plugin-first expansion is slowed by missing policy-plugin templates and insufficient out-of-the-box conformance checks.

**Scope**
- Add `plugin scaffold policy` template with trust/sandbox defaults.
- Add `plugin validate policy` checks for manifest, reason-code schema, timeout envelope, deterministic fallback compatibility.
- Publish fixtures for plugin authors to self-certify before integration.

**Acceptance Criteria**
- New policy plugin can be scaffolded and validated with documented one-command workflow.
- CI includes policy-plugin conformance checks as required gates.
- SDK docs clearly separate mandatory core interfaces from optional extension hooks.

**RFC link**
- `rfcs/0048-phase9c-multitenant-plugin-boundary-contract-v1.md`
- `rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md`

---

### P9C-07 — Phase-9C Compatibility Matrix + Migration Notes + Evidence Bundle

**Type:** Governance / Documentation  
**Labels:** `phase-9c`, `docs`, `compatibility`, `governance`

**Problem** Stage closure cannot be audited without synchronized matrix/migration/evidence artifacts linking each acceptance criterion to objective proof.

**Scope**
- Publish Phase-9C release checklist, compatibility report, and exit evidence bundle.
- Update compatibility matrix for core-vs-plugin policy ownership and fallback semantics.
- Map each P9C issue acceptance criterion to evidence links (fixtures, reports, runbooks).

**Acceptance Criteria**
- Phase-9C artifacts are linked from `docs/development/README.md`.
- RFC/ADR gap status is current and explicit.
- Exit bundle includes deterministic-core-with-plugins-disabled proof and plugin-failure-isolation drills.

**RFC link**
- `rfcs/0048-phase9c-multitenant-plugin-boundary-contract-v1.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`
