# Phase 1 — Release Readiness Checklist

## Status

- **Owner**: Runtime/Release maintainers
- **Last updated**: 2026-04-26
- **Scope**: Phase-1 production runtime release gate

## 1) Versioning & Compliance Shield

- [ ] Stable contracts use SemVer (`MAJOR.MINOR.PATCH`).
- [ ] Breaking public-contract changes require **MAJOR** bump and migration notes.
- [ ] Backward-compatible contract extensions (new optional fields) use **MINOR**.
- [ ] **PATCH** is bug-fix only (no public semantic change).
- [ ] JobSpec includes explicit version marker (`apiVersion`).
- [ ] AQO includes explicit version marker (`version`).
- [ ] QFS metadata includes explicit version marker (`version`).
- [ ] Every PR includes:
  - [ ] `Version Impact` section.
  - [ ] `Affected Interfaces` section.
  - [ ] `Migration Notes` section.

## 2) Consolidated Release Gates

### Security

- [ ] Credential redaction and secret-handling checks pass.
- [ ] Authn/Authz controls are validated for runtime control endpoints.
- [ ] Security scan workflow passes for release branch.

### Performance

- [ ] Stage latency budgets are measured (`compile`, `queue`, `execute`, `persist`).
- [ ] No regression above agreed thresholds versus previous baseline.
- [ ] Retry and cancellation policies are bounded and observable.

### Documentation

- [ ] Public contract docs are synchronized (JobSpec/AQO/QFS/API).
- [ ] Upgrade/migration notes are published.
- [ ] Release notes include a versioning-impact section.

### Upgrade Notes

- [ ] Operators have explicit rollout/rollback instructions.
- [ ] Data/artifact compatibility notes are documented.
- [ ] Any required migration tooling is released and linked.

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

- [ ] All Phase-1 issues are closed and verified.
- [ ] Migration tools/notes are ready for existing users.
- [ ] Version matrix above is unchanged (or updated via approved MAJOR/MINOR process).
