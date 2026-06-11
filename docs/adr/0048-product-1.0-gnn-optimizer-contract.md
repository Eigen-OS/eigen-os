# ADR 0048 — Product 1.0 GNN Optimizer Contract

## Status

Accepted

## Context

Product 1.0 requires a stable optimizer contract for graph-based optimization decisions.

## Decision

The optimizer contract is frozen with deterministic scoring, explicit fallback behavior, and explainability metadata.

## Consequences

- optimizer decisions become reproducible,
- confidence reporting becomes explicit,
- trace continuity is part of the contract surface.
