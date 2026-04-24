# MVP-2 — Compilation Pipeline Plan

Status: **In Progress**  
Last updated: **2026-04-24**

## Goal

Deliver a deterministic and testable compilation path from `job.yaml` + `program.eigen.py` to a valid `SubmitJobRequest` and AQO v0.1 payload, with CLI submission flow wired to `System API`.

## Scope of MVP-2

### 1) JobSpec v0.1 parser and validator

Deliver a library/service that:

- reads `job.yaml`,
- validates required and constrained fields,
- produces canonical `SubmitJobRequest` protobuf.

#### Validation baseline

- `apiVersion` must match MVP (`eigen.os/v0.1`).
- program descriptor and source references are required.
- quantum resource constraints (qubits/shots/device target) are validated.
- semantic consistency checks (entrypoint, file references, format) are enforced.

#### Acceptance criteria

- For a known fixture `job.yaml`, output protobuf is byte-stable/logically identical to expected fixture.
- Validation failures map to `INVALID_ARGUMENT` with actionable field-level messages.
- Unit tests cover positive and negative fixture sets.

---

### 2) Eigen-Lang compiler (AST → AQO)

Deliver Python compiler service that:

- parses source via `ast.parse` (no runtime execution),
- enforces MVP language restrictions,
- generates deterministic AQO v0.1 JSON (`RX`, `RY`, `RZ`, `CX`, `MEASURE`).

#### Mandatory safety and determinism checks

- exactly one `@hybrid_program` entrypoint,
- AST structural limits (max nodes, max depth),
- forbid unsupported constructs (for example unrestricted imports, `exec`, direct I/O),
- deterministic AQO serialization (stable ordering and formatting).

#### Acceptance criteria

- Golden tests verify deterministic AQO for multiple valid programs.
- Invalid programs fail with `INVALID_ARGUMENT` and clear diagnostic reason.
- Conformance suite runs in CI and is required for merge.

---

### 3) CLI command `eigen submit`

Deliver Rust CLI flow that:

- packages `job.yaml` + `program.eigen.py`,
- computes SHA-256,
- builds and sends `SubmitJobRequest` to `System API`,
- prints `job_id` on success.

#### Required options

- `-f, --file` for JobSpec path,
- `--wait` for terminal status waiting mode,
- `--proxy` for API endpoint override,
- explicit program path override when not colocated with `job.yaml`.

#### Acceptance criteria

- Integration test against mock/fake API validates outgoing request shape.
- CLI output test captures `stdout` and verifies `job_id` rendering.
- Non-zero exit and clear message on validation/API errors.

---

### 4) Unit and conformance tests

#### Minimum coverage gate

- Eigen-Lang → AQO conformance set: **at least 5 programs** (sequential + parallel chains).
- JobSpec → SubmitJobRequest fixture set with deterministic assertions.

#### Acceptance criteria

- Tests run automatically in CI.
- AQO output and RPC payload assertions are deterministic.
- Negative tests verify rejection and status/error mapping.

## Delivery checklist

- [ ] JobSpec parser/validator merged with fixtures.
- [ ] Compiler AST validator + AQO generator merged.
- [ ] `eigen submit` end-to-end request packaging merged.
- [ ] Conformance suites (positive/negative) enabled in CI.
- [ ] Documentation updated in `docs/reference/` and tutorials.

## Suggested execution order

1. JobSpec parser fixtures and protobuf parity tests.
2. Compiler AST validator + deterministic AQO fixtures.
3. CLI submit wiring and mock API contract tests.
4. CI gate hardening and docs synchronization.

## Related documents

- MVP roadmap: [`../roadmap.md`](../roadmap.md)
- MVP scope: [`../requirements/mvp-scope.md`](../requirements/mvp-scope.md)
- Eigen-Lang references: [`../reference/eigen-lang/README.md`](../reference/eigen-lang/README.md)
- JobSpec reference: [`../reference/jobspec.md`](../reference/jobspec.md)
- ADR index: [`../adr/README.md`](../adr/README.md)
- MVP-2 ADRs: [`../adr/0003-mvp2-jobspec-parser-contract.md`](../adr/0003-mvp2-jobspec-parser-contract.md), [`../adr/0004-mvp2-eigen-lang-ast-safety.md`](../adr/0004-mvp2-eigen-lang-ast-safety.md), [`../adr/0005-mvp2-conformance-and-ci-gates.md`](../adr/0005-mvp2-conformance-and-ci-gates.md)
