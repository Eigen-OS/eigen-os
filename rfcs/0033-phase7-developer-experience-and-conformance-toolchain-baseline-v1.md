# RFC 0033: Phase-7 Developer Experience and Conformance Toolchain Baseline v1

- **Status**: Accepted
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-29
- **Target Milestone**: Phase 7
- **Tracking Issue**: P7-04 (docs/development/phase-7-issue-pack.md)

## Summary

Defines the baseline developer workflow and CI conformance gates required to keep contracts stable while reducing contributor friction.

## Goals

- Publish a deterministic onboarding flow.
- Expand conformance/compatibility CI gates.
- Standardize formatter/lint/scaffold workflows.

## Reference-level design

- A single documented local command sequence for format/lint/tests.
- CI gates for contract drift, migration-note checks, and compatibility fixtures.
- Maintained tutorial smoke checks tied to repository examples.

### Docs-smoke split (Default CI vs Nightly)

**Default CI (blocking):**
- Link/anchor checks for changed docs files in the PR.
- Reference integrity checks for canonical contract docs:
  - `docs/reference/**`
  - `src/services/eigen-compiler/src/eigen_lang/**`
  - `docs/reference/formats/**`
  - `docs/reference/api/**`
- Smoke checks for primary user-path docs:
  - `docs/tutorials/quickstart-local-sim.md`
  - `docs/howto/run-observability.md`
- Code-snippet execution/validation only for snippets that are:
  - in quickstart/howto, or
  - canonical examples, or
  - touching release/CI entrypoints.

**Nightly CI (non-blocking for PR merge):**
- Full-repo docs link/anchor sweeps.
- Extended snippet validation for non-canonical docs/tutorials.
- Additional docs regression scenarios across historical branches/fixtures.

## Observability

- Track CI gate failure classes by category:
  - `contract_drift`
  - `compatibility_regression`
  - `docs_smoke_failure`

## Test plan

- Add coverage assertions for conformance suites.
- Add deterministic docs smoke checks for canonical tutorials.
- Add regression fixtures for previous supported minor compatibility path.

## Compatibility and versioning

- **Version impact:** workflow baseline contract `1.0.0`.
- **Compatibility:** gate additions are `MINOR`; removal of mandatory checks is `MAJOR`.

## Open questions

- Rollout sequence for introducing docs-smoke blockers without increasing false positives in first two sprints.
