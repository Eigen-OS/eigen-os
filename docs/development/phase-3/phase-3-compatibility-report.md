# Phase-3 Compatibility Report

- **Status:** Signed for Phase-3 release readiness.
- **Last updated:** 2026-04-27
- **Owner:** Benchmarking maintainers
- **Release line:** `0.8.0`

## Contract version matrix

Version matrix is **locked** for the `0.8.0` release line.

| Contract surface | Current version | Compatibility notes |
| --- | --- | --- |
| Benchmark run lifecycle contract | `1.0.0` | Breaking state-machine/idempotency behavior requires MAJOR bump. |
| Dataset manifest schema | `1.0.0` | Required field removals/changes require MAJOR bump. |
| Dataset ingestion contract | `1.0.0` | Optional metadata additions are MINOR-only when backward compatible. |
| Comparison contract | `1.0.0` | Delta/regression semantics changes require MAJOR bump. |
| Methodology contract | `1.0.0` | Methodology metadata remains mandatory and versioned. |
| History contract | `1.0.0` | Ordering and cursor semantics are part of public contract. |

## Compatibility suite evidence

- Run lifecycle contract suite: `pytest src/services/benchmark-service/tests/test_run_lifecycle.py`
- Dataset ingestion contract suite: `pytest src/services/benchmark-service/tests/test_dataset_ingestion.py`
- Compare contract suite: `pytest src/services/benchmark-service/tests/test_compare_contract.py`
- History contract suite: `pytest src/services/benchmark-service/tests/test_history_contract.py`
- Golden fixture review gate: `golden-fixtures-approved` label required when stable contract fixtures change.

## Versioning policy compliance

Phase-3 contracts follow mandatory SemVer governance:

1. **MAJOR** for incompatible payload/state-machine/semantic changes.
2. **MINOR** for backward-compatible optional fields/metadata.
3. **PATCH** for fixes only (no public benchmark semantic changes).
4. Mandatory version markers in run snapshots, comparison outputs, and history entries.
5. Deprecation policy: field removal only after one MINOR release with deprecation marker.

## Migration policy

Every contract-affecting PR must include:

1. **Version Impact** (`MAJOR`/`MINOR`/`PATCH`/`NONE`)
2. **Compatibility** statement in the PR description
3. **Migration Notes** (actionable steps or explicit `None`)

## Release readiness

Compatibility package and ADR synchronization package are signed. Phase-3 release gate can be marked **Ready**.
