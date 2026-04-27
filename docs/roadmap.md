This roadmap is aligned with the current MVP definition and tracks the minimum milestones required for an end-to-end release.

## Current delivery focus

- ✅ **MVP-1 (Core Services Setup)** completed: repository skeleton, public contracts, service stubs, QRTX/Driver Manager/QFS scaffolding, and CI baseline.
- ✅ **MVP-2 (Compilation Pipeline)** completed: JobSpec parser/validator, Eigen-Lang AST→AQO compiler hardening, CLI `eigen submit`, and conformance suites.
- Detailed MVP-2 execution plan: [`development/mvp-2-compilation-pipeline.md`](development/mvp-2-compilation-pipeline.md)
- ✅ MVP-3 (Execution & Results Pipeline) completed; closure record: [`development/mvp-3-execution-and-results.md`](development/mvp-3-execution-and-results.md)
- MVP-3 RFC package (accepted): [`../rfcs/0016-mvp3-kernel-driver-execution-contract.md`](../rfcs/0016-mvp3-kernel-driver-execution-contract.md), [`../rfcs/0017-mvp3-results-retrieval-and-cli-runtime-ux.md`](../rfcs/0017-mvp3-results-retrieval-and-cli-runtime-ux.md), [`../rfcs/0018-mvp3-runtime-observability-and-release-gates.md`](../rfcs/0018-mvp3-runtime-observability-and-release-gates.md)
- Post-MVP open-source roadmap: [`development/post-mvp-open-source-roadmap.md`](development/post-mvp-open-source-roadmap.md)
- Phase 1 release readiness checklist: [`development/phase-1-release-readiness-checklist.md`](development/phase-1-release-readiness-checklist.md)
- Phase 1 RFC (implemented): [`../rfcs/0019-phase1-production-runtime-plan.md`](../rfcs/0019-phase1-production-runtime-plan.md)
- MVP-3 ADR package: [`adr/0007-mvp3-release-readiness-runtime-contracts-and-security-closure.md`](adr/0007-mvp3-release-readiness-runtime-contracts-and-security-closure.md)
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

## Milestone 3 — CLI and developer workflow (completed)

- ✅ Finalized CLI MVP commands (`submit`, `status`, `results`, `watch`).
- ✅ Documented packaging and reproducible local execution flow.
- ✅ Kept examples and quickstarts synchronized with current contracts.

## Milestone 4 — Quality and observability gates (completed)

- ✅ Enforced unit + smoke integration coverage for core services.
- ✅ Verified metrics exposure and trace propagation across service boundaries.
- ✅ Validated error handling and conformance fixtures in CI.

## Milestone 5 — MVP release readiness (completed)

- ✅ Completed MVP Definition of Done checklist for all in-scope services.
- ✅ Confirmed docs and governance artifacts are up to date.
- ✅ MVP baseline is frozen after MVP-3 closure; post-MVP planning is now active.

## Out of scope for MVP (tracked after release)

- Real hardware backends
- Advanced scheduler fairness/quotas
- Web dashboard
- Multi-node high availability
- Advanced optimization passes

## Milestone 6 — Phase 1 production runtime (completed)

- ✅ External provider driver integration baseline (IBM/Qiskit Runtime path).
- ✅ Timeout, cancellation, and retry policy hardening in runtime state machine.
- ✅ Object-storage-compatible artifact persistence and retrieval semantics.
- ✅ Observability v2 rollout with stage latency and timeline visibility.
- ✅ Release readiness checklist closed; product version advanced to `0.2.0`

## Milestone 7 — Phase 2 orchestration layer (completed)

- ✅ Scheduler core: priority queues, quotas, and baseline fairness policies.
- ✅ Device-aware scheduling using latency/calibration/availability signals.
- ✅ Multi-device and batch orchestration contracts and guardrails.
- ✅ Operational controls for orchestration SLOs and rebalancing safety.
- ✅ Release readiness checklist, compatibility package, and migration notes completed.
- ✅ Product version advanced to `0.3.0`.
