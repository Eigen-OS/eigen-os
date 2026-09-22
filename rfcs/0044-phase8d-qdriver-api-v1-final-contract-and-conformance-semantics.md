# RFC 0044 — Phase-8D QDriver API v1 Final Contract and Conformance Semantics

- **Status:** Accepted
- **Date:** 2026-05-19
- **Owner:** Runtime + Driver Manager
- **Version:** 1.0.0
- **Phase:** 8D

## Summary

This RFC freezes the QDriver API v1.0 contract, canonical conformance assertions, and fail-closed behavior for unsupported capabilities across official providers (`simulator`, `ibm`, `aws`).

## Contract decisions

1. QDriver capability descriptors are additive-only for minor versions.
2. Unsupported operations MUST return stable, documented error classes.
3. Conformance requires pass for submit/watch/results/cancel lifecycle semantics.
4. Tolerance-aware parity checks MUST use the versioned policy artifact.
5. Contract drift checks MUST fail closed in CI.

## Versioning and compatibility

- **Version impact:** MINOR
- **Breaking marker:** false
- **Migration notes:** None

## Required evidence

- Conformance suite report across official provider matrix.
- Contract drift check output for QDriver/API projection surfaces.
- Compatibility matrix update with changelog entry.

## References

- `docs/development/phase-8d/phase-8d-compatibility-report.md`
- `docs/development/phase-8d/phase-8d-exit-evidence-bundle.md`
- `docs/development/fixtures/phase8d/provider_tolerance_policy_v1.json`
