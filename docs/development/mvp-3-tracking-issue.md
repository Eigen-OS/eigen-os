# MVP-3 tracking: execution and results pipeline readiness

- **Type**: Tracking issue
- **Created**: 2026-04-25
- **Owner**: Core maintainers
- **Related RFCs**: [RFC 0016](../../rfcs/0016-mvp3-kernel-driver-execution-contract.md), [RFC 0017](../../rfcs/0017-mvp3-results-retrieval-and-cli-runtime-ux.md), [RFC 0018](../../rfcs/0018-mvp3-runtime-observability-and-release-gates.md)
- **Related ADRs**: [ADR 0007](../adr/0007-mvp3-release-readiness-runtime-contracts-and-security-closure.md)

## Goal

Launch MVP-3 with deterministic compile → execute → results flow on `sim:local`, covering kernel lifecycle closure, driver execution contract, stable result retrieval, CLI runtime UX, and mandatory observability/CI gates.

## Current status

✅ **Closed on 2026-04-25**. All MVP-3 exit criteria are satisfied; this document is retained as an implementation ledger.

## Scope

1. Kernel runtime state machine closure and idempotent terminalization semantics.
2. Driver-manager simulator execution contract for MVP AQO subset.
3. Deterministic results persistence/retrieval contract (`GetJobResults` + QFS artifacts).
4. CLI `status/watch/results` UX behavior aligned with terminal lifecycle semantics.
5. Runtime observability assertions and blocking CI release gates.

## Work breakdown

### A) Kernel runtime + driver execution contract (RFC 0016)
- [x] Freeze lifecycle transition rules and enforce terminal idempotency (`PENDING -> COMPILING -> RUNNING -> DONE|ERROR|CANCELLED|TIMEOUT`).
  - **Branch**: `feat/kernel-mvp3-lifecycle-freeze`
  - **Commit**: `feat(kernel): freeze mvp3 lifecycle transitions and terminalization guard`
- [x] Harden kernel `ExecuteCircuit` dispatch boundaries and canonical internal error mapping.
  - **Branch**: `feat/kernel-driver-dispatch-contract`
  - **Commit**: `feat(kernel): enforce driver dispatch contract and runtime error mapping`
- [x] Expand driver-manager simulator contract tests for MVP op subset and unsupported payload behavior.
  - **Branch**: `test/driver-manager-mvp3-contract`
  - **Commit**: `test(driver-manager): add mvp3 simulator contract and unsupported-path tests`

### B) Results persistence/retrieval + CLI runtime UX (RFC 0017)
- [x] Freeze QFS runtime artifact paths and deterministic result serialization conventions.
  - **Branch**: `feat/results-qfs-contract`
  - **Commit**: `feat(results): freeze qfs runtime artifact contract for mvp3`
- [x] Implement deterministic `GetJobResults` behavior for `DONE`, not-ready, and failed-terminal states.
  - **Branch**: `feat/api-results-semantics`
  - **Commit**: `feat(api): implement deterministic getjobresults mvp3 semantics`
- [x] Align CLI `status/watch/results` terminal handling, exit codes, and user-facing diagnostics.
  - **Branch**: `feat/cli-runtime-ux-mvp3`
  - **Commit**: `feat(cli): align runtime status watch results ux with mvp3 contracts`
- [x] Add e2e fixtures for success/failure terminal jobs with repeated result retrieval stability checks.
  - **Branch**: `test/runtime-results-fixtures`
  - **Commit**: `test(e2e): add mvp3 runtime results stability fixtures`

### C) Runtime observability + CI gates (RFC 0018)
- [x] Promote runtime smoke checks (success + failure paths) to required CI jobs.
  - **Branch**: `chore/ci-mvp3-runtime-gates`
  - **Commit**: `ci: mark mvp3 runtime smoke gates as required`
- [x] Add telemetry assertions for trace propagation and required metrics labels across runtime path.
  - **Branch**: `test/runtime-observability-assertions`
  - **Commit**: `test(observability): enforce mvp3 trace and metric correlation assertions`
- [x] Standardize runtime fixture/golden update workflow and explicit review requirements.
  - **Branch**: `chore/runtime-fixture-governance`
  - **Commit**: `chore(ci): add runtime fixture governance and review controls`
- [x] Run MVP-3 readiness audit before freeze.
  - **Branch**: `docs/mvp3-readiness-audit`
  - **Commit**: `docs: complete mvp3 runtime release readiness audit`

## Exit criteria

- [x] RFC 0016 moved from `Draft` to `Accepted`.
- [x] RFC 0017 moved from `Draft` to `Accepted`.
- [x] RFC 0018 moved from `Draft` to `Accepted`.
- [x] MVP-3 checklist in `mvp-3-execution-and-results.md` fully closed.
- [x] Runtime documentation (`reference/`, tutorials, development docs) synchronized with implementation.
- [x] MVP-3 ADR package created and linked from `docs/adr/README.md`.
