# Phase-9A Release Readiness Checklist

- **Status:** Accepted (for milestone execution)
- **Date:** 2026-05-20
- **Milestone:** M9A

Use this checklist at sprint reviews and release-candidate evaluation for Phase-9A closure.

## 1) Governance and contract readiness

- [ ] RFC 0041 accepted and linked.
- [ ] RFC 0042 accepted and linked.
- [ ] RFC 0043 accepted and linked.
- [ ] ADR mirrors are accepted and linked for RFC 0041/0042/0043 (ADR 0027/0028/0029).
- [ ] Phase-9A compatibility report is published and marked Accepted.

## 2) Runtime and security readiness

- [ ] QFS L2 quota/retention/restore semantics are deterministic and evidenced.
- [ ] LQM atomic allocation and offline failover behavior is deterministic and evidenced.
- [ ] PDP enforcement is fail-closed across QRTX/QFS/LQM/KB paths.
- [ ] Vault/KMS lifecycle events (issue/rotate/revoke/expire) are auditable.
- [ ] Driver signature enforcement is mandatory for load/activation paths.

## 3) CI fail-closed readiness

- [ ] Stage-9A required CI gate mapping is approved (`docs/development/phase-9a/p9a-06-ci-fail-closed-gates.md`).
- [ ] Contract drift checks fail closed on undocumented change.
- [ ] SAST, DAST, and SBOM gates are blocking for `main`.
- [ ] Fault-injection/conformance suites are required and green.
- [ ] Required branch-protection job list is published and current.

## 4) Compatibility and versioning readiness

- [ ] Compatibility matrix artifacts are versioned and fixture-tested.
- [ ] Contract-surface changes carry explicit Version Impact classification (MAJOR/MINOR/PATCH/NONE).
- [ ] Any breaking behavior includes migration notes and rollout/rollback guidance.
- [ ] Deprecation window policy (2 minor releases or 90 days) is recorded for any deprecated interface.
- [ ] Release notes draft includes contract-impact summary and operator actions.

## 5) Operations and rollback readiness

- [ ] Stage-9A rollback runbook is approved (`docs/howto/stage-9a-rollback-runbook.md`).
- [ ] Rollback drill evidence fixture is validated (`docs/development/fixtures/phase9a/rollback_drill_evidence_v1.json`).
- [ ] Escalation and ownership map is reviewed by SRE + component owners.
- [ ] Mean-time-to-restore target evidence is attached for each drill scenario.
- [ ] Exception handling process is documented for fail-closed gate override requests.

## 6) Exit evidence bundle completeness

- [ ] Security evidence package is complete (PDP, identity/attestation, secrets lifecycle).
- [ ] Conformance evidence package is complete (CI gate bundle + contract drift + driver policy).
- [ ] Rollback evidence package is complete (runbook + drills + lessons learned).
- [ ] RFC/ADR gap analysis is current and explicitly states any open decisions.
- [ ] Stage-9A planning artifacts are linked from `docs/development/README.md`.
