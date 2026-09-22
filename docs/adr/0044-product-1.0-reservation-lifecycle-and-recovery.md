# ADR 0044 — Product 1.0 Reservation Lifecycle and Recovery Semantics

## Status

Proposed

## Context

The public `DeviceService.ReserveDevice` RPC exists today as a compatibility
surface, but the repository still needs deterministic, replay-safe reservation
state with expiry, renewal, recovery after restart, and auditable persistence.

## Decision

1. The `purpose` field is the stable binding handle for reservation lineage.
2. Identical normalized reservation inputs renew the same reservation lineage.
3. Active reservations on the same device reject double booking.
4. Expired reservations are swept deterministically and remain restorable from
   the persisted reservation store.
5. Reservation state is persisted as a compatibility bridge and mirrored to QFS
   evidence artifacts for audit/replay.

## Consequences

- Reservation behavior becomes deterministic for replay.
- Restart recovery rehydrates active reservations from the persisted store.
- Double booking is rejected instead of being silently overwritten.
- The public proto remains unchanged while the internal lifecycle semantics are
  tightened for Product 1.0.

## Compliance notes

- This ADR applies to the current compatibility bridge and does not claim that
  a standalone Resource Manager service already exists.
- Any future public RPC for explicit release/extend semantics must preserve the
  version policy and compatibility rules.
