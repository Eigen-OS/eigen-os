# ADR 0019: Phase-7 Developer Experience and Conformance Toolchain Baseline v1

- **Status**: Accepted
- **Date**: 2026-04-29
- **Deciders**: Eigen OS maintainers
- **Consulted**: Developer Experience, CI owners, Documentation owners
- **Informed**: Contributors and release managers
- **Related RFC**: [RFC 0033](../../rfcs/0033-phase7-developer-experience-and-conformance-toolchain-baseline-v1.md)

## Context

Phase-7 requires deterministic contributor workflows and conformance gates that prevent contract drift while keeping iteration speed acceptable.

A split between default blocking checks and nightly extended checks is needed to balance safety and developer throughput.

## Decision

Adopt a Phase-7 DX baseline with:

1. One canonical local baseline command (`scripts/dev/run-tooling-baseline.sh`).
2. Blocking CI gates for contract drift, migration-note checks, compatibility fixtures, and canonical docs smoke checks.
3. Nightly non-blocking full docs sweeps and extended snippet validation.

Track CI failure classes under:

- `contract_drift`
- `compatibility_regression`
- `docs_smoke_failure`

## Consequences

### Positive

- New contributors have a deterministic local workflow.
- Critical contract and docs regressions are caught earlier in default CI.
- Nightly expansion reduces false-positive pressure on PR velocity.

### Trade-offs

- Requires ongoing ownership of docs-smoke and fixture maintenance.
- Adds governance overhead when changing baseline gates.

## Implementation Notes

- Normative DX baseline source: RFC 0033.
- `docs/development/README.md` and `docs/rfcs-pointer.md` must stay synchronized with gate definitions and lifecycle status.
