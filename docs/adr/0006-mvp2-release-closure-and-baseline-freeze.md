# ADR 0006: MVP-2 release closure and baseline freeze

- **Status:** Accepted
- **Date:** 2026-04-24
- **Deciders:** Core architecture maintainers

## Context

MVP-2 scope is completed across parser contracts, AST-safe compilation, deterministic AQO output, CLI submission packaging, and required CI conformance gates. The repository needs an explicit architecture record that formalizes MVP-2 closure and defines what is considered the stable baseline for subsequent work.

## Decision

1. MVP-2 is declared complete with ADR 0003, ADR 0004, and ADR 0005 treated as normative implementation baseline.
2. The stable MVP-2 baseline consists of:
   - deterministic `JobSpec -> SubmitJobRequest` mapping,
   - AST-only Eigen-Lang compilation with safety limits,
   - deterministic AQO v0.1 serialization,
   - required parser/compiler/CLI conformance gates in CI.
3. Any behavior-changing modification to MVP-2 contracts after this point must include:
   - an RFC (or RFC amendment) for rationale,
   - an ADR update/new ADR when accepted,
   - synchronized fixture/test updates in the same change set.
4. Post-MVP-2 work should be treated as incremental evolution (MVP-2.x / MVP-3 planning) without silently redefining accepted MVP-2 guarantees.

## Consequences

- Teams have a single formal checkpoint that MVP-2 is closed and operationally frozen at the contract level.
- Change governance for parser/compiler/CLI contracts becomes explicit and auditable.
- Future roadmap items can build on a stable baseline without ambiguity around MVP-2 acceptance criteria.

## Related

- MVP-2 plan: `docs/development/mvp-2-compilation-pipeline.md`
- ADR 0003: `docs/adr/0003-mvp2-jobspec-parser-contract.md`
- ADR 0004: `docs/adr/0004-mvp2-eigen-lang-ast-safety.md`
- ADR 0005: `docs/adr/0005-mvp2-conformance-and-ci-gates.md`