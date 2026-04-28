# ADR 0015 — Phase-5 distributed queue and delivery semantics v1

- **Status**: Accepted
- **Date**: 2026-04-28
- **Deciders**: Eigen OS maintainers
- **Supersedes / Related**: RFC 0027, ADR 0014

## Context

Phase-5 needs a provider-neutral distributed queue contract with deterministic lease/retry behavior. RFC 0027 is implemented and defines queue envelope fields, at-least-once delivery guarantees, idempotency requirements, and dead-letter semantics.

## Decision

1. Adopt distributed queue and delivery contract baseline `1.0.1`.
2. Require mandatory queue contract markers in task/lease/dead-letter artifacts:
   - `queue_contract_version`
   - `lease_event_version`
   - `dead_letter_contract_version`
3. Freeze v1 delivery semantics:
   - baseline guarantee is **at-least-once**;
   - `idempotency_key` is mandatory and preserved across retries;
   - lease expiration triggers deterministic redelivery with incremented `attempt`.
4. Require deterministic terminal handling:
   - tasks beyond retry cap MUST transition to dead-letter artifacts with explicit reason metadata;
   - duplicate deliveries MUST be replay-safe and non-destructive.
5. Govern queue contract evolution with SemVer:
   - incompatible delivery/lease semantics => `MAJOR`
   - additive optional queue metadata => `MINOR`
   - deterministic replay/order fixes without contract break => `PATCH`

## Consequences

### Positive

- Queue providers can be swapped without changing delivery behavior guarantees.
- Retry and dead-letter operations become predictable and testable.
- Determinism gates can detect replay drift before release.

### Trade-offs

- Queue adapters have stricter conformance requirements.
- Operators must manage retry budgets and dead-letter policies explicitly.

## Evidence package

- RFC: `rfcs/0027-phase5-distributed-queue-and-delivery-semantics-v1.md`
- Implementation:
  - `src/rust/crates/resource-manager/src/queue/mod.rs`
  - `src/rust/crates/resource-manager/src/queue/providers/in_memory.rs`
  - `src/rust/crates/resource-manager/tests/distributed_queue_contract_tests.rs`

## Rollout / governance

- This ADR is the normative implementation record for Phase-5 queue/delivery contract closure.
- Any incompatible delivery semantic change requires synchronized RFC+ADR updates and MAJOR planning.
- Phase-5 release closure requires this ADR plus signed compatibility and readiness package.
