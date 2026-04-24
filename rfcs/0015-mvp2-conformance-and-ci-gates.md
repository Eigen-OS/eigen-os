# RFC 0015: MVP-2 Conformance Fixtures and CI Gates

- **Status**: Draft
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-24
- **Target Milestone**: Phase 0 (MVP-2)
- **Tracking Issue**: (to be created)
- **Replaces / Related**: RFC 0008, RFC 0010, ADR 0005

## Summary

Define the mandatory MVP-2 conformance and CI quality gates for JobSpec parsing, Eigen-Lang compilation, CLI submit packaging, and baseline observability checks.

## Motivation

MVP-2 requires reproducibility and confidence across multiple components. A clear RFC for CI gates prevents accidental regressions and aligns contributors on merge requirements.

## Goals

- Require deterministic fixture coverage for JobSpec and compiler outputs.
- Make conformance suites blocking in CI for MVP-2 scoped components.
- Standardize minimum negative-test expectations for validation behavior.
- Ensure release readiness checks are explicit and auditable.

## Non-Goals

- Full end-to-end performance benchmarking suite.
- Post-MVP hardware backend compliance expansion.
- Non-MVP policy checks unrelated to compilation pipeline.

## Guide-level Explanation

Before a PR merges, CI must prove:

1. JobSpec fixtures map deterministically to expected submit payloads.
2. Eigen-Lang conformance tests pass for golden and negative cases.
3. CLI submit path produces expected request envelopes.
4. Required observability and smoke checks remain green.

If any gate fails, merge is blocked until fixed or intentionally updated.

## Reference-level Design

## Interfaces / APIs

- CI pipeline is the enforcement interface for gate policy.
- Required jobs include parser, compiler, CLI, and smoke integration checks.
- Golden fixtures are version-controlled and reviewed like code.

## Data Models

- Fixture sets:
  - `job.yaml` input → canonical `SubmitJobRequest` expectations.
  - `program.eigen.py` input → canonical AQO output.
- Golden updates require explicit reviewer acknowledgment.

## Security and Privacy

- CI must run without executing untrusted program payloads.
- Test artifacts should avoid leaking sensitive runtime secrets.
- Failure logs should provide diagnostics without secret exposure.

## Observability

- CI should publish pass/fail visibility for all MVP-2 gates.
- Smoke tests should verify metrics and trace propagation signals remain intact.
- Gate outcomes should be easy to audit for release readiness.

## Performance

- Conformance suite runtime should stay within practical PR feedback windows.
- Larger stress/perf suites may be nightly and non-blocking during MVP-2.
- Determinism checks should avoid flaky time-dependent assertions.

## Testing Plan

- At least 5 valid Eigen-Lang conformance programs (including sequential/parallel chains).
- Negative conformance set for unsupported syntax and safety violations.
- JobSpec fixture matrix for required and malformed payloads.
- CLI integration tests against mock/fake API endpoint.

## Implementation / Migration

1. Finalize fixture directories and naming conventions.
2. Mark CI jobs as required in branch protection.
3. Add policy notes to contributing/development docs.
4. Run release-readiness audit for MVP-2 start gate.

## Considered Alternatives

- **Ad-hoc tests per subsystem**: rejected (insufficient system-level confidence).
- **Non-blocking conformance jobs**: rejected for MVP-2 risk profile.

## Open Questions

- Should golden fixture update tooling be standardized in repo scripts?
- Which CI gates remain required after MVP-2 completion?
