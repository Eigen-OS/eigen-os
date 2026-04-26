# Phase 1 — Release Readiness Checklist

## Status

- **Owner**: Runtime/Release maintainers
- **Last updated**: 2026-04-26
- **Scope**: Phase-1 production runtime release gate
- **Release decision**: ✅ Ready (all gate artifacts linked below)

## 1) Versioning & Compliance Shield

- [x] Stable contracts use SemVer (`MAJOR.MINOR.PATCH`).
- [x] Breaking public-contract changes require **MAJOR** bump and migration notes.
- [x] Backward-compatible contract extensions (new optional fields) use **MINOR**.
- [x] **PATCH** is bug-fix only (no public semantic change).
- [x] JobSpec includes explicit version marker (`apiVersion`).
- [x] AQO includes explicit version marker (`version`).
- [x] QFS metadata includes explicit version marker (`version`).
- [x] Every PR includes:
  - [x] `Version Impact` section.
  - [x] `Affected Interfaces` section.
  - [x] `Migration Notes` section.

Evidence:
- SemVer policy and changelog process: `CHANGELOG.md`.
- Mandatory PR metadata sections: `.github/PULL_REQUEST_TEMPLATE.md`.
- Contract version markers: `docs/reference/jobspec.md`, `docs/reference/formats/aqo.md`, `docs/reference/formats/qfs-layout.md`.

## 2) Consolidated Release Gates

### Security

- [x] Credential redaction and secret-handling checks pass.
- [x] Authn/Authz controls are validated for runtime control endpoints.
- [x] Security scan workflow passes for release branch.

### Performance

- [x] Stage latency budgets are measured (`compile`, `queue`, `execute`, `persist`).
- [x] No regression above agreed thresholds versus previous baseline.
- [x] Retry and cancellation policies are bounded and observable.

### Documentation

- [x] Public contract docs are synchronized (JobSpec/AQO/QFS/API).
- [x] Upgrade/migration notes are published.
- [x] Release notes include a versioning-impact section.

### Upgrade Notes

 [x] Operators have explicit rollout/rollback instructions.
- [x] Data/artifact compatibility notes are documented.
- [x] Any required migration tooling is released and linked.

Evidence:
- Security and authz baseline: `SECURITY.md`, `docs/architecture/components/security-isolation.md`.
- Performance/observability baseline: `docs/development/phase-1-production-runtime.md`.
- Migration and compatibility guidance: `docs/development/phase-1-migration-notes.md`.
- Release note structure with versioning impact: `.github/PULL_REQUEST_TEMPLATE.md`.

## 3) Compatibility Test Suite (merge-blocking)

Run the canonical suite:

```bash
scripts/test/run-contract-compatibility-suite.sh
```

Gate is green only when all contract checks pass for:

- JobSpec parser conformance
- AQO simulator/driver contract checks
- QFS metadata/version contract checks

## 4) Supported Version Matrix (locked for Phase 1)

| Contract | Supported in Phase 1 | Notes |
|---|---|---|
| JobSpec | `eigen.os/v0.1` | `apiVersion` is mandatory |
| AQO | `0.1` | top-level `version` is mandatory |
| QFS metadata schema | `0.1` + schema tags `source_artifacts.v1` / `compiled_artifacts.v1` | `version` is mandatory |

## 5) Exit Conditions

- [x] All Phase-1 issues are closed and verified.
- [x] Migration tools/notes are ready for existing users.
- [x] Version matrix above is unchanged (or updated via approved MAJOR/MINOR process).
