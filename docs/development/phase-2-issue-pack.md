his document is a ready-to-use set of GitHub issues for the **Phase-2** stage of the roadmap.

**Context Source:** `docs/development/post-mvp-open-source-roadmap.md` (Section: "Phase 2 — Orchestration Layer").

---

## Versioning Rules (Mandatory for every Phase-2 issue)

> Include this block in the description of every issue (as "Definition of Done / Constraints").

1. **SemVer for Stable Contracts (Phase-2 policy):**
   - Scheduler API/DTOs/statuses/reason codes are versioned via `MAJOR.MINOR.PATCH`.
2. **Breaking Changes only via MAJOR:**
   - Any incompatible change to queues, quota semantics, dispatch reason codes, or batch contracts requires a new `MAJOR` version.
3. **Backward-compatible changes via MINOR:**
   - New optional policy fields, capability flags, and extensions that do not break clients -> `MINOR`.
4. **PATCH for fixes only:**
   - No changes to the public semantics of orchestration contracts.
5. **Mandatory Version Markers in artifacts:**
   - Scheduler decisions, batch manifests, and routing explanations must contain an explicit version field.
6. **Deprecation Policy:**
   - Before removing a public policy field/code, at least one `MINOR` release must mark it as deprecated.
7. **Changelog Discipline:**
   - Every Phase-2 PR must include the following sections:
     - `Version impact`
     - `Compatibility`
     - `Migration notes` (if applicable).

---

## Milestone

- **Milestone:** `Phase-2 Orchestration Layer`
- **Suggested labels:** `phase-2`, `orchestration`, `scheduler`, `runtime`, `reliability`, `sre`, `api`

---

## Issues

### P2-01 — Scheduler Core v1: Priority Queues + Admission Control

**Type:** Feature  
**Labels:** `phase-2`, `scheduler`, `orchestration`

**Problem** A production scheduler baseline is needed with predictable execution order and manageable admission control.

**Scope**
- Priority queues (job priority + FIFO within the same priority level).
- Admission policy (queue limits, reject/defer semantics).
- Scheduler loop metrics and health endpoints.

**Acceptance Criteria**
- The scheduler deterministically selects the next job.
- Admission decisions are documented and observable.
- Integration tests cover basic queue scenarios.

**Versioning Constraints**
- Scheduler decision envelope contains a version.
- Breaking change to decision DTO -> `MAJOR`.

---

### P2-02 — Quotas and Fairness Policy Baseline

**Type:** Reliability  
**Labels:** `phase-2`, `scheduler`, `reliability`

**Problem** Without quotas and fairness, individual tenants or projects can monopolize backend capacity.

**Scope**
- Per-tenant/per-project quotas.
- Weighted fairness policy.
- Starvation prevention policy.

**Acceptance Criteria**
- Quota and fairness policies are configurable.
- Tests confirm starvation prevention is working.
- Quota denial and fairness lag metrics are published.

**Versioning Constraints**
- Changing fairness score semantics without a `MAJOR` version is prohibited.

---

### P2-03 — Device Scoring Engine (Latency + Availability + Calibration)

**Type:** Feature  
**Labels:** `phase-2`, `orchestration`, `runtime`

**Problem** A formalized mechanism is needed to select a backend based on operational signals.

**Scope**
- Device score model implementation.
- Inputs: queue depth, recent latency, calibration freshness, and health status.
- Weight configuration and defaults.

**Acceptance Criteria**
- Dispatch records include the score breakdown.
- Fallback to a deterministic tie-breaker is implemented.
- Device score is verified against test fixtures.

**Versioning Constraints**
- Public score fields and reason codes require SemVer discipline.

---

### P2-04 — Dispatch Explainability API/CLI

**Type:** Feature / DX  
**Labels:** `phase-2`, `api`, `orchestration`

**Problem** Operators and developers need explainability: why was a job sent to a specific backend?

**Scope**
- Dispatch rationale schema definition.
- API endpoint and CLI command to retrieve rationale.
- Correlation with timelines, logs, and traces.

**Acceptance Criteria**
- An explainability payload is available for every dispatched job.
- The payload includes the policy version and reason codes.
- Troubleshooting use cases are documented.

**Versioning Constraints**
- Removing existing reason codes requires a `MAJOR` version.

---

### P2-05 — Multi-device Execution Contract (Split/Merge)

**Type:** Feature  
**Labels:** `phase-2`, `orchestration`, `runtime`

**Problem** A contract is needed for safe split/merge operations when executing a workload across multiple backends.

**Scope**
- Split planner for compatible tasks.
- Partial-result envelope definition.
- Merge semantics and consistency checks.

**Acceptance Criteria**
- Split/merge contract is documented and covered by integration tests.
- Partial failure errors are mapped to a standardized error envelope.
- Artifacts contain references to the parent job and shard IDs.

**Versioning Constraints**
- Breaking changes to the partial-result contract -> `MAJOR`.

---

### P2-06 — Batch Execution Optimizer v1

**Type:** Feature  
**Labels:** `phase-2`, `scheduler`, `performance`

**Problem** Throughput needs to be increased by grouping and executing compatible jobs together.

**Scope**
- Batch candidate selection policy.
- Batch size and wait window tuning.
- Backpressure-safe batch dispatcher.

**Acceptance Criteria**
- Throughput improvement is confirmed via benchmark scenarios.
- Latency regression remains within SLO boundaries.
- A kill-switch for batch mode is implemented.

**Versioning Constraints**
- Batch manifest schema versioning is mandatory.

---

### P2-07 — Rebalancing and Preemption Safety Rules

**Type:** Reliability  
**Labels:** `phase-2`, `reliability`, `scheduler`

**Problem** The system must safely rebalance the queue and, if necessary, perform preemption during load changes.

**Scope**
- Rebalancing triggers implementation.
- Preemption policy and guardrails.
- Idempotent requeue semantics.

**Acceptance Criteria**
- No job loss during requeue or preemption.
- Preemption policy is documented and testable.
- Preemption impact metrics are available in observability tools.

**Versioning Constraints**
- Changing terminal/preempted status semantics without a `MAJOR` version is prohibited.

---

### P2-08 — Orchestration Observability Pack

**Type:** Feature  
**Labels:** `phase-2`, `observability`, `sre`

**Problem** Metrics and dashboards are required to manage queues, quotas, fairness, and dispatch quality.

**Scope**
- Queue depth and age metrics.
- Fairness lag, quota deny, and rebalance counters.
- Dashboards and alerts specifically for the orchestrator.

**Acceptance Criteria**
- A basic orchestration dashboard is available to operators.
- Alert rules cover overload and starvation indicators.
- Runbook includes triage steps.

**Versioning Constraints**
- Metric names are considered part of the public observability contract.

---

### P2-09 — Compatibility and Migration Suite for Scheduler Contracts

**Type:** Quality  
**Labels:** `phase-2`, `quality`, `api`

**Problem** A merge-blocking quality gate is needed for orchestration contracts.

**Scope**
- Contract compatibility tests (scheduler DTOs, reason codes, batch manifests).
- Snapshot/golden fixtures for policy outputs.
- CI gate integration.

**Acceptance Criteria**
- CI blocks incompatible contract changes.
- Every contract change includes migration notes.
- Updating golden fixtures requires an explicit review label.

**Versioning Constraints**
- A Phase-2 release cannot be marked as "Ready" without a compatibility report.

---

### P2-10 — Phase-2 Release Readiness Checklist

**Type:** Meta / Release  
**Labels:** `phase-2`, `release`, `quality`

**Problem** A unified gating process is required for the Phase-2 release.

**Scope**
- Consolidated checklist: scheduler reliability, performance, docs, and upgrade notes.
- Compatibility report for orchestration contracts.
- Release notes template with a versioning impact section.

**Acceptance Criteria**
- All Phase-2 issues are linked to the milestone and verified against DoD.
- Release notes and migration notes are prepared.
- Supported version matrix for scheduler, device, and batch contracts is locked.

**Versioning Constraints**
- The release is not marked as "Ready" without a signed compatibility and migration package.

---

## Suggested Dependency Graph

- `P2-01` -> `P2-02`
- `P2-01` + `P2-03` -> `P2-04`
- `P2-03` -> `P2-05`
- `P2-01` + `P2-02` -> `P2-06`
- `P2-06` -> `P2-07`
- `P2-08` parallel after `P2-01`
- `P2-09` blocked by P2-01..P2-08
- `P2-10` blocked by all tasks above

## Suggested Issue Template Snippet

```md
## Versioning Impact

- Contract changed: yes/no
- Change type: MAJOR/MINOR/PATCH
- Affected interfaces: Scheduler API | Dispatch rationale | Device scoring | Batch manifest | Metrics

## Compatibility

- Backward compatible: yes/no
- Forward compatible: yes/no
- Deprecation window (if any):

## Migration notes

- Required operator action:
- Required client action:
