# RFC 0027: Phase-5 Distributed Queue and Delivery Semantics v1

- **Status**: Implemented
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-28
- **Accepted on**: 2026-04-28
- **Implemented on**: 2026-04-28
- **Target Milestone**: Phase 5
- **Tracking Issue**: P5-08 (docs/development/phase-5-issue-pack.md)
- **Replaces / Related**: RFC 0026, docs/development/phase-5-distributed-execution.md

## Summary

This RFC defines a pluggable queue abstraction and delivery contract for distributed execution, including lease/ack/requeue/dead-letter behavior and idempotency requirements.

## Motivation

Distributed execution requires a queue layer that can switch providers without changing runtime semantics. Delivery guarantees and retry behavior must be explicit for correctness.

## Goals

- Standardize queue adapter interface across providers.
- Define delivery semantics baseline (`at-least-once`) and idempotency contract.
- Specify deterministic lease timeout, redelivery, and dead-letter behavior.

## Non-Goals

- Exactly-once semantics in v1.
- Global ordering across all tenants and queues.
- Queue provider benchmarking framework.

## Guide-level Explanation

The control plane publishes a task to a queue adapter. A worker acquires a lease, executes with an idempotency key, and acknowledges completion. Lease expiration may re-deliver work; duplicates are safe.

## Reference-level Design

### Queue contract envelope (v1)

- `queue_contract_version: "1.0.0"`
- `task_id`
- `job_id`
- `assignment_id`
- `idempotency_key`
- `lease_id`
- `attempt`
- `visibility_timeout_seconds`
- `enqueued_at`

### Required adapter operations

- `enqueue(task)`
- `lease(queue, worker_id)`
- `ack(lease_id)`
- `requeue(lease_id, reason)`
- `dead_letter(task_id, reason)`

### Delivery semantics

- Baseline guarantee: **at-least-once**.
- Idempotency key is mandatory and must be preserved across retries.
- Lease expiration returns task to queue with incremented `attempt`.
- Tasks exceeding `max_attempts` must transition to dead-letter queue.

## Interfaces / APIs

- Internal runtime queue adapter API (provider-neutral).
- Control-plane hooks to emit queue events in trace/metrics pipelines.

## Data Models

- `QueueTaskEnvelope`
- `LeaseRecord`
- `DeadLetterRecord`

## Security and Privacy

- Queue payloads must avoid direct embedding of secret material.
- Provider credentials should be managed via existing secret management paths.
- Tenant isolation tags are mandatory in queue task metadata.

## Observability

Required metrics:

- `queue_enqueued_total`
- `queue_lease_acquired_total`
- `queue_redelivery_total`
- `queue_dead_letter_total`
- `queue_lease_latency_ms`

Required logs/events:

- lease acquired/released
- redelivery reason
- dead-letter reason

## Performance

- Queue-to-lease p95 target: `< 2s`.
- Ack path should remain sub-100ms p95 under nominal load.

## Benchmarking/Test Plan

- Adapter conformance suite against in-memory + external provider.
- Replay tests for lease expiration and redelivery determinism.
- Failure-injection tests for ack timeout and provider transient errors.

## Implementation / Migration

1. Introduce provider-neutral queue adapter interface.
2. Implement local in-memory adapter for development.
3. Implement first production-like adapter.
4. Add compatibility fixtures and CI gate.

Migration notes:

- Current in-process dispatch path maps to local adapter with same semantics.

## Compatibility and Versioning

- **Version impact:** New queue contract surface with `1.0.0` baseline.
- **Compatibility:** Non-cluster mode remains operational through local adapter mapping.
- **Migration notes:** Deployments with external queues must configure visibility timeout and DLQ policy.

## Considered Alternatives

- Exactly-once delivery via distributed transactions: rejected for complexity/cost in v1.
- Provider-specific direct integrations only: rejected due to lock-in and contract drift.

## Open Questions

- Default dead-letter retention and replay tooling ownership.
