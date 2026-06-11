# ADR 0045 — Product 1.0 Queue Delivery and Dead-Letter Semantics

## Status

Proposed

## Context

Product 1.0 Wave 5 requires deterministic queue delivery semantics that can be
replayed, audited, and aligned with scheduling/reservation recovery behavior.
The repository already has a provider-neutral in-memory queue adapter with
lease, ack, requeue, redelivery, and dead-letter behavior, but the governing
contract needs to be explicit.

## Decision

1. Queue ownership belongs to the runtime task envelope.
2. Lease acquisition is bounded by visibility timeout and is deterministic for
   identical normalized inputs.
3. Acknowledgement is worker-owned and removes the lease from in-flight state.
4. Requeue is worker-owned and either redelivers the task or dead-letters it
   when the retry budget is exhausted.
5. Expired leases are swept deterministically before subsequent delivery work.
6. Dead-letter terminalization is a terminal state, not a soft retry state.
7. Replay order for equivalent inputs MUST remain stable.

## Consequences

- Queue delivery can be tested and replayed deterministically.
- Dead-letter records become the terminal evidence for exhausted retry budgets.
- Queue behavior remains compatible with the current Resource Manager MVP while
  preserving a clear target contract for Product 1.0.
- Scheduling and reservation recovery can reason about queue expiry/redelivery
  without hidden state.

## Compliance notes

- Any future public API surface for queue control must preserve this contract or
  bump the relevant MAJOR version.
- Observability markers and manifest entries should reference this ADR.
