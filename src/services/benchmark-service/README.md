# benchmark-service

Phase-3 benchmark core service for run lifecycle contract `1.0.0` and comparison contract `1.0.0`.

## Run lifecycle state machine (v1)

```text
PENDING -> PREPARING -> RUNNING -> SUCCEEDED
                        \-> FAILED
PENDING/PREPARING/RUNNING -> CANCELLED
```

Terminal states: `SUCCEEDED`, `FAILED`, `CANCELLED`.

## Contract guarantees

- Idempotent `start_run(idempotency_key)`.
- Idempotent `retry_run(run_id, retry_key)` from `FAILED|CANCELLED`.
- Immutable run snapshot with explicit `contract_version` and `snapshot_version`.
- Deterministic snapshot payload canonicalization (`json.dumps(..., sort_keys=True)`).

## Dataset ingestion contract (QSBench-compatible)

Dataset manifest schema version: `1.0.0`.

Ingestion guarantees:

- Manifest schema validation with structured error payloads (`code`, `field`, `message`).
- Provenance validation via required `source_uri` and `source_checksum`.
- Bundle checksum verification for `source_file`.
- Dataset catalog registration with queryable versions per dataset.

## Benchmark Run API contract (`/benchmarks/run`)

- Stable request/response envelope with SemVer marker `api_version: 1.0.0`.
- Error envelope aligned with public conventions: `error.code`, `error.message`, `error.details[]`.
- Contract fixture tests enforce required field stability in CI.

## Benchmark Compare API contract (`/benchmarks/compare`)

- Deterministic comparison output for identical inputs.
- Request model compares `baseline` vs `candidate` with optional `cohort_filters`.
- Output includes per-metric deltas (`absolute`, `percent`) and statistical metadata (`z_score`, `standard_error`, `confidence`).
- Regression flags are policy-based using threshold and confidence gates.
- Mandatory SemVer markers in comparison artifacts:
  - `api_version: 1.0.0`
  - `comparison_schema_version: 1.0.0`
  - `methodology.methodology_version: 1.0.0`

## Phase-3 change log discipline

For every Phase-3 PR, include:

- **Version impact**: additive `/benchmarks/compare` feature, package version raised to `0.4.0`.
- **Compatibility**: backward-compatible addition; existing `/benchmarks/run` and dataset contracts unchanged.
- **Migration notes**: clients can adopt `/benchmarks/compare` without changes to existing run lifecycle integrations.
