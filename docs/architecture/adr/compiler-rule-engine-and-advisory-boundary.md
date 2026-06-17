# ADR: Deterministic rule engine with advisory-only neuro-symbolic assistance

- **Status:** Accepted
- **Date:** 2026-06-17
- **Scope:** Compiler service and compiler-facing neuro-symbolic boundary

## Context

The compiler now has a deterministic semantic rule engine, workload-family profile resolution, and a neuro-symbolic component that can score, rank, or explain candidate rewrites.

The compiler boundary must remain deterministic. Advisory output cannot be the source of truth for legality, lowering, or AQO validity.

## Decision

Use the deterministic rule engine as the only authority for compiler legality and lowering preconditions.

Allow the neuro-symbolic layer to operate only as an advisory component that may:

- propose rewrite candidates,
- rank alternatives,
- emit heuristic hints,
- explain why a compiler action was suggested.

The advisor must not:

- override rule-engine approval,
- generate valid compiler IR on its own,
- change pass ordering or pass membership,
- bypass semantic validation,
- relax lowering constraints.

## Consequences

- Compiler failures remain attributable to deterministic stages and rules.
- Advisor influence must be recorded explicitly as accepted, rejected, or transformed into a deterministic compiler action.
- Advisor components can be swapped or disabled without breaking the compiler contract.
- AQO remains unchanged at v1.0.0; the contract change is in compiler metadata and diagnostics, not the IR schema.

## Notes

This ADR is the architectural home for the compiler rule engine, pass pipeline, workload-family profiles, and advisory-only neuro-symbolic boundary.
