# P9A-06 — CI Fail-Closed Gates (SAST/DAST/SBOM/Drift/Fault Injection)

## Required blocking jobs on `main`

Stage-9A branch protection for `main` must require the following GitHub Actions jobs:

1. `sast-gate` — static analysis across Python/Rust sources via Bandit + Semgrep.
2. `dast-gate` — OWASP ZAP baseline scan against `src/services/system-api/openapi.yaml`.
3. `sbom-gate` — CycloneDX SBOM generation plus Trivy vulnerability gate (HIGH/CRITICAL fail).
4. `contract-drift-gate` — manifest-backed contract drift detection (`scripts/ci/check-contract-drift.py`).
5. `migration-notes-gate` — PR template SemVer/migration policy enforcement.
6. `phase9a-ci-gate-bundle` — deterministic failure-injection and fail-closed conformance suite.

## Fail-closed policy

- Any failing required job blocks merge.
- Contract drift without manifest update remains blocked until versioning metadata and migration notes are aligned.
- Security regressions (SAST/DAST/SBOM) and fault-injection failures are release blockers for Stage-9A.

## Deterministic fault-injection suite coverage

`phase9a-ci-gate-bundle` executes:

- system-api fail-closed auth-context test;
- driver-manager profile-matrix, rollback-governance, and tolerance drift fail-closed tests;
- CLI plugin trust fail-closed test;
- runtime deterministic replay gate.

This suite is deterministic by construction (fixture-anchored tests + replay assertions) and required for Stage-9A release readiness.
