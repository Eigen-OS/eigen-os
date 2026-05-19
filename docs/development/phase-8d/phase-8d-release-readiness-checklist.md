# Phase-8D Release Readiness Checklist

- **Status:** Draft (for milestone execution)
- **Date:** 2026-05-19
- **Milestone:** M8D

Use this checklist at sprint reviews and release candidate evaluation for Phase-8D closure.

## 1) Governance and contract readiness

- [ ] RFC 0044 accepted and linked.
- [ ] RFC 0045 accepted and linked.
- [ ] RFC 0046 accepted and linked.
- [ ] ADR mirrors created/updated for all accepted RFC decisions (ADR 0030-0032).
- [ ] Compatibility matrix policy artifact is versioned.

## 2) Driver and provider readiness

- [ ] QDriver v1.0 capability and error taxonomy are frozen.
- [ ] Conformance harness is required and green.
- [ ] IBM Quantum official driver passes conformance and parity checks.
- [ ] AWS Braket official driver passes conformance and parity checks.
- [ ] Simulator parity profile is frozen and published.

## 3) Externalization surface readiness

- [ ] REST parity checks for submit/watch/results/cancel are green.
- [ ] Provider compatibility matrix is published and linked.
- [ ] Web dashboard skeleton is published with non-GA marker.
- [ ] VS Code integration skeleton is published with non-GA marker.
- [ ] Jupyter integration skeleton is published with non-GA marker.

## 4) Quality and CI gate readiness

- [ ] Cross-provider tolerance gate is required and green.
- [ ] Nightly conformance smoke for simulator/IBM/AWS is required and green.
- [ ] Contract drift checks for external API projections are required and green.
- [ ] Gate failures produce deterministic reason codes and mitigation hints.
- [ ] Rollback-safety fixture verification is required and green.

## 5) Operations and rollback readiness

- [ ] Runbooks for provider outage/degradation/auth/quota failures are approved (`docs/howto/official-provider-rollback-runbook.md`).
- [ ] Rollback controls (pin/quarantine/demotion) are documented and tested via rollback-safety fixture checks.
- [ ] Escalation map is reviewed with owner groups.
- [ ] One rollback drill per official provider is completed and evidenced.
- [ ] On-call handoff package is approved.

## 6) Exit evidence bundle completeness

- [ ] Conformance suite report is published.
- [ ] Cross-provider tolerance report is published.
- [ ] Compatibility report is published.
- [ ] Runbook drill evidence is published.
- [ ] Release-note impact summary draft is prepared and reviewed.
