# ADR 0018: Phase-7 API and Contract Versioning Policy v1

- **Status**: Accepted
- **Date**: 2026-04-29
- **Deciders**: Eigen OS maintainers
- **Consulted**: Runtime, CLI, Plugin SDK, Release Engineering
- **Informed**: Contributors and integrators
- **Related RFC**: [RFC 0032](../../rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md)

## Context

Phase-7 closure requires a single operational policy for contract versioning and deprecation handling across public APIs, CLI payloads, plugin-facing envelopes, compatibility matrix artifacts, and CI governance.

Without one policy baseline, compatibility regressions can be merged without explicit migration guidance.

## Decision

Adopt SemVer as mandatory for all stable contract surfaces and enforce the following:

1. `MAJOR` for incompatible behavior, field removals, and semantics changes.
2. `MINOR` for additive backward-compatible changes with deterministic defaults.
3. `PATCH` for non-semantic fixes (bug fixes, docs fixes, observability tuning).

Deprecation lifecycle is fixed to:

- Support deprecated interfaces for **2 minor releases or 90 days, whichever is longer**.
- Emit diagnostics during support window.
- Remove only in a `MAJOR` release after explicit RFC/ADR update plus migration notes.

CI must fail closed on undocumented contract drift and missing migration notes for breaking markers.

## Consequences

### Positive

- Governance and implementation teams share one deterministic versioning baseline.
- Breaking changes become auditable by policy metadata and migration notes.
- Compatibility matrix becomes a versioned artifact with fixture-based protections.

### Trade-offs

- Contributors must classify changes and update release metadata on every contract touch.
- Additional CI gates increase initial maintenance overhead.

## Implementation Notes

- Normative policy source: RFC 0032.
- PR/release notes must include version-impact and breaking-marker fields.
- Compatibility matrix updates are required to be fixture-tested in CI.
