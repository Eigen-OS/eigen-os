# ADR 0049: Product 1.0 Optimizer Production Path

- Status: Accepted
- Date: 2026-06-12
- Deciders: Core maintainers
- RFC: `rfcs/0051-product-1.0-optimizer-production-path.md`

## Context

Wave 7a is the implementation bridge that moves the optimizer from fixture-backed coverage into the production execution path without redesigning the frozen optimizer contract.

## Decision

Adopt RFC 0051 as the governance baseline for Wave 7a implementation. Wave 7a issues must preserve contract shape, add deterministic fallback, emit optimization candidate traces, and maintain bounded observability labels.

## Consequences

- The optimizer becomes operational in the production path.
- The contract remains stable for downstream consumers.
- Any metric rename or removals require normal breaking-change handling.
