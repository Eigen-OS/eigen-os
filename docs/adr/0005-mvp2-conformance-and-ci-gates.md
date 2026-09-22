# ADR 0005: MVP-2 conformance fixtures and CI gating policy

- **Status:** Accepted
- **Date:** 2026-04-24
- **Deciders:** Core architecture maintainers

## Context

MVP-2 introduces deterministic compilation and request packaging requirements that need explicit CI quality gates.

## Decision

1. CI must include conformance suites for:
   - Eigen-Lang → AQO deterministic fixtures,
   - JobSpec → SubmitJobRequest deterministic fixtures,
   - CLI `eigen submit` request-shape tests against a mock API.
2. Minimum conformance baseline includes at least five valid Eigen-Lang programs (including sequential and parallel chains) plus negative fixtures.
3. Any contract-affecting change requires fixture updates in the same PR.
4. Failing conformance tests block merge.

## Consequences

- Contract drift is detected early.
- MVP-2 delivery criteria are enforceable in automation.
- Developers get a predictable update workflow for golden fixtures.

## Related

- MVP-2 plan: `docs/development/mvp-2-compilation-pipeline.md`
- Development checks: `docs/development/README.md`