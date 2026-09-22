# Phase-4 Compatibility Report

- **Status:** Signed for Phase-4 release readiness.
- **Last updated:** 2026-04-28
- **Owner:** Intelligent runtime maintainers
- **Release line:** `0.9.0`

## Contract version matrix

Version matrix is **locked** for the `0.9.0` release line.

| Contract surface | Current version | Compatibility notes |
| --- | --- | --- |
| Backend scoring contract | `1.0.0` | Breaking score/tie-break semantics require MAJOR bump. |
| Scoring profile schema | `1.0.0` | Removing required profile fields requires MAJOR bump. |
| Scheduling policy contract | `1.0.0` | Priority ladder or fallback semantic changes require MAJOR bump. |
| Policy bundle schema | `1.0.0` | Additive optional policy metadata is MINOR-only when backward compatible. |
| Explainability API contract | `1.0.0` | Explain envelope semantic changes or required-field removals require MAJOR bump. |

## Compatibility suite evidence

- Scoring contract suite: `cargo test -p resource-manager scoring_contract`
- Policy engine contract suite: `cargo test -p resource-manager policy_contract`
- Explainability API suite: `pytest src/services/system-api/tests/test_explain_api_contract.py`
- Runtime decision determinism suite: `scripts/ci/check-runtime-decision-determinism.sh`
- Golden fixture review gate: `golden-fixtures-approved` label required when stable contract fixtures change.

## Versioning policy compliance

Phase-4 contracts follow mandatory SemVer governance:

1. **MAJOR** for incompatible decision semantics, explanation envelope, or policy resolution changes.
2. **MINOR** for backward-compatible optional fields and additive explainability metadata.
3. **PATCH** for fixes only (no public decision semantic changes).
4. Mandatory version markers in decision artifacts and explain responses.
5. Deprecation policy: field removal only after one MINOR release with deprecation marker.

## Migration policy

Every Phase-4 contract-affecting PR must include:

1. **Version impact** (`MAJOR`/`MINOR`/`PATCH`/`NONE`)
2. **Compatibility** statement in the PR description
3. **Migration notes** (actionable steps or explicit `None`)

## Release readiness

Compatibility package and ADR synchronization package are signed. Phase-4 release gate can be marked **Ready**.
