# Phase 1 — Production Runtime Plan

## Status

- **Phase**: 1 (Post-MVP)
- **Planning status**: Active
- **Last updated**: 2026-04-26
- **Primary RFC**: [`../../rfcs/0019-phase1-production-runtime-plan.md`](../../rfcs/0019-phase1-production-runtime-plan.md)
- **Release checklist**: [`phase-1-release-readiness-checklist.md`](phase-1-release-readiness-checklist.md)

## Why this phase exists

MVP-3 froze a deterministic simulator runtime contract (`sim:local`) and release gates.
Phase 1 extends that baseline into a production-oriented runtime that can execute against external hardware providers, survive transient failures, and persist durable artifacts with stronger observability.

## Scope (in)

1. **External hardware driver path (initial provider: IBM/Qiskit Runtime)**
   - Introduce provider-backed driver capability declarations.
   - Add backend capability discovery and readiness checks.
   - Preserve stable internal `kernel -> driver-manager` execution contract semantics.

2. **Runtime reliability hardening**
   - Timeout policy and deterministic cancellation semantics.
   - Retry policy for safe transient failures (bounded + observable).
   - Idempotency guarantees at submission/execution boundary.

3. **Durable result storage and retrieval**
   - Object-storage-compatible result writer/reader abstraction (S3-like API model).
   - Versioned result artifact layout and metadata durability checks.
   - Backward-compatible behavior for local/simulator development mode.

4. **Observability v2 for operations**
   - Per-job lifecycle timeline visibility.
   - Stage-level latency metrics (`compile`, `queue`, `execute`, `persist`).
   - Expanded correlation fields for debugging cross-service failures.

## Scope (out)

- Scheduler fairness/quotas and multi-tenant policy (Phase 2).
- Multi-device orchestration and batch optimization (Phase 2).
- Benchmarking platform and datasets (Phase 3).
- ML-driven backend selection/scheduling (Phase 4).

## Exit criteria (Definition of Done)

Phase 1 is considered complete when all items below are true:

1. End-to-end `submit -> watch -> results` succeeds on at least one external provider backend in CI/staging.
2. Failure-path matrix is deterministic for timeout, cancellation, and retry-exhausted conditions.
3. Result persistence supports object-storage mode with immutable versioned artifacts.
4. Observability v2 metrics/traces/log fields are documented and validated by automated tests.
5. Required CI gates are updated and enforced in branch protection.

## Workstreams and deliverables

### A. Provider Driver Integration

- Driver-manager provider adapter interface.
- Provider credential/config loading contract.
- Capability probing endpoint + cache policy.
- Conformance fixture set for provider submit/status/result mapping.

### B. Runtime Semantics and Policies

- State-machine extension for `CANCEL_REQUESTED` and timeout transitions.
- Retry classification matrix (`retriable`, `non-retriable`, `operator-action`).
- Public error mapping updates for policy-driven failures.

### C. Storage Upgrade

- QFS-compatible storage abstraction with local and object backends.
- Artifact manifest (`result.json`, `metadata.json`, optional raw provider payload).
- Read-after-write consistency checks in integration tests.

### D. Observability v2

- Metric set and label contract.
- Trace span taxonomy for critical runtime stages.
- Structured logging field baseline for incident triage.

## CI and quality gates (target)

1. **External backend smoke (success path)**
2. **External backend smoke (failure path)**
3. **Cancellation + timeout contract tests**
4. **Retry policy conformance tests**
5. **Object storage persistence contract tests**
6. **Observability v2 assertions (metrics + traces + logs)**
7. **Contract compatibility suite (JobSpec/AQO/QFS version markers + conformance)**

## Proposed milestone cadence

- **M1 (foundation)**: provider adapter scaffolding, timeout/cancel contract draft, storage abstraction interfaces.
- **M2 (integration)**: external backend happy-path E2E, artifact versioning, observability v2 baseline.
- **M3 (hardening)**: retry matrix closure, failure-path determinism, CI gate promotion.
- **M4 (freeze)**: release-readiness checklist + ADR closure package.

## Risks and mitigations

1. **Provider API instability**
   - Mitigation: adapter isolation layer + fixture-based contract tests.
2. **Flaky external backend CI**
   - Mitigation: deterministic mocks for PR-blocking checks, scheduled live backend validation.
3. **Storage consistency edge cases**
   - Mitigation: immutable artifact naming + explicit write/commit protocol.
4. **Observability cardinality growth**
   - Mitigation: bounded label sets and governance in review checklist.

## Dependencies

- RFC 0016/0017/0018 baseline contracts.
- Security posture from ADR 0007.
- Provider SDK/legal constraints for external execution APIs.

## Cross-links

- Post-MVP roadmap: [`post-mvp-open-source-roadmap.md`](post-mvp-open-source-roadmap.md)
- MVP-3 closure: [`mvp-3-execution-and-results.md`](mvp-3-execution-and-results.md)
- RFC pointer page: [`../rfcs-pointer.md`](../rfcs-pointer.md)
