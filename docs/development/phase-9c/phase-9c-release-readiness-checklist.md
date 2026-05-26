# Phase-9C Release Readiness Checklist

## Scope

This checklist closes Stage-C (Multi-tenant policy + plugin-first expansion) from `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md` and must be completed together with:

- `docs/development/phase-9c/phase-9c-compatibility-report.md`
- `docs/development/phase-9c/phase-9c-exit-evidence-bundle.md`
- `docs/development/phase-9c/phase-9c-rfc-adr-gap-analysis.md`
- `docs/development/fixtures/phase9c/policy_capability_matrix_v1_1_0.json`

## Contract & governance gates

- [ ] RFC 0048 status is `Accepted` or `Implemented` with no unresolved normative TODOs.
- [ ] ADR 0034 is published and synchronized with RFC 0048 outcomes.
- [ ] SemVer impact is declared for all changed contract surfaces per RFC 0032.
- [ ] Migration notes are present for every breaking change (if any).
- [ ] CI fail-closed policy is preserved for contract-drift and conformance gates.

## Stage-C functional closure gates

- [ ] Core tenant envelope (`tenant_id`, `project_id`, quota envelope) is versioned with deterministic defaults.
- [ ] Baseline fair queueing primitives are deterministic with plugins disabled.
- [ ] Advanced scheduling ownership is plugin-only and explicitly excluded from core deterministic baseline.
- [ ] Plugin-failure isolation semantics are enforced for timeout/crash/malformed-output classes.
- [ ] Kernel fallback reason codes are stable, documented, and fixture-validated.
- [ ] Explain API evidence includes tenant/project, quota evaluation, plugin provenance, and fallback outcome.
- [ ] Policy plugin SDK conformance checks are required in CI for integration eligibility.

## Evidence & reproducibility gates

- [ ] Compatibility matrix fixture is versioned and validated as immutable release artifact.
- [ ] Deterministic-core-with-plugins-disabled proof includes ordering snapshots and reason code assertions.
- [ ] Plugin-failure-isolation drill includes timeout/crash/malformed-output scenarios with expected fallback path.
- [ ] Acceptance criteria mapping for P9C-01..P9C-07 is complete and link-resolvable.
- [ ] Runbook links include operator commands for replaying Stage-C evidence checks.

## Documentation closure gates

- [ ] `docs/development/README.md` links to all Phase-9C planning and closure artifacts.
- [ ] RFC/ADR gap status is explicit and up to date.
- [ ] Phase-9C compatibility report is published with versioning rationale.
- [ ] Exit evidence bundle maps each acceptance criterion to objective proof.
