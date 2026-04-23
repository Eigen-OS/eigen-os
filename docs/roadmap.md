This roadmap is aligned with the current MVP definition and tracks the minimum milestones required for an end-to-end release.

## Milestone 1 — API and contract baseline

- Stabilize public gRPC services (`JobService`, `DeviceService`) for MVP workflows.
- Freeze internal service contracts between kernel, compiler, and driver manager.
- Validate canonical error mapping and structured error details.

## Milestone 2 — End-to-end MVP execution

- Deliver submit → compile → execute → results flow on `sim:local`.
- Ensure deterministic AST-only compilation to AQO for MVP subset.
- Complete job lifecycle transitions and cancellation behavior in kernel/QRTX.

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
