# Benchmark Observability Contract

This document defines the stable metrics contract for Phase-3 benchmarking SRE coverage.

## Contract version

- Contract version: `1.0.0`
- Version marker metric: `eigen_bench_contract_info{version="1.0.0"}`

SemVer policy:

- `MAJOR`: incompatible metric rename/removal/semantic break;
- `MINOR`: additive metrics/labels with backward compatibility;
- `PATCH`: bugfix-only corrections without public semantic changes.

## Repository status snapshot (as of 2026-05-10)

### Implemented and verified

- Stable exporter for benchmark contract metrics exists at `monitoring/metrics/prometheus/exporter.py`.
- Contract test coverage validates metric names and version marker at `monitoring/metrics/tests/test_stage_observability.py`.
- Alert pack for benchmark SLO protection exists at `monitoring/metrics/prometheus/benchmark-alerts.yaml`.
- Dashboard pack for benchmark lifecycle telemetry exists at `monitoring/dashboards/benchmark_dashboard.json`.
- Operational runbook exists at `docs/howto/benchmark-observability-runbook.md`.

### Missing / not yet productized

- Benchmark metrics are currently exported via contract-focused monitoring artifacts; a dedicated long-running benchmark-service metrics endpoint wiring is not yet documented as mandatory runtime topology.
- Explicit label contract (allowed label keys and bounded cardinality examples) is still under-specified for future additive metrics.
- Automated CI guard that checks dashboard/alert expression compatibility against contract version bumps is not yet formalized as a required gate.

## Required metrics

- `eigen_bench_queue_depth` (gauge)
- `eigen_bench_run_duration_seconds` (gauge)
- `eigen_bench_runs_succeeded_total` (counter)
- `eigen_bench_runs_failed_total` (counter)
- `eigen_bench_ingestion_failures_total` (counter)
- `eigen_bench_stalled_runs` (gauge)

## Alert pack

Prometheus alert rules for this contract are maintained in:

- `monitoring/metrics/prometheus/benchmark-alerts.yaml`

Critical alerts:

- run stall detection,
- ingestion failure spike,
- failed-run ratio breach.

## Dashboard pack

Grafana dashboard for benchmark queue/run health:

- `monitoring/dashboards/benchmark_dashboard.json`

The dashboard includes queue depth, run duration trend, success vs failed run throughput, ingestion failures, stalled runs, and contract marker visibility.

## Compatibility rules

1. Metric names listed above are public contract surface.
2. Label cardinality must remain bounded and deterministic.
3. Deprecated metrics require at least one `MINOR` cycle before removal.
4. Alert and dashboard expressions must be updated in the same PR when metric additions are introduced.

## Migration notes

- No mandatory migration for existing operators.
- To adopt this contract, ingest `eigen_bench_*` metrics, load `benchmark-alerts.yaml`, import `benchmark_dashboard.json`, and use `docs/howto/benchmark-observability-runbook.md` for incident response.
