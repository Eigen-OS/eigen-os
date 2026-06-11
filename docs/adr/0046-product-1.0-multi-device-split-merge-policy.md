# ADR 0046 — Product 1.0 Multi-device Split / Merge Policy

## Status

Proposed

## Context

The multi-device execution contract already defines replay-safe split planning,
shard identity, partial result and failure envelopes, and merge validation.
Product 1.0 Wave 5 needs the implementation and contract inventory to reflect a
single authoritative split/merge policy rather than a placeholder-compatible
shape.

## Decision

1. Split plans use versioned manifests with caller-supplied `created_at_ms` and
   `trace_id`.
2. Shard plans carry deterministic identity and replay metadata, including
   `attempt`, optional lease timeout, optional resource profile, and lineage ref.
3. Partial result and partial failure envelopes preserve the same parent/shard
   lineage and are sorted deterministically before merge validation.
4. `MergeDecision` is the canonical validation artifact; the final result
   persistence layer MUST use the same shard ordering and lineage references.
5. Single-device compatibility paths remain represented as a one-shard split
   plan and MUST not use a separate placeholder contract.

## Consequences

- Split/merge behavior can be replayed and compared deterministically.
- Contract inventory can mark the multi-device execution surface as implemented.
- Current single-device execution remains compatible without inventing a
  parallel "special case" contract.

## Follow-up

- Keep the resource-manager contract inventory row in sync with this ADR.
- Keep the multi-device execution contract doc as the normative reference.
- Preserve the golden fixtures for both current and previous manifest baselines.
