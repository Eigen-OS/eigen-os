# Phase-9A RFC/ADR Gap Analysis

## Purpose

Define RFC/ADR coverage needed for Stage-9A core-closure work and record whether new RFCs/ADRs are required.

## Source context

- `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md` (Stage A)
- `docs/development/phase-9a/phase-9a-execution-plan.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`

## Coverage matrix

| Stage-9A domain | Existing RFC | Existing ADR | Gap decision |
|---|---|---|---|
| QFS L2 quotas/retention/recovery | `rfcs/0039-phase8b-qfs-l2-l3-data-fabric-hardening-contract-v1.md` | `docs/adr/0025-phase8b-qfs-l2-l3-data-fabric-hardening-contract-v1.md` | **Covered**; no new RFC/ADR required if semantics stay backward-compatible. |
| LQM atomic allocation + failover wiring | `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md` | `docs/adr/0030-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md` | **Partially covered**; add Stage-9A appendix/migration notes if error classes change. |
| PDP enforcement + workload identity | `rfcs/0041-phase9a-policy-engine-v2-contract.md`, `rfcs/0042-phase9a-federated-identity-and-workload-attestation.md` | `docs/adr/0027-phase9a-policy-engine-v2-contract.md`, `docs/adr/0028-phase9a-federated-identity-and-workload-attestation.md` | **Covered**; enforce implementation mapping docs. |
| Contract drift auto-remediation | `rfcs/0043-phase9a-contract-drift-detection-and-auto-remediation.md` | `docs/adr/0029-phase9a-contract-drift-detection-and-auto-remediation.md` | **Covered**; CI evidence required. |
| Driver signature enforcement + official matrix governance | `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`, `rfcs/0045-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md` | `docs/adr/0030-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`, `docs/adr/0031-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md` | **Covered with update**; require explicit Stage-9A governance addendum in docs. |

## Stage-9A closure synchronization status (P9A-08)

- **Last synchronized:** 2026-05-20
- **Decision status:** Current for Stage-9A closure package.
- **Traceability links:**
  - Issue pack: `docs/development/phase-9a/phase-9a-issue-pack.md`
  - Release readiness checklist: `docs/development/phase-9a/phase-9a-release-readiness-checklist.md`
  - Compatibility report: `docs/development/phase-9a/phase-9a-compatibility-report.md`
  - Exit evidence bundle: `docs/development/phase-9a/phase-9a-exit-evidence-bundle.md
  
## Decision

- **No new RFC IDs are mandatory at Stage-9A kickoff.**
- **No new ADR IDs are mandatory at Stage-9A kickoff.**
- Existing RFC/ADR set is sufficient provided every Stage-9A issue links normative source(s) and includes SemVer/migration treatment per RFC-0032.

## Required documentation updates

1. Publish Stage-9A issue pack with mandatory versioning/compatibility constraints block.
2. Publish Stage-9A readiness checklist and compatibility report before stage close.
3. Record any contract-breaking deltas with MAJOR bump and migration notes.

## Re-open triggers (must create new RFC+ADR)

Create a new RFC + mirrored ADR if any of the following occurs:

- New public gRPC/REST methods or wire payload fields that alter stable behavior.
- Changes to deterministic state model for job lifecycle or qubit allocation semantics.
- New mandatory trust roots/signature chain requirements incompatible with current driver onboarding.
- Contract-level changes to retention/restore guarantees that impact operator expectations.
