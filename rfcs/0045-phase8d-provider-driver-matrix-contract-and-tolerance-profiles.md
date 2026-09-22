# RFC 0045 — Phase-8D Provider Driver Matrix Contract and Tolerance Profiles

- **Status:** Accepted
- **Date:** 2026-05-19
- **Owner:** Driver Manager + Reliability
- **Version:** 1.0.0
- **Phase:** 8D

## Summary

This RFC defines the official provider matrix contract (`simulator`, `ibm`, `aws`), tolerance profile governance, and incident/rollback policy hooks used by release gates.

## Contract decisions

1. Official provider matrix is versioned and published as a compatibility artifact.
2. Tolerance limits are governed by a versioned fixture and enforced in CI.
3. Provider incidents require documented pin/quarantine/demotion rollback controls.
4. Nightly conformance history (>=14 days) is required for closure evidence.
5. Matrix contract changes require SemVer discipline and drift gate updates.

## Versioning and compatibility

- **Version impact:** MINOR
- **Breaking marker:** false
- **Migration notes:** None

## Required evidence

- Provider conformance/parity/tolerance reports.
- Rollback rehearsal evidence and incident drill records.
- Compatibility matrix artifact + changelog linkage.

## References

- `docs/development/phase-8d/phase-8d-release-readiness-checklist.md`
- `docs/development/phase-8d/phase-8d-exit-evidence-bundle.md`
- `docs/development/fixtures/phase8d/rollback_rehearsal_matrix_v1.json`
