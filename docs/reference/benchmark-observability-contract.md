# Benchmark Observability Contract

**Status:** Phase-3 stable observability contract.

## Version

- Contract version marker metric: `eigen_bench_contract_info{version="1.0.0"} 1`

SemVer policy for benchmark observability metrics:

- **MAJOR**: rename/remove metric names or change semantic meaning.
- **MINOR**: add new optional metric names/labels while preserving existing semantics.
- **PATCH**: fixes only; no public metric contract semantic changes.

## Stable Metric Names

- `eigen_bench_queue_depth` (gauge)
- `eigen_bench_run_duration_seconds` (gauge)
- `eigen_bench_runs_succeeded_total` (counter)
- `eigen_bench_runs_failed_total` (counter)
- `eigen_bench_ingestion_failures_total` (counter)
- `eigen_bench_stalled_runs` (gauge)

## Compatibility Rules

1. Metric names listed above are public contract surface.
2. Label cardinality must remain bounded and deterministic.
3. Deprecated metrics require at least one MINOR cycle before removal.
4. Alert and dashboard expressions must be updated in the same PR when metric additions are introduced.
