This roadmap is aligned with the current MVP definition and tracks the minimum milestones required for an end-to-end release.

## Current delivery focus (as of 2026-04-24)

- ✅ **MVP-1 (Core Services Setup)** completed: repository skeleton, public contracts, service stubs, QRTX/Driver Manager/QFS scaffolding, and CI baseline.
- ✅ **MVP-2 (Compilation Pipeline)** completed: JobSpec parser/validator, Eigen-Lang AST→AQO compiler hardening, CLI `eigen submit`, and conformance suites.
- Detailed MVP-2 execution plan: [`development/mvp-2-compilation-pipeline.md`](development/mvp-2-compilation-pipeline.md)
- MVP-2 RFC package (implemented): [`../rfcs/0013-mvp2-jobspec-parser-submit-contract.md`](../rfcs/0013-mvp2-jobspec-parser-submit-contract.md), [`../rfcs/0014-mvp2-eigen-lang-ast-safety-deterministic-aqo.md`](../rfcs/0014-mvp2-eigen-lang-ast-safety-deterministic-aqo.md), [`../rfcs/0015-mvp2-conformance-and-ci-gates.md`](../rfcs/0015-mvp2-conformance-and-ci-gates.md)

## Milestone 1 — API and contract baseline

- Stabilize public gRPC services (`JobService`, `DeviceService`) for MVP workflows.
- Freeze internal service contracts between kernel, compiler, and driver manager.
- Validate canonical error mapping and structured error details.

## Milestone 2 — End-to-end MVP execution (MVP-2 completed)

- Deliver submit → compile → execute → results flow on `sim:local`.
- Ensure deterministic AST-only compilation to AQO for MVP subset.
- Add a fixture-driven JobSpec→`SubmitJobRequest` parser/validator gate.
- Enforce conformance tests for Eigen-Lang→AQO and CLI submit request packaging.

## Milestone 3 — CLI and developer workflow

- Finalize CLI MVP commands (`submit`, `status`, `results`, `watch`).
- Document packaging and reproducible local execution flow.
- Keep examples and quickstarts synchronized with current contracts.

## Milestone 4 — Quality and observability gates

- Enforce unit + smoke integration coverage for core services.
- Verify metrics exposure and trace propagation across service boundaries.
- Validate error handling and conformance fixtures in CI.

## Milestone 5 — MVP release readiness

- Complete MVP Definition of Done checklist for all in-scope services.
- Confirm docs and governance artifacts are up to date.
- Tag MVP release and start post-MVP planning for hardware drivers and advanced scheduling.

## Out of scope for MVP (tracked after release)

- Real hardware backends
- Advanced scheduler fairness/quotas
- Web dashboard
- Multi-node high availability
- Advanced optimization passes
