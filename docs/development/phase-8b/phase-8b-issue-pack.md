This document is a ready-to-use set of GitHub issues for the **Phase-8B** stage of the roadmap.

**Context Sources:**
- `docs/development/phase-8-implementation-roadmap-v1.1.0.md` (Section: "Phase-8B")
- `docs/development/phase-8b-execution-plan.md`
- `docs/development/post-mvp-open-source-roadmap.md` (phase progression context)
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md` (normative versioning constraints)

---

## Versioning & Compatibility Rules (Mandatory for every Phase-8B issue)

> Include this block in the description of every issue (as "Definition of Done / Constraints").

1. **SemVer is mandatory for stable contracts** across API, protobuf schemas, CLI payloads, and persisted envelopes.
2. **Breaking behavior requires `MAJOR`** and explicit migration notes.
3. **Backward-compatible additions use `MINOR`** with deterministic defaults.
4. **`PATCH` is non-semantic only** (bug fixes, docs fixes, observability tuning).
5. **Deprecations require a fixed support window:** deprecated interfaces remain supported for 2 minor releases or 90 days, whichever is longer; removals then require explicit RFC/ADR update + migration notes.
6. **Compatibility matrix updates are versioned artifacts** and must be fixture-tested.
7. **CI must fail closed** on undocumented contract drift.

---

## Milestone

- **Milestone:** `Phase-8B Runtime and Data Fabric Hardening`
- **Suggested labels:** `phase-8b`, `runtime`, `data-fabric`, `observability`, `ci`, `quality`

---

## Priority and ownership proposal (requires maintainer confirmation)

| Issue | Priority | Proposed owner group |
| --- | --- | --- |
| P8B-01 QRTX DAG Resolver and Lifecycle Idempotency Hardening | P0 | Runtime/Core |
| P8B-02 Scheduler Policy Pack: Priority + Quota + Topology/Noise Hooks | P0 | Runtime/Core + Scheduling |
| P8B-03 QFS-L3 Artifact Layout, Retention, and Metadata Indexing | P0 | Data/Storage |
| P8B-04 QFS-L2 Checkpoint/Restore API and Cost Guardrails | P0 | Data/Storage + Runtime/Core |
| P8B-05 Observability Join Model and Alert Pack for Runtime/Data Signals | P1 | Observability/SRE |
| P8B-06 Phase-8B CI Gate Bundle: Scale, Latency Trend, Integrity | P0 | QA/CI Infrastructure |
| P8B-07 Phase-8B Docs/RFC-ADR Sync and Exit Evidence Package | P1 | Architecture/Governance + Tech Writing |

> Confirmation required from maintainers for final DRI assignments and sequencing.

---

## Issues

### P8B-01 — QRTX DAG Resolver and Lifecycle Idempotency Hardening

**Type:** Runtime / Scheduling Core  
**Labels:** `phase-8b`, `runtime`, `quality`

**Problem** Scheduler determinism and replay safety are incomplete without a full DAG resolver and strict lifecycle transition invariants.

**Scope**
- Implement full DAG dependency resolver with deterministic error diagnostics.
- Define and enforce replay-safe lifecycle transitions for submit/schedule/dispatch/retry/cancel.
- Add idempotency tests for repeated and out-of-order control signals.

**Acceptance Criteria**
- DAG resolver handles valid/malformed dependency graphs with stable reason codes.
- Lifecycle transitions are idempotent and replay-safe under fixture-based tests.
- CI blocks merges when lifecycle invariants regress.

**RFC link**
- `docs/development/phase-8b-execution-plan.md`

---

### P8B-02 — Scheduler Policy Pack: Priority + Quota + Topology/Noise Hooks

**Type:** Runtime / Policy  
**Labels:** `phase-8b`, `runtime`, `scheduling`

**Problem** Research load fairness and target-performance behavior require explicit and testable scheduling policy layers.

**Scope**
- Implement priority and quota policy modules with starvation protection.
- Add topology/noise-aware dispatch hooks with deterministic fallback behavior.
- Document policy inputs, defaults, and operator override constraints.

**Acceptance Criteria**
- Policy modules are configurable and deterministic under fixed fixtures.
- Fallback behavior is explicit when topology/noise telemetry is missing.
- Policy regressions fail CI via policy fixture suite.

**RFC link**
- `docs/development/phase-8b-execution-plan.md`

---

### P8B-03 — QFS-L3 Artifact Layout, Retention, and Metadata Indexing

**Type:** Data Fabric / Storage  
**Labels:** `phase-8b`, `data-fabric`, `storage`

**Problem** Artifact persistence and retrieval remain fragile without strict layout invariants, retention semantics, and metadata indexing.

**Scope**
- Enforce strict artifact layout and metadata field validation.
- Implement retention policy executor and deterministic cleanup reason codes.
- Add metadata indexing for trace-linked artifact lookup paths.

**Acceptance Criteria**
- Artifact layout validation passes/fails deterministically with stable diagnostics.
- Retention behavior is covered by fixture tests across edge cases.
- Indexed lookup paths are documented and exercised in integration tests.

**RFC link**
- `docs/development/phase-8b-execution-plan.md`

---

### P8B-04 — QFS-L2 Checkpoint/Restore API and Cost Guardrails

**Type:** Data Fabric / Runtime API  
**Labels:** `phase-8b`, `data-fabric`, `runtime`, `quality`

**Problem** Checkpoint operations need hardened runtime behavior and explicit budget guardrails to avoid reliability and cost regressions.

**Scope**
- Harden checkpoint/restore API behavior and compatibility handling.
- Add guardrails for checkpoint size/time budget and admission controls.
- Add end-to-end integrity verification for restore and replay paths.

**Acceptance Criteria**
- Checkpoint/restore API behavior is deterministic and fixture-tested.
- Budget guardrail rejections emit stable reason codes and hints.
- Integrity suite validates snapshot decode and replay compatibility.

**RFC link**
- `docs/development/phase-8b-execution-plan.md`

---

### P8B-05 — Observability Join Model and Alert Pack for Runtime/Data Signals

**Type:** Observability / SRE  
**Labels:** `phase-8b`, `observability`, `sre`

**Problem** Runtime and storage regressions are hard to triage without unified correlation and milestone-specific alerts.

**Scope**
- Complete lifecycle span model across queue/schedule/dispatch/execute/persist/checkpoint.
- Join scheduler spans and hardware telemetry via stable correlation keys.
- Add alert pack for queue pressure, compiler regressions, and driver degradation.

**Acceptance Criteria**
- Correlation model is documented and validated by smoke fixtures.
- Alert definitions have deterministic thresholds and runbook links.
- Critical regression classes produce actionable diagnostics in CI/ops workflows.

**RFC link**
- `docs/development/phase-8b-execution-plan.md`

---

### P8B-06 — Phase-8B CI Gate Bundle: Scale, Latency Trend, Integrity

**Type:** Quality / CI  
**Labels:** `phase-8b`, `ci`, `quality`, `runtime`

**Problem** Phase-8B closure requires enforceable release gates for scale, latency trends, and artifact/checkpoint integrity.

**Scope**
- Add synthetic queue scale gate (>=10,000 jobs).
- Add enqueue latency trend gate (<=100 ms p95 target envelope in benchmark profile).
- Add artifact and checkpoint integrity gates with deterministic failure diagnostics.

**Acceptance Criteria**
- Gate bundle is executable and required on `main`/release branch policy.
- Scale, latency, and integrity failures are fail-closed with reason codes + mitigation hints.
- Fixture outputs and trend artifacts are versioned and documented.

**RFC link**
- `docs/development/phase-8b-execution-plan.md`

---

### P8B-07 — Phase-8B Docs/RFC-ADR Sync and Exit Evidence Package

**Type:** Governance / Documentation  
**Labels:** `phase-8b`, `docs`, `governance`

**Problem** Phase-8B cannot be closed without synchronized planning docs, compatibility artifacts, and governance traceability.

**Scope**
- Publish and synchronize Phase-8B execution/issue/checklist/report package.
- Confirm whether any new RFC/ADR items are required and open them if needed.
- Produce exit evidence bundle with CI gate links and compatibility impact statement.

**Acceptance Criteria**
- All Phase-8B planning artifacts are linked from `docs/development/README.md`.
- RFC/ADR delta decision is explicit ("none needed" or tracked issues/RFCs opened).
- Exit review bundle includes CI evidence and release-note draft references.

**RFC link**
- `docs/development/phase-8b-execution-plan.md`