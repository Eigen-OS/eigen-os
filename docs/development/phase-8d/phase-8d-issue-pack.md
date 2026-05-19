This document is a ready-to-use set of GitHub issues for the **Phase-8D** stage of the roadmap.

**Context Sources:**
- `docs/development/phase-8/phase-8-implementation-roadmap-v1.1.0.md` (Section: "Phase-8D")
- `docs/development/phase-8d/phase-8d-execution-plan.md`
- `docs/development/post-mvp-open-source-roadmap.md` (phase progression context)
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md` (normative versioning constraints)

---

## Versioning & Compatibility Rules (Mandatory for every Phase-8D issue)

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

- **Milestone:** `Phase-8D Hardware Externalization`
- **Suggested labels:** `phase-8d`, `drivers`, `system-api`, `dashboard`, `ide`, `conformance`, `sre`

---

## Priority and ownership proposal (requires maintainer confirmation)

| Issue | Priority | Proposed owner group |
| --- | --- | --- |
| P8D-01 QDriver API v1.0 Finalization + Conformance Kit | P0 | Runtime/Drivers |
| P8D-02 IBM Quantum Official Driver Hardening | P0 | Drivers/Provider Integrations |
| P8D-03 AWS Braket Official Driver Hardening | P0 | Drivers/Provider Integrations |
| P8D-04 Simulator Parity Profile + Cross-Provider Tolerance Suite | P0 | Runtime/QA |
| P8D-05 System API REST Parity + Compatibility Matrix Publication | P0 | System API + Architecture |
| P8D-06 Developer Surfaces Skeleton Pack (Web Dashboard, VS Code, Jupyter) | P1 | DX/Frontend + SDK |
| P8D-07 Operator Runbooks + Rollback Governance for Official Matrix | P1 | SRE/Operations |
| P8D-08 Phase-8D Docs/RFC-ADR Sync + Exit Evidence Bundle | P1 | Architecture/Governance + Tech Writing |

---

## Issues

### P8D-01 — QDriver API v1.0 Finalization + Conformance Kit

**Type:** Runtime / Driver Contract  
**Labels:** `phase-8d`, `drivers`, `runtime`, `conformance`

**Problem** QDriver behavior is not yet frozen as a normative v1.0 contract with machine-verifiable conformance semantics.

**Scope**
- Finalize QDriver v1.0 capability model, lifecycle, and error taxonomy.
- Build conformance harness with deterministic fixtures (submit/watch/results/cancel).
- Enforce fail-closed behavior for unsupported capabilities.

**Acceptance Criteria**
- Conformance suite runs against simulator, IBM, and AWS adapters.
- Adapter non-compliance yields deterministic error class and actionable diagnostics.
- Release gates require conformance green for official matrix.

**RFC link**
- `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`

---

### P8D-02 — IBM Quantum Official Driver Hardening

**Type:** Provider Driver  
**Labels:** `phase-8d`, `drivers`, `ibm`, `conformance`

**Problem** IBM integration requires hardened adapter semantics, quota/error handling, and matrix-grade operational support.

**Scope**
- Implement version-pinned IBM adapter compatibility layer.
- Add retries/timeouts/quota handling aligned with QDriver v1.0 semantics.
- Add IBM profile to nightly conformance smoke.

**Acceptance Criteria**
- Canonical Phase-8D workload runs unchanged on IBM target within documented tolerance.
- IBM-specific failure classes map to stable QDriver error taxonomy.
- Incident runbook sections for IBM degradation are published.

**RFC link**
- `rfcs/0045-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`

---

### P8D-03 — AWS Braket Official Driver Hardening

**Type:** Provider Driver  
**Labels:** `phase-8d`, `drivers`, `aws`, `conformance`

**Problem** AWS Braket adapter needs parity-grade integration and drift controls to join the official support matrix.

**Scope**
- Implement version-pinned Braket adapter compatibility layer.
- Add retries/timeouts/queue-state handling aligned with QDriver v1.0 semantics.
- Add AWS profile to nightly conformance smoke.

**Acceptance Criteria**
- Canonical Phase-8D workload runs unchanged on AWS target within documented tolerance.
- AWS-specific failure classes map to stable QDriver error taxonomy.
- Incident runbook sections for AWS degradation are published.

**RFC link**
- `rfcs/0045-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`

---

### P8D-04 — Simulator Parity Profile + Cross-Provider Tolerance Suite

**Type:** Runtime Quality / Validation  
**Labels:** `phase-8d`, `simulator`, `quality`, `conformance`

**Problem** Externalization claims are unverifiable without a formal parity baseline and tolerance suite.

**Scope**
- Freeze simulator parity profile for canonical workload class.
- Define cross-provider tolerance envelope (result shape, latency bands, noise deltas).
- Publish automated comparison reports for simulator/IBM/AWS.

**Acceptance Criteria**
- Same workload input produces tolerance-compliant outputs on all official targets.
- Drift beyond tolerance fails release gate.
- Tolerance policy is versioned and linked from compatibility matrix.

**RFC link**
- `rfcs/0045-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`

---

### P8D-05 — System API REST Parity + Compatibility Matrix Publication

**Type:** API / Compatibility  
**Labels:** `phase-8d`, `system-api`, `compatibility`, `governance`

**Problem** Operator and integrator trust depends on stable parity between internal contracts and externally documented REST behavior.

**Scope**
- Validate parity for submit/watch/results/cancel key paths.
- Publish versioned compatibility matrix across providers/capabilities.
- Add contract drift checks between protobuf/internal API and REST projection.

**Acceptance Criteria**
- REST parity checks are required and green in CI.
- Compatibility matrix is published and versioned with release artifact links.
- CLI/SDK flows remain backward-compatible or include migration notes.

**RFC link**
- `rfcs/0046-phase8d-externalization-surfaces-contract-v1.md`

---

### P8D-06 — Developer Surfaces Skeleton Pack (Web Dashboard, VS Code, Jupyter)

**Type:** Developer Experience / Surface Bootstrap  
**Labels:** `phase-8d`, `dashboard`, `ide`, `notebook`, `dx`

**Problem** Ecosystem onboarding is blocked without minimal but consistent developer surfaces.

**Scope**
- Publish web dashboard skeleton for lifecycle/status/target visibility.
- Publish VS Code integration skeleton for submit/status/results flow.
- Publish Jupyter integration skeleton for notebook-side workflow + trace metadata capture.

**Acceptance Criteria**
- All skeletons are documented with explicit non-GA markers.
- Basic walkthroughs execute against simulator profile.
- Surface contracts align with system-api parity constraints.

**RFC link**
- `rfcs/0046-phase8d-externalization-surfaces-contract-v1.md`

---

### P8D-07 — Operator Runbooks + Rollback Governance for Official Matrix

**Type:** Operations / SRE  
**Labels:** `phase-8d`, `sre`, `operations`, `rollback`

**Problem** Official provider support is unsafe without incident response playbooks and deterministic rollback controls.

**Scope**
- Publish runbooks for provider outage/degradation/auth/quota failure classes.
- Define rollback controls: adapter pin, quarantine, matrix demotion.
- Add rehearsal checks for rollback procedures and escalation paths.

**Acceptance Criteria**
- Runbooks are approved by operations and component owners.
- Rollback rehearsal evidence is linked in exit bundle.
- Conformance gates include rollback-safety checks.

**RFC link**
- `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`
- `rfcs/0045-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`

---

### P8D-08 — Phase-8D Docs/RFC-ADR Sync + Exit Evidence Bundle

**Type:** Governance / Documentation  
**Labels:** `phase-8d`, `docs`, `governance`

**Problem** Phase-8D cannot be closed without synchronized execution/governance documents and linked validation artifacts.

**Scope**
- Publish execution/issue/checklist/compatibility/exit-evidence docs for Phase-8D.
- Synchronize accepted Phase-8D RFCs with mirrored ADRs and pointers.
- Prepare closure evidence mapping every acceptance criterion to artifacts.

**Acceptance Criteria**
- Phase-8D planning artifacts are linked from `docs/development/README.md`.
- RFC/ADR coverage decision is explicit in gap analysis.
- Exit evidence bundle includes conformance, parity, and runbook drill proof.

**RFC link**
- `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`
- `rfcs/0045-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`
- `rfcs/0046-phase8d-externalization-surfaces-contract-v1.md`
