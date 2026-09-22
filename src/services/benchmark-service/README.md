# benchmark-service

Phase-3 benchmark core service for run lifecycle contract `1.0.0`, comparison contract `1.0.0`, and benchmark observability contract `1.0.0`.

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

## Benchmark History API contract (`/benchmarks/history`)

- Deterministic pagination with opaque cursor token (`page_token`) and bounded `page_size` in `[1, 100]`.
- Stable ordering guarantee is part of the public contract: `created_at DESC, run_id ASC`.
- Mandatory query validation: `time_range.start_at`, `time_range.end_at`, optional `filters.states[]`, and optional `filters.dataset`.
- Trend-oriented aggregates per query window:
  - `trend.total_runs`, `trend.terminal_runs`, `trend.success_rate`
  - `trend.state_counts`
  - `trend.daily[]` (`run_count`, `success_count`, `failure_count`, `cancelled_count`)
- Version markers:
  - `api_version: 1.0.0`
  - `query_version: 1.0.0`
  - history entries keep explicit `history_entry_version`.

## Reproducibility and determinism gate (P3-08)

- Reproducibility gate policy version: `1.0.0`.
- Thresholds:
  - `min_runs: 3`
  - `max_relative_stddev_pct: 2.0`
  - `max_absolute_stddev: 0.005`
- Gate validates:
  - deterministic snapshot metadata (`snapshot.request_hash`, `snapshot.payload`)
  - bounded per-metric variance for identical run configs
- CI quality gate: `scripts/ci/check-benchmark-reproducibility.sh`.
- Failed gate emits drift diagnostics with `code`, `field`, and `message`.

## Phase-3 change log discipline

For every Phase-3 PR, include:

- **Version impact**: additive benchmark observability pack, package version raised to `0.7.0`.
- **Compatibility**: backward-compatible addition; existing `/benchmarks/run`, `/benchmarks/compare`, `/benchmarks/history`, and dataset contracts unchanged.
- **Migration notes**: no mandatory migration. Operators should import `monitoring/dashboards/benchmark_dashboard.json`, load `monitoring/metrics/prometheus/benchmark-alerts.yaml`, and follow `docs/howto/benchmark-observability-runbook.md`.
