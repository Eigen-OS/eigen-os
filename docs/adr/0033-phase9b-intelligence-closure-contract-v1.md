# ADR 0033: Phase-9B Intelligence Closure Contract v1

- Status: Accepted
- Date: 2026-05-20
- Deciders: Core maintainers
- RFC: `rfcs/0047-phase9b-intelligence-closure-contract-v1.md`

## Context

Phase-9B closes Stage-B requirements from the TZ v1.3.0 open-core alignment plan. The project needs a stable operational baseline that ties acceptance criteria to objective evidence while preserving SemVer and fail-closed contract governance.

## Decision

Adopt the Phase-9B intelligence closure contract as an accepted operational baseline with these mandatory outcomes:

1. Phase-9B closure artifacts are first-class release deliverables (release checklist, compatibility report, exit evidence bundle).
2. RFC/ADR synchronization is explicit for Stage-B contract decisions.
3. Exit evidence must include reproducibility, canary, rollback, and non-regression reports.
4. Versioning and compatibility discipline remains governed by RFC 0032:
   - breaking behavior => MAJOR + migration notes;
   - backward-compatible additions => MINOR;
   - non-semantic fixes => PATCH.
5. CI/conformance policy remains fail-closed for undocumented drift.

## Consequences

### Positive

- Stage-B closure becomes auditable and reproducible.
- Acceptance criteria can be independently verified from evidence links.
- SemVer governance remains consistent with previously accepted policy.

### Trade-offs

- Documentation overhead increases for each Stage-B closure cycle.
- Release closure depends on maintaining evidence artifact freshness.

## Compliance notes

- This ADR does not introduce a breaking runtime/API schema change on its own.
- For any future breaking contract updates in Phase-9B scope, migration notes become mandatory.
