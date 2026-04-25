# RFC 0018: MVP-3 Runtime Observability and Release Gates

- **Status**: Accepted
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-25
- **Accepted on**: 2026-04-25
- **Target Milestone**: Phase 0 (MVP-3)
- **Tracking Issue**: docs/development/mvp-3-tracking-issue.md
- **Replaces / Related**: RFC 0008, RFC 0015, docs/development/mvp-3-execution-and-results.md

## Summary

Define mandatory MVP-3 runtime observability checks and blocking CI gates for submit→execute→results reliability on `sim:local`.

## Motivation

MVP-3 introduces execution lifecycle risk not covered by compilation-only conformance. Required runtime gates prevent regressions in terminalization, result retrieval, and trace/metrics correlation.

## Goals

- Require runtime smoke and observability checks as merge-blocking CI gates.
- Standardize minimum trace, metric, and structured log assertions for MVP-3.
- Add explicit release-readiness audit for MVP-3 closure.

## Non-Goals

- Full-scale load/performance benchmarking in blocking PR CI.
- Production SRE alert strategy for multi-cluster operations.
- Post-MVP analytics dashboards and long-term trend reporting.

## Guide-level Explanation

Before merge, CI must prove that runtime flow is healthy:

1. `submit -> watch -> results` succeeds for positive simulator path.
2. failing execution path produces deterministic `ERROR` terminal state and diagnostics.
3. trace context remains intact across `system-api`, `kernel`, and `driver-manager`.
4. metrics and logs expose required correlation identifiers.

Any regression in these gates blocks merge until fixed or intentionally updated.

## Reference-level Design

## Interfaces / APIs

- CI required jobs include:
  - runtime smoke (success path)
  - runtime smoke (failure path)
  - observability assertions (metrics + trace propagation)
  - fixture integrity checks for runtime outputs

## Data Models

- Runtime golden fixtures include:
  - status transition timeline
  - final `GetJobResults` payload
  - observability assertions (metric names / expected labels)
- Fixture update process requires explicit maintainer acknowledgement.

## Security and Privacy

- Observability checks must avoid exposing secrets/tokens in logs.
- CI artifacts should retain only sanitized traces and bounded logs.
- Failure diagnostics remain actionable without leaking sensitive internals.

## Observability

Minimum required telemetry fields per runtime request:

- `trace_id`
- `job_id`
- service/component label
- terminal state and canonical error code (if failed)

Metrics minimum set:

- runtime job count by terminal state
- end-to-end runtime latency histogram
- retrieval success/failure counters

## Performance

- Blocking runtime checks should stay within practical PR feedback bounds.
- Heavy stress scenarios may run as nightly non-blocking suites.
- Telemetry assertions should avoid flaky time-dependent expectations.

## Testing Plan

- Positive and negative runtime smoke tests in CI.
- Trace propagation integration test through full chain.
- Metrics validation test for required labels and counters.
- MVP-3 release-readiness audit checklist execution before freeze.

## Implementation / Migration

1. Promote runtime smoke and observability checks to required CI status.
2. Freeze runtime fixture update workflow and reviewer requirements.
3. Document required telemetry fields in development docs.
4. Execute MVP-3 readiness audit and close tracking issue.

## Considered Alternatives

- **Non-blocking runtime observability checks**: rejected for MVP-3 risk profile.
- **Manual release verification only**: rejected; not auditable enough for contract freeze.

## Resolution Notes

- Runtime smoke (success + failure), trace propagation checks, and telemetry field assertions remain required post-MVP-3 unless superseded by a newer ADR.
- Failure-path smoke is split into deterministic validation/runtime/backend fixtures to preserve ownership and triage clarity.
