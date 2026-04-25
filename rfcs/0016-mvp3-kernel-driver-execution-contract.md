# RFC 0016: MVP-3 Kernel Runtime and Driver Execution Contract

- **Status**: Draft
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-25
- **Target Milestone**: Phase 0 (MVP-3)
- **Tracking Issue**: docs/development/mvp-3-tracking-issue.md
- **Replaces / Related**: RFC 0006, RFC 0015, docs/development/mvp-3-execution-and-results.md

## Summary

Define the MVP-3 runtime contract for deterministic execution lifecycle from accepted submit envelope to terminal job state on `sim:local`, including `kernel -> driver-manager` interaction semantics.

## Motivation

MVP-2 completed deterministic submission and compilation. MVP-3 must freeze runtime behavior so that execution transitions, error mapping, and simulator contract are predictable for both API consumers and CI gates.

## Goals

- Freeze allowed job lifecycle transitions and terminalization semantics in kernel runtime.
- Define `ExecuteCircuit` execution contract for simulator target `sim:local`.
- Require deterministic terminal status outcomes for stable polling and watch UX.
- Standardize canonical runtime error mapping between internal and public boundaries.

## Non-Goals

- Multi-node scheduling fairness and queue preemption policy.
- Hardware backend support beyond MVP simulator driver.
- Performance SLOs for distributed deployments.

## Guide-level Explanation

For MVP-3, each job must move through a bounded runtime lifecycle:

1. `PENDING`
2. `COMPILING`
3. `RUNNING`
4. Terminal: `DONE | ERROR | CANCELLED | TIMEOUT`

Terminalization is idempotent: once terminal state is persisted, no later write can change terminal outcome.

Kernel invokes driver-manager only after successful compile artifact resolution. Driver-manager must accept AQO v0.1 payload for the MVP subset (`RX`, `RY`, `RZ`, `CX`, `MEASURE`) and return normalized `counts` output with execution metadata.

## Reference-level Design

## Interfaces / APIs

- Internal RPC: `DriverManagerService.ExecuteCircuit` is invoked by kernel with:
  - `job_id`
  - target (`sim:local` for MVP-3)
  - AQO payload + metadata
- Runtime error mapping:
  - invalid payload / unsupported operation -> `INVALID_ARGUMENT` or `UNIMPLEMENTED` (frozen per validation boundary)
  - transient backend unavailability -> `UNAVAILABLE`
  - backend capacity pressure -> `RESOURCE_EXHAUSTED`

## Data Models

- Runtime state record per `job_id` includes:
  - current state
  - `created_at`, `started_at`, `finished_at`
  - terminal `error_code` / `error_message` when failed
  - correlation fields (`trace_id`, `job_id`, optional `driver_id`)

## Security and Privacy

- Kernel and driver-manager do not execute arbitrary user code at runtime stage.
- Execution inputs are pre-validated artifacts from compile stage.
- Runtime logs must avoid leaking sensitive payload bodies while preserving diagnostics.

## Observability

- Trace propagation required across `system-api -> kernel -> driver-manager`.
- Metrics baseline includes:
  - state transition counters
  - execution duration histogram
  - terminal error counters by canonical code
- Structured logs include `{job_id, trace_id, state, component}`.

## Performance

- Runtime orchestrator should avoid duplicate driver submissions on retry boundaries.
- State transition persistence must be O(1) relative to number of historical events.
- Deterministic terminalization is prioritized over speculative throughput optimizations.

## Testing Plan

- Kernel state-machine integration tests for valid and invalid transitions.
- Driver-manager contract tests for MVP op subset and unsupported paths.
- E2E smoke tests verifying stable terminal status across repeated polls.
- Failure-mode tests proving idempotent terminal writes.

## Implementation / Migration

1. Freeze state machine transition table and terminalization guard.
2. Harden driver-manager simulator execution contract and error normalization.
3. Add deterministic runtime fixtures for successful and failing jobs.
4. Promote runtime execution smoke checks to required CI gates.

## Considered Alternatives

- **Terminal state mutation for retries**: rejected (breaks deterministic API semantics).
- **Driver-managed state transitions**: rejected (kernel must remain lifecycle authority).

## Open Questions

- Should timeout terminalization be controlled solely by kernel or shared with API layer policy?
- Do we need a dedicated internal status code for simulator deterministic mismatch errors?
