# RFC 0046 — Phase-8D Externalization Surfaces Contract v1

- **Status:** Accepted
- **Date:** 2026-05-19
- **Owner:** System API + Developer Surfaces
- **Version:** 1.0.0
- **Phase:** 8D

## Summary

This RFC formalizes Phase-8D externalization surfaces: System API REST parity obligations and non-GA developer surface skeleton contracts (dashboard, VS Code, Jupyter).

## Contract decisions

1. REST submit/watch/results/cancel parity checks are required release gates.
2. Provider metadata exposure in REST is additive with deterministic defaults.
3. Dashboard, VS Code, and Jupyter artifacts remain explicitly non-GA in this phase.
4. Compatibility matrix links MUST be published from development/governance indexes.
5. Any surface-breaking behavior requires MAJOR + migration notes.

## Versioning and compatibility

- **Version impact:** MINOR
- **Breaking marker:** false
- **Migration notes:** None

## Required evidence

- REST parity report.
- Surface demo/walkthrough evidence.
- Governance pointer synchronization (`docs/development/README.md`, `docs/rfcs-pointer.md`, `docs/adr/README.md`).

## References

- `docs/development/phase-8d/phase-8d-execution-plan.md`
- `docs/development/phase-8d/phase-8d-exit-evidence-bundle.md`
