# Phase-9A — Core Closure Execution Plan (TZ v1.3.0)

This document defines execution for **Stage A (Core closure)** from `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md`.

## Scope

Stage A closes critical-path kernel compliance for TZ v1.3.0:

- QFS L2 completion (retention, quotas, restore cache, recovery drills).
- QFS L1 / LQM completion (atomic qubit allocation, offline-node behavior, reconnect policy, HAL wiring).
- Security convergence (PDP enforcement across QRTX/LQM/QFS/KB, Vault/KMS lifecycle, anomaly/rate controls).
- Driver hardening (signed loading mandatory, official simulator/cloud matrix).
- CI hardening (SAST/DAST/SBOM + contract-conformance + fault-injection gates).

## Workstreams

1. **Runtime Data Fabric Hardening**
   - Finalize L2 quota model and retention windows.
   - Implement deterministic restore-path eviction (LRU) and recovery tests.
2. **Live Qubit Manager Production Closure**
   - Enforce atomic allocation and anti-double-booking semantics.
   - Add offline device failover states and reconnect backoff policy.
3. **Security Enforcement Closure**
   - Enforce PDP decisions at all critical path edges.
   - Bind secret lifecycle policy to Vault/KMS contract and auditable events.
4. **Driver Supply-Chain & Matrix Hardening**
   - Enforce signature verification before driver activation.
   - Freeze Stage-9A official matrix profile and smoke cadence.
5. **Release Gates and Failure-Injection**
   - Fail-closed CI rules for contract drift/security regressions.
   - Deterministic failure-injection scenarios per critical component.

## Deliverables

- `phase-9a-issue-pack.md` (ready-to-file issue set).
- `phase-9a-rfc-adr-gap-analysis.md` (normative governance sync).
- Stage-9A readiness checklist + compatibility and exit artifacts (tracked by issue P9A-08).

## Exit criteria

Stage-9A is complete when all are true:

1. All P0 Stage-9A issues are closed with evidence links.
2. Contracts introduced/changed in Stage-9A are fixture-locked and SemVer-tagged.
3. Rollback procedures for LQM/QFS/Driver policy are documented and drill-verified.
4. CI blocks merges on contract drift, signature bypass, and security policy regressions.

## Normative references

- `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md`
- `docs/development/post-mvp-open-source-roadmap.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`
- `rfcs/0039-phase8b-qfs-l2-l3-data-fabric-hardening-contract-v1.md`
- `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`
- `rfcs/0041-phase9a-policy-engine-v2-contract.md`
- `rfcs/0042-phase9a-federated-identity-and-workload-attestation.md`
- `rfcs/0043-phase9a-contract-drift-detection-and-auto-remediation.md`
