# Phase-8D RFC/ADR Gap Analysis (Hardware Externalization and Provider Readiness)

- **Status:** Accepted
- **Date:** 2026-05-19
- **Version:** 1.2.0
- **Issue:** P8D-08

## Objective

Determine whether Phase-8D scope is fully covered by existing accepted contracts or requires additional RFC/ADR artifacts before milestone closure.

## Inputs reviewed

- `docs/development/phase-8/phase-8-implementation-roadmap-v1.1.0.md`
- `docs/development/phase-8d/phase-8d-execution-plan.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`
- Accepted Phase-8A/8B/8C baselines and mirrored ADR package.

## Gap decision

**Phase-8D requires a new RFC/ADR package (3 RFCs + 3 mirrored ADRs) for closure.**

Rationale:
- Current contracts do not freeze QDriver v1.0 conformance semantics for official provider matrix governance.
- Current governance does not provide normative tolerance and compatibility policy for simulator vs cloud providers.
- Developer externalization surfaces (dashboard + IDE/notebook skeletons + REST parity contract) need explicit lifecycle and compatibility language.

## Required governance package for Phase-8D

1. **RFC 0044 / ADR 0030** — QDriver API v1.0 Final Contract and Conformance Semantics.
2. **RFC 0045 / ADR 0031** — Provider Driver Matrix Contract (Simulator/IBM/AWS) and Tolerance Profiles.
3. **RFC 0046 / ADR 0032** — Externalization Surfaces Contract (System API parity + dashboard + VS Code/Jupyter skeletons).

## Governance traceability requirements

- Phase-8D closure requires all three RFCs accepted and mirrored ADRs accepted.
- `docs/rfcs-pointer.md`, `docs/adr/README.md`, and `docs/development/README.md` must include final links.
- Any breaking delta to existing APIs/contracts discovered during implementation requires RFC revision before merge.
- Conformance and compatibility matrix artifacts must be versioned and linked in the release package.

## Compatibility statement (planning state)

- **Version Impact (planning docs only):** MINOR.
- **Breaking Marker (planning docs only):** false.
- **Migration Notes:** TBD at RFC acceptance; expected to remain additive for existing CLI/system-api flows.

## Gap matrix

| Area | Required artifact | Current evidence | Status |
| --- | --- | --- | --- |
| QDriver v1.0 conformance semantics | New accepted RFC + mirrored ADR | RFC 0044 + ADR 0030 accepted | Closed |
| Provider parity/tolerance policy | New accepted RFC + mirrored ADR | RFC 0045 + ADR 0031 accepted | Closed |
| REST parity + developer externalization surfaces | New accepted RFC + mirrored ADR | RFC 0044 + ADR 0030 accepted | Closed |
| Incident/rollback governance for official matrix | Acceptance criteria + runbook policy references | Checklist + runbook references linked | Closed |
| Docs pointer synchronization | Updated development/RFC/ADR indexes | Pointers synchronized in docs indexes | Closed |
