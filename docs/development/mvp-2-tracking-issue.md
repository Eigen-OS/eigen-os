# Issue: MVP-2 tracking — Compilation Pipeline

- **Type**: Tracking issue
- **Created**: 2026-04-24
- **Owner**: Core maintainers
- **Related RFCs**: [RFC 0013](../../rfcs/0013-mvp2-jobspec-parser-submit-contract.md), [RFC 0014](../../rfcs/0014-mvp2-eigen-lang-ast-safety-deterministic-aqo.md), [RFC 0015](../../rfcs/0015-mvp2-conformance-and-ci-gates.md)
- **Related ADRs**: [ADR 0003](../adr/0003-mvp2-jobspec-parser-contract.md), [ADR 0004](../adr/0004-mvp2-eigen-lang-ast-safety.md), [ADR 0005](../adr/0005-mvp2-conformance-and-ci-gates.md)

## Goal

Launch MVP-2 with deterministic submit → compile → execute flow on `sim:local`, covering JobSpec validation, Eigen-Lang AST safety, AQO determinism, and mandatory CI gates.

## Scope

1. JobSpec `job.yaml` parser/validator with canonical `SubmitJobRequest` mapping.
2. Eigen-Lang AST-only compiler path with strict allowlist and deterministic AQO v0.1 output.
3. CLI `eigen submit` request packaging + API compatibility checks.
4. Conformance fixtures and blocking CI quality gates.

## Work breakdown

### A) JobSpec parser and contract mapping

- [ ] Finalize required/optional field matrix for JobSpec v0.1.
- [ ] Add deterministic fixtures (`job.yaml` -> expected request payload).
- [ ] Enforce field-level `INVALID_ARGUMENT` diagnostics.
- [ ] Add parser tests to CI required checks.

### B) Eigen-Lang AST safety and deterministic AQO

- [ ] Freeze MVP allowlist/forbidden constructs.
- [ ] Enforce AST structural limits (nodes/depth/input size).
- [ ] Ensure deterministic AQO serialization and hash stability.
- [ ] Add golden + negative conformance test sets.

### C) CLI submit packaging

- [ ] Validate `-f/--file` flow and explicit program override rules.
- [ ] Ensure SHA-256 packaging is deterministic and tested.
- [ ] Verify request envelope against mock/fake System API.
- [ ] Verify clear user-facing failures for validation/API errors.

### D) CI and release readiness gates

- [ ] Mark conformance jobs as required for merge.
- [ ] Require explicit review on golden fixture changes.
- [ ] Keep smoke checks (`submit -> results`) green in CI.
- [ ] Run MVP-2 readiness audit before freeze.

## Exit criteria

- [ ] RFC 0013 moved from `Draft` to `Accepted`.
- [ ] RFC 0014 moved from `Draft` to `Accepted`.
- [ ] RFC 0015 moved from `Draft` to `Accepted`.
- [ ] MVP-2 checklist in `mvp-2-compilation-pipeline.md` fully closed.
- [ ] Documentation (`reference/`, tutorials, development docs) synchronized with implementation.

## Notes for GitHub issue creation

Use this file as the body for GitHub issue titled:

`MVP-2 tracking: compilation pipeline readiness`