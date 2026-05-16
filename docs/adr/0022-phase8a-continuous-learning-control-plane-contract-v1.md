# ADR 0022: Phase-8A Continuous Learning Control Plane Contract v1

- **Status**: Accepted
- **Date**: 2026-05-16
- **Decision owners**: Runtime/Core, ML Platform, Architecture/Governance
- **Supersedes / Related**: RFC 0036, ADR 0018, ADR 0019

## Context

Continuous learning orchestration in Phase-8A needs explicit lifecycle-state and control-command semantics to avoid cross-service ambiguity. RFC 0036 defines contract v1 invariants for commands, transitions, idempotency, and auditability.

## Decision

Adopt RFC 0036 as the operational baseline for control-plane contract v1:

1. Control commands and lifecycle transitions are stable, versioned interface semantics.
2. Idempotency and replay guarantees are mandatory and test-covered.
3. Governance/audit observability fields are required across control actions.
4. Drift in lifecycle or command semantics requires SemVer classification with migration policy compliance.

## Consequences

- Learning pipeline operations gain deterministic, auditable control-plane behavior.
- Downstream automation can rely on stable transition invariants.
- Governance and CI controls can detect undocumented incompatibilities early.

## Verification and evidence

- RFC source: `rfcs/0036-phase8a-continuous-learning-control-plane-contract-v1.md`
- Synchronization pointers: `docs/rfcs-pointer.md`, `docs/development/README.md`
- Phase-8A closure docs: gap analysis, readiness checklist, compatibility report
