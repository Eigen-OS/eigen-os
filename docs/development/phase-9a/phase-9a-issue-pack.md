This document is a ready-to-use set of GitHub issues for the **Phase-9A** stage of the roadmap.

**Context Sources:**
- `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md` (Section: "Stage A — Core closure")
- `docs/development/phase-9a/phase-9a-execution-plan.md`
- `docs/development/post-mvp-open-source-roadmap.md` (phase progression context)
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md` (normative versioning constraints)

---

## Versioning & Compatibility Rules (Mandatory for every Phase-9A issue)

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

- **Milestone:** `Phase-9A Core Closure`
- **Suggested labels:** `phase-9a`, `kernel`, `qfs`, `lqm`, `security`, `drivers`, `sre`, `conformance`

---

## Priority and ownership proposal (requires maintainer confirmation)

| Issue | Priority | Proposed owner group |
| --- | --- | --- |
| P9A-01 QFS L2 Retention/Quota/Restore Cache Closure | P0 | Runtime/Data Fabric |
| P9A-02 Live Qubit Manager Atomic Allocation + Offline Failover | P0 | Runtime/Kernel |
| P9A-03 PDP Enforcement End-to-End (QRTX/QFS/LQM/KB) | P0 | Security + Kernel |
| P9A-04 Vault/KMS Secret Lifecycle + Audit Wiring | P0 | Security/Platform |
| P9A-05 Driver Signature Enforcement + Official Matrix Hardening | P0 | Drivers/Platform Integrity |
| P9A-06 CI Fail-Closed Gates (SAST/DAST/SBOM/Drift/Fault Injection) | P0 | DevEx/Release Engineering |
| P9A-07 Stage-9A Rollback Runbooks + Drill Evidence | P1 | SRE/Operations |
| P9A-08 Phase-9A Docs + RFC/ADR Sync + Exit Evidence Bundle | P1 | Architecture/Governance + Tech Writing |

---

## Issues

### P9A-01 — QFS L2 Retention/Quota/Restore Cache Closure

**Type:** Runtime Data Fabric  
**Labels:** `phase-9a`, `qfs`, `runtime`, `reliability`

**Problem** QFS L2 behavior is not yet fully deterministic under quota pressure and restore-path churn.

**Scope**
- Finalize quota semantics and retention windows for checkpoint artifacts.
- Implement deterministic LRU restore cache + eviction diagnostics.
- Add recovery/fault tests for checkpoint restore under pressure.

**Acceptance Criteria**
- Quota exceedance yields deterministic error classes and non-corrupt recovery behavior.
- Restore cache policy is observable and documented.
- Recovery suite is required and green in CI for Stage-9A release gates.

**RFC link**
- `rfcs/0039-phase8b-qfs-l2-l3-data-fabric-hardening-contract-v1.md`

---

### P9A-02 — Live Qubit Manager Atomic Allocation + Offline Failover

**Type:** Kernel Runtime / HAL Integration  
**Labels:** `phase-9a`, `lqm`, `kernel`, `availability`

**Problem** LQM cannot be considered production-ready without strict atomic allocation guarantees and deterministic offline-node handling.

**Scope**
- Harden atomic qubit allocation/deallocation with anti-double-booking checks.
- Implement offline-node detection, reconnect/backoff, and safe degradation states.
- Validate LQM-to-QDriver wiring for error propagation and retry semantics.

**Acceptance Criteria**
- Allocation race scenarios are prevented by test and fixture evidence.
- Offline/reconnect transitions are deterministic and observable.
- Driver-originated allocation failures map to stable runtime error taxonomy.

**RFC link**
- `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`
- `docs/development/phase-9a/p9a-02-lqm-atomic-allocation-offline-failover.md` (implementation spec and deterministic test matrix)

---

### P9A-03 — PDP Enforcement End-to-End (QRTX/QFS/LQM/KB)

**Type:** Security / Policy Enforcement  
**Labels:** `phase-9a`, `security`, `policy`, `kernel`

**Problem** Zero-trust guarantees are incomplete while authorization checks remain inconsistent across critical runtime edges.

**Scope**
- Enforce PDP policy decisions in submit/execute/store/restore/query paths.
- Standardize deny/audit responses and policy reason codes.
- Add negative conformance tests for unauthorized cross-tenant access.

**Acceptance Criteria**
- All critical path edges fail closed on missing/invalid authorization context.
- Audit trail includes stable policy decision metadata.
- Unauthorized access tests are mandatory and green in CI.

**RFC link**
- `rfcs/0041-phase9a-policy-engine-v2-contract.md`
- `rfcs/0042-phase9a-federated-identity-and-workload-attestation.md`

---

### P9A-04 — Vault/KMS Secret Lifecycle + Audit Wiring

**Type:** Security Platform Integration  
**Labels:** `phase-9a`, `security`, `secrets`, `operations`

**Problem** Secret storage/rotation/revocation guarantees are not yet uniformly implemented for runtime and driver paths.

**Scope**
- Define and implement secret lifecycle states (issue, rotate, revoke, expire).
- Enforce least-privilege retrieval paths for runtime components and drivers.
- Publish auditable secret-event traces integrated with observability.

**Acceptance Criteria**
- Secret lifecycle events are queryable and linked to actor/workload context.
- Revoked credentials are blocked within documented propagation windows.
- Rotation drill evidence is attached in Stage-9A exit bundle.

**RFC link**
- `rfcs/0042-phase9a-federated-identity-and-workload-attestation.md`

---

### P9A-05 — Driver Signature Enforcement + Official Matrix Hardening

**Type:** Driver Supply Chain / Compatibility  
**Labels:** `phase-9a`, `drivers`, `integrity`, `conformance`

**Problem** Driver trust posture is incomplete while unsigned or weakly-validated artifacts can still enter runtime paths.

**Scope**
- Make signature verification mandatory prior to driver load/activation.
- Freeze Stage-9A official driver matrix profile and version pins.
- Add fail-closed checks for signature bypass and metadata mismatch.

**Acceptance Criteria**
- Unsigned/tampered drivers are rejected deterministically with auditable reasons.
- Official matrix artifacts are versioned and fixture-tested.
- Release gates block on signature-policy regressions.

**RFC link**
- `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`
- `docs/development/phase-9a/p9a-02-lqm-atomic-allocation-offline-failover.md` (implementation spec and deterministic test matrix)
- `rfcs/0045-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`

---

### P9A-06 — CI Fail-Closed Gates (SAST/DAST/SBOM/Drift/Fault Injection)

**Type:** Release Engineering / Security Quality  
**Labels:** `phase-9a`, `ci`, `security`, `conformance`

**Problem** Stage-9A compliance cannot be trusted without hard fail-closed CI coverage for contracts and security regressions.

**Scope**
- Add required jobs for SAST/DAST/SBOM verification.
- Enforce contract drift checks and failure-injection scenarios as blocking gates.
- Publish required-branch-protection mapping for Stage-9A.

**Acceptance Criteria**
- Required CI jobs are documented and enforced for `main`.
- Any contract drift without migration notes fails the pipeline.
- Fault-injection suite is deterministic and required for release.

**RFC link**
- `rfcs/0043-phase9a-contract-drift-detection-and-auto-remediation.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`

---

### P9A-07 — Stage-9A Rollback Runbooks + Drill Evidence

**Type:** Operations / SRE  
**Labels:** `phase-9a`, `sre`, `rollback`, `operations`

**Problem** Operational risk is elevated unless rollback controls are codified and drill-validated for Stage-9A changes.

**Scope**
- Publish runbooks for LQM, QFS L2, policy engine, and driver trust regressions.
- Define rollback levers (pin, quarantine, gate disable policy with approvals).
- Run and document rollback drills with escalation paths.

**Acceptance Criteria**
- Runbooks are approved by component owners and SRE.
- Drill artifacts prove mean-time-to-restore within stated target.
- Exit bundle contains drill evidence and lessons learned.

**RFC link**
- `rfcs/0041-phase9a-policy-engine-v2-contract.md`
- `rfcs/0043-phase9a-contract-drift-detection-and-auto-remediation.md`

---

### P9A-08 — Phase-9A Docs + RFC/ADR Sync + Exit Evidence Bundle

**Type:** Governance / Documentation  
**Labels:** `phase-9a`, `docs`, `governance`

**Problem** Stage-9A cannot be closed without synchronized execution governance and artifact traceability.

**Scope**
- Publish issue-pack/checklist/compatibility/exit-evidence artifacts for Stage-9A.
- Synchronize implementation status against existing RFC/ADR set.
- Map each acceptance criterion to objective evidence links.

**Acceptance Criteria**
- Stage-9A planning artifacts are linked from `docs/development/README.md`.
- RFC/ADR gap decision is explicit and up to date.
- Exit evidence bundle covers security, conformance, and rollback drills.

**RFC link**
- `rfcs/0041-phase9a-policy-engine-v2-contract.md`
- `rfcs/0042-phase9a-federated-identity-and-workload-attestation.md`
- `rfcs/0043-phase9a-contract-drift-detection-and-auto-remediation.md`
