# ADR 0042 — Product 1.0 Distributed Execution Split / Merge Policy

## Status

Proposed

## Decision

Distributed execution must use deterministic split-plan manifests and replay-safe merge semantics.

## Consequences

- stable shard identity,
- stable merge validation,
- partial-failure visibility,
- artifact lineage preserved in QFS.
