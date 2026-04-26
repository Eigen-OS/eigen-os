# RFC 0019: Phase 1 Production Runtime Plan

- **Status**: Draft
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-26
- **Target Milestone**: Phase 1
- **Tracking Issue**: —
- **Replaces / Related**: RFC 0016, RFC 0017, RFC 0018, docs/development/post-mvp-open-source-roadmap.md

## Summary

Define the Phase 1 implementation contract that evolves Eigen-OS from MVP-3 simulator-first runtime into a production-oriented runtime with external hardware provider support, stronger runtime resiliency semantics, durable object-storage-compatible artifacts, and operational observability v2.

## Motivation

MVP-3 validated deterministic runtime behavior for `sim:local` and established baseline release gates. To become practically useful for external users, Eigen-OS now needs:

- a stable path for real backend integration;
- deterministic behavior under timeout/cancellation/transient failure conditions;
- durable and versioned result persistence;
- richer telemetry for operating non-trivial runtime flows.

Without a dedicated Phase 1 contract, implementation can fragment across services and break runtime expectations established in MVP-3.

## Goals

- Introduce external provider driver integration while preserving kernel runtime authority.
- Specify deterministic timeout, cancellation, and retry behavior.
- Add object-storage-compatible result persistence with versioned artifact layout.
- Standardize observability v2 metrics/logs/traces for runtime operations.
- Promote Phase 1 gates to merge-blocking CI checks with deterministic fixtures.

## Non-Goals

- Scheduler fairness, quotas, and multi-tenant policy controls (Phase 2).
- Cross-device workload decomposition and batch optimization (Phase 2).
- Benchmark dataset platform and comparative analytics tooling (Phase 3).
- ML-driven backend selection and adaptive scheduling policy (Phase 4).

## Guide-level Explanation

Phase 1 keeps MVP-3 runtime lifecycle guarantees but broadens execution environments and hardens reliability.

Operationally, the expected user path remains:

1. submit a valid job;
2. observe deterministic state transitions;
3. receive terminal status;
4. retrieve durable result artifacts.

The critical difference is that execution may target external providers through driver-manager adapters. Runtime policy for timeout, cancellation, and retries remains centrally governed by kernel, and output durability no longer depends on local-only filesystem assumptions.

## Reference-level Design

### Interfaces / APIs

1. **Driver-manager provider adapter contract**
   - Driver descriptor declares capabilities (`supports_cancel`, `supports_partial_results`, `max_shots`, `backend_family`).
   - Provider-specific credentials/config are loaded through a typed driver config schema.

2. **Kernel runtime policy contract**
   - Timeout is kernel-enforced and yields deterministic terminal state.
   - Cancellation becomes two-step: `CANCEL_REQUESTED -> CANCELLED|ERROR`.
   - Retry policy applies only to classified retriable failures and is bounded.

3. **Public API behavior**
   - Existing `status/results/watch` UX remains backward compatible.
   - Additional metadata fields may be returned for runtime policy diagnostics (attempt count, terminal reason category).

### Data Models

1. **Runtime state record extensions**
   - `attempt`, `max_attempts`
   - `cancel_requested_at`
   - `timeout_deadline`
   - `terminal_reason_category`

2. **Result artifact layout v2**
   - `result.json` (normalized output)
   - `metadata.json` (timestamps, backend identifiers, runtime policy outcomes)
   - optional provider raw payload (sanitized) for diagnostics.

3. **Storage abstraction**
   - Read/write via backend-agnostic storage interface (local + object store).
   - Artifact version is immutable per successful terminalization.

### Security and Privacy

- Provider credentials must not be logged or persisted into public artifacts.
- Raw provider payload inclusion is opt-in and sanitized.
- Runtime traces/logs retain diagnostic value while redacting sensitive parameters.
- Cancellation and retry control endpoints must enforce existing authz/authn boundaries.

### Observability

Required metric families:

- runtime stage duration histogram (`compile`, `queue`, `execute`, `persist`)
- retries by reason and terminal outcome
- cancellation and timeout counters
- result persistence success/failure counters

Required trace/log fields:

- `trace_id`, `job_id`, `attempt`
- provider/backend identifier
- terminal state and reason category
- storage artifact version identifier

### Performance

- Retry backoff must remain bounded and policy-configurable.
- Additional observability must avoid unbounded cardinality.
- Storage writes should use append/commit semantics to reduce partial artifact exposure.
- Phase 1 blocking checks should remain within practical PR CI time limits.

## Testing Plan

- External provider adapter contract tests (mock + fixture driven).
- Timeout/cancel integration tests with deterministic terminalization assertions.
- Retry matrix tests for retriable/non-retriable/operator-action errors.
- Storage backend contract tests (local and object-storage-compatible mode).
- Observability v2 assertions for required metrics/trace fields/log schema.

## Implementation / Migration

1. Add provider adapter interfaces and baseline implementation for one external provider.
2. Extend kernel state machine and runtime policy engine for timeout/cancel/retry semantics.
3. Introduce storage abstraction and artifact layout v2 with backward-compatible readers.
4. Update reference docs and fixture sets for new runtime policy metadata.
5. Promote Phase 1 tests/gates to required status checks.
6. Record closure in ADR package when Phase 1 exits draft/implementation.

## Considered Alternatives

- **Provider-owned retry/cancel logic only**: rejected; breaks deterministic platform semantics.
- **Keep local-only artifact storage for Phase 1**: rejected; insufficient for practical deployment.
- **Observability enhancements as non-blocking guidance**: rejected; too risky for production runtime claims.

## Open Questions

- Which object storage consistency assumptions are mandatory vs best-effort?
- Should partial results be exposed in public API during cancellation windows?
- Which external-provider smoke checks are PR-blocking vs scheduled/nightly?
- Do we require per-tenant quota hooks in Phase 1 or defer entirely to Phase 2?
