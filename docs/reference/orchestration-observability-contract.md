# Orchestration Observability Contract

**Status:** Phase-2 stable contract for exported orchestrator metrics.  
**Implementation state:** exporter and monitoring assets are implemented; runtime wiring of real scheduler signals is still partial.

## Version

- Contract marker metric: `eigen_orch_contract_info{version="2.3.0"} 1`
- Current SemVer line: **2.3.x**

SemVer policy for orchestration observability:

- **MAJOR** — rename/remove a public metric, or change its meaning/type.
- **MINOR** — add backward-compatible metrics or labels.
- **PATCH** — implementation/documentation fixes without public semantic changes.

## Stable Metrics (Public Surface)

All names below are **stable** and must be treated as public API:

- `eigen_orch_queue_depth` (gauge)
- `eigen_orch_queue_oldest_age_seconds` (gauge)
- `eigen_orch_queue_avg_age_seconds` (gauge)
- `eigen_orch_fairness_lag_millis_total` (counter)
- `eigen_orch_fairness_lag_millis_max` (gauge)
- `eigen_orch_quota_denied_tenant_total` (counter)
- `eigen_orch_quota_denied_project_total` (counter)
- `eigen_orch_rebalance_trigger_total` (counter)
- `eigen_orch_starvation_prevention_total` (counter)

## Label/Type Contract

- `eigen_orch_contract_info` has exactly one required label: `version`.
- Other Phase-2 orchestration metrics are currently exported **without labels** (single global time series per metric).
- Metric type declarations in Prometheus text output are part of compatibility expectations.
- Any future label introduction must keep cardinality bounded and deterministic.

## Source of Truth in Repository

- Export format and metric list: `monitoring/metrics/prometheus/exporter.py`.
- Prometheus alert rules consuming this contract: `monitoring/metrics/prometheus/orchestrator-alerts.yaml`.
- Dashboard consuming this contract: `monitoring/dashboards/orchestration_dashboard.json`.
- Contract coverage tests: `monitoring/metrics/tests/test_stage_observability.py`.
- Operational runbook: `docs/howto/orchestrator-observability-runbook.md`.

## What Is Implemented Now

1. A dedicated `OrchestrationTelemetryExporter` with an immutable snapshot model and explicit contract version `2.3.0`.
2. Prometheus text exposition includes `# TYPE` lines for every public orchestration metric.
3. Alerting and dashboard assets are aligned to the exact stable metric names above.
4. Repository tests assert the contract marker and all Phase-2 orchestration metrics.

## Known Gaps / Missing Pieces

The contract surface is stable, but system-level observability completeness is still evolving:

1. **Runtime signal wiring is partial.**
   The exporter supports snapshot updates, but end-to-end automatic feeding from full production-grade scheduler/orchestrator flows is not fully documented as complete in architecture/runtime docs.
2. **No tenant/project label breakdown yet.**
   Quota/fairness metrics are global counters in the current public surface; per-tenant/per-project slicing is not exposed in this contract version.
3. **No histogram distribution metrics for queue/fairness.**
   Only global gauges/counters are exported; deeper percentile distributions for queue age/fairness lag are not part of v2.3.0.
4. **No explicit stale-data freshness guard metric.**
   The contract currently lacks a dedicated “last snapshot update timestamp/age” metric.

## Compatibility Rules

1. Metrics listed in this document are public contract surface.
2. Label cardinality must remain bounded and deterministic.
3. Deprecation requires at least one **MINOR** cycle before removal.
4. Alerts/dashboards/tests must be updated in the same change set when contract additions are introduced.
5. Contract marker version must be bumped on every contract-level SemVer change and reflected consistently in docs, tests, and exporter defaults.
