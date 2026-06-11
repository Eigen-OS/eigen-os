# ADR 0043 — Product 1.0 Queue Delivery and Recovery Semantics

## Status

Proposed

## Decision

Queue delivery semantics shall define leases, acknowledgements, redelivery, dead-letter behavior, and recovery on replay.

## Consequences

- deterministic retry behavior,
- clear lease expiry handling,
- stable dead-letter semantics,
- no implicit delivery guarantees beyond the contract.
