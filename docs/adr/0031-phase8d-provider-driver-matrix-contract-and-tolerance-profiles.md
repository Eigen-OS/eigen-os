# ADR 0031 — Phase-8D Provider Driver Matrix Contract and Tolerance Profiles

- **Status:** Accepted
- **Date:** 2026-05-19
- **Deciders:** Driver Manager, SRE, Platform Governance
- **Supersedes:** None
- **Superseded by:** None
- **RFC Link:** `rfcs/0045-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`

## Context

Phase-8D introduces multi-provider readiness requirements that need explicit matrix governance, tolerance profiles, and rollback evidence.

## Decision

Adopt RFC 0045 as the operational baseline for provider matrix versioning, tolerance-policy enforcement, and incident rollback governance.

## Consequences

- Matrix/tolerance artifacts are required release evidence.
- Incident drill and rollback rehearsal evidence become closure prerequisites.
- Contract drift and parity regressions fail closed in CI.
