# RFC 0032: Phase-7 API and Contract Versioning Policy v1

- **Status**: Accepted
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-29
- **Target Milestone**: Phase 7
- **Tracking Issue**: P7-01 (docs/development/phase-7-issue-pack.md)

## Summary

Defines a unified versioning and deprecation policy across public API, CLI envelopes, plugin-facing contracts, and compatibility manifests.

## Goals

- Standardize SemVer behavior and change classification.
- Define minimum deprecation/support windows.
- Require migration-note artifacts for breaking changes.

## Policy

1. `MAJOR`: incompatible contract semantics or removals.
2. `MINOR`: backward-compatible additions with deterministic defaults.
3. `PATCH`: non-semantic bug fixes only.

Deprecation lifecycle:

- `Announced` in release notes and migration notes.
- `Warned` by tooling/CLI diagnostics during the support window.
- `Removed` only in `MAJOR` with migration guidance after support-window closure.

Deprecation support window:

- Deprecated interfaces remain supported for **2 minor releases or 90 days, whichever is longer**.
- After the window closes, removal is allowed only with an explicit RFC/ADR update and migration notes.

## Test plan

- Fixture tests for compatibility matrix parser/evaluator.
- CI check for migration-note presence when breaking markers are present.
- Snapshot tests for rejection reason outputs.

## Compatibility and versioning

- **Version impact:** policy artifact `1.1.0` (adds explicit CI/pr-marker enforcement rules).
- **Migration notes:** mandatory on every breaking change proposal.

## Open questions

- Minimum supported window length by component tier (core vs auxiliary tooling).

## Implementation status

- PR template includes explicit `Breaking Marker` and contract interfaces taxonomy.
- CI migration gate fails closed on undocumented breaking markers.
- Dev/RFC pointers link to this policy as the normative source.
