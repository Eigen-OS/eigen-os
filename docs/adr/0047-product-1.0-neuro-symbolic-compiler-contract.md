# ADR 0047 — Product 1.0 Neuro-Symbolic Compiler Contract

## Status

Accepted

## Context

Product 1.0 requires a deterministic compiler boundary for Eigen-Lang and AQO generation.

## Decision

The compiler contract is frozen at the Product 1.0 boundary with deterministic lowering, stable error mapping, and replay-safe artifact metadata.

## Consequences

- compiler outputs become contract-bound,
- compiler errors become standardized,
- artifact lineage becomes part of the release evidence.
