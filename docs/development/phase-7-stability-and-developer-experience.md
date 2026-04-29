# Phase-7: Stability & Developer Experience

- **Status:** Planning
- **Date:** 2026-04-29
- **Scope:** API stability, compatibility guarantees, developer onboarding/tooling, and CI quality hardening.

## Goal

Make Eigen-OS easier to adopt and contribute to while preserving deterministic runtime and contract-first evolution.

## Fixed policy decisions (2026-04-29)

- Deprecated interfaces remain supported for **2 minor releases or 90 days, whichever is longer**.
- Removal after deprecation window is allowed only with explicit RFC/ADR updates and migration notes.

## Delivery themes

1. **Stable contracts and compatibility guarantees**
   - API/versioning policy with explicit SemVer and deprecation windows.
   - Runtime + CLI + SDK compatibility matrix and support windows.
2. **Developer experience baseline**
   - End-to-end docs refresh for new contributors and plugin developers.
   - Opinionated examples that map to real adoption scenarios.
3. **Quality gates and release confidence**
   - Stronger CI coverage with deterministic fixture discipline.
   - Conformance expansion for language/runtime/plugin compatibility paths.

## Primary artifacts for Phase-7

- RFC 0032: API and contract versioning policy.
- RFC 0033: Developer experience and conformance toolchain baseline.
- Issue pack: `phase-7-issue-pack.md`.
- Governance check: `phase-7-rfc-adr-gap-analysis.md`.
- Execution closure docs (to be created during implementation):
  - `phase-7-release-readiness-checklist.md`
  - `phase-7-compatibility-report.md`

## Exit criteria

Phase-7 is considered complete when:

1. Phase-7 RFC package is **Accepted** and linked in pointers/roadmap docs.
2. ADR synchronization is done for implemented RFC decisions.
3. Compatibility policy is published and tested with deterministic fixtures.
4. CI gates include expanded conformance and migration-note checks.
5. Developer docs/tutorial examples are updated and validated via smoke checks.
