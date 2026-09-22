# Benchmark Observability Runbook (Phase-3)

## Purpose

Use this runbook when benchmark queue pressure, stalled runs, or ingestion failures impact benchmark SLOs.

## Public Metrics Contract

Metric names below are part of the public observability contract for Phase-3 benchmarking and must remain SemVer-governed.

- `eigen_bench_queue_depth`
- `eigen_bench_run_duration_seconds`
- `eigen_bench_runs_succeeded_total`
- `eigen_bench_runs_failed_total`
- `eigen_bench_ingestion_failures_total`
- `eigen_bench_stalled_runs`
- `eigen_bench_contract_info{version="1.0.0"}`

## Dashboard and Alerts

- Dashboard: `monitoring/dashboards/benchmark_dashboard.json`
- Alert rules: `monitoring/metrics/prometheus/benchmark-alerts.yaml`

## Triage Flow

1. **Confirm stalled-run signal**
   - Alert: `EigenBenchmarkRunStalled` when `eigen_bench_stalled_runs > 0` for 10m.
   - Inspect run state transitions and worker heartbeats for `RUNNING` entries without progress.

2. **Check ingestion health**
   - Alert: `EigenBenchmarkIngestionFailuresSpike` when `increase(eigen_bench_ingestion_failures_total[10m]) > 0`.
   - Verify dataset bundle checksums and manifest required fields.

3. **Evaluate run failure pressure**
   - Alert: `EigenBenchmarkFailureRateHigh` when 15m failure ratio exceeds 20%.
   - Compare `increase(eigen_bench_runs_failed_total[15m])` vs `increase(eigen_bench_runs_succeeded_total[15m])`.

4. **Correlate latency/throughput regression signal**
   - Review `eigen_bench_run_duration_seconds` and queue depth trend together.
   - Rising duration with growing queue often indicates saturation or backend instability.

5. **Action checklist**
   - Restart or scale benchmark workers if runs are stalled.
   - Quarantine invalid dataset bundles and rerun ingestion validation.
   - If failure ratio remains elevated, pause candidate rollout and run `/benchmarks/compare` against last known-good baseline.

## Post-Incident Notes

Capture in incident record:

- Alert name, start/end time, and impacted datasets/backends.
- Metric snapshots before and after mitigation.
- Any policy changes (with contract version impact and compatibility notes).
