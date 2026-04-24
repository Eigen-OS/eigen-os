# MVP-2 tracking: compilation pipeline readiness

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

### A) JobSpec parser and contract mapping (RFC 0013)
- [ ] Finalize required/optional field matrix for JobSpec v0.1 and implement canonical mapping to `SubmitJobRequest`.
  - **Branch**: `feat/jobspec-v0.1-mapping`
  - **Commit**: `feat(parser): implement SubmitJobRequest canonical mapping for v0.1`
- [ ] Enforce field-level `INVALID_ARGUMENT` diagnostics, path traversal blocks, and size caps.
  - **Branch**: `feat/jobspec-security-diagnostics`
  - **Commit**: `feat(parser): enforce field diagnostics and security boundaries`
- [ ] Add deterministic positive and negative fixtures (`job.yaml` -> expected request payload).
  - **Branch**: `test/jobspec-fixtures`
  - **Commit**: `test(parser): add deterministic positive and negative jobspec fixtures`

### B) Eigen-Lang AST safety and deterministic AQO (RFC 0014)
- [ ] Freeze MVP allowlist/forbidden constructs (block `exec`, `eval`, dynamic I/O) and enforce exactly one `@hybrid_program`.
  - **Branch**: `feat/ast-allowlist-policy`
  - **Commit**: `feat(compiler): enforce AST allowlist and entrypoint constraints`
- [ ] Enforce AST structural limits (node counts, depth limits, input size).
  - **Branch**: `feat/ast-structural-limits`
  - **Commit**: `feat(compiler): apply structural safety limits to AST parser`
- [ ] Ensure deterministic AQO serialization (stable key ordering) and hash stability.
  - **Branch**: `feat/aqo-determinism`
  - **Commit**: `feat(compiler): ensure deterministic AQO v0.1 JSON serialization`
- [ ] Add golden + negative conformance test sets for the compiler.
  - **Branch**: `test/compiler-conformance`
  - **Commit**: `test(compiler): implement golden and negative AST conformance suites`

### C) CLI submit packaging
- [ ] Validate `-f/--file` flow and explicit program override rules.
  - **Branch**: `feat/cli-submit-flow`
  - **Commit**: `feat(cli): implement explicit file flow and program overrides`
- [ ] Ensure SHA-256 packaging is deterministic and tested.
  - **Branch**: `feat/cli-deterministic-packaging`
  - **Commit**: `feat(cli): make source packaging and hashing deterministic`
- [ ] Verify request envelope against mock/fake System API and ensure clear user-facing failures.
  - **Branch**: `test/cli-api-integration`
  - **Commit**: `test(cli): verify request envelopes and error handling via mock API`

### D) CI and release readiness gates (RFC 0015)
- [ ] Mark conformance jobs (parser, compiler, CLI) as required for merge.
  - **Branch**: `chore/ci-required-gates`
  - **Commit**: `ci: mark MVP-2 conformance and smoke jobs as required`
- [ ] Implement tooling for golden fixture updates and require explicit review on changes.
  - **Branch**: `chore/golden-fixture-tooling`
  - **Commit**: `chore(ci): add golden fixture update script and review rules`
- [ ] Keep smoke checks (`submit -> results`) green in CI, including trace/metrics validation.
  - **Branch**: `test/smoke-observability`
  - **Commit**: `test(ci): ensure smoke tests validate metrics and trace context`
- [ ] Run MVP-2 readiness audit before freeze.
  - **Branch**: `docs/mvp2-audit`
  - **Commit**: `docs: complete MVP-2 release readiness audit`

## Exit criteria

- [x] RFC 0013 moved from `Draft` to `Accepted`.
- [x] RFC 0014 moved from `Draft` to `Accepted`.
- [x] RFC 0015 moved from `Draft` to `Accepted`.
- [x] MVP-2 checklist in `mvp-2-compilation-pipeline.md` fully closed.
- [x] Documentation (`reference/`, tutorials, development docs) synchronized with implementation.
