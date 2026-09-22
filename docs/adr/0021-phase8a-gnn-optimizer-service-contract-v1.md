# ADR 0021: Phase-8A GNN Optimizer Service Contract v1

- **Status**: Accepted
- **Date**: 2026-05-16
- **Decision owners**: Optimizer/Compiler, Architecture/Governance
- **Supersedes / Related**: RFC 0035, ADR 0018, ADR 0019

## Context

Phase-8A requires a stable optimizer service contract to prevent interface drift and to preserve deterministic behavior expectations across replay and regression gates. RFC 0035 defines the normative optimizer contract v1.

## Decision

Adopt RFC 0035 as the operational baseline for optimizer service contract v1:

1. Optimizer request/response contract is SemVer-governed as a stable service interface.
2. Deterministic seed and fallback semantics are required and testable through fixtures.
3. Performance and trace fields used by downstream observability pipelines are required contract members.
4. CI contract gates must block undocumented breaking schema/behavior drift.

## Consequences

- Optimizer integration remains predictable across compile/execute workflows.
- Reproducible optimization behavior is enforceable in CI replay gates.
- Service evolution remains compatible-by-default unless explicitly marked MAJOR with migration notes.

## Verification and evidence

- RFC source: `rfcs/0035-phase8a-gnn-optimizer-service-contract-v1.md`
- Synchronization pointers: `docs/rfcs-pointer.md`, `docs/development/README.md`
- Phase-8A closure docs: gap analysis, readiness checklist, compatibility report
