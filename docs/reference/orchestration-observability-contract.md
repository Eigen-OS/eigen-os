# Orchestration Observability Contract

**Status:** Phase-2 stable observability contract.

## Version

- Contract version marker metric: `eigen_orch_contract_info{version="2.3.0"} 1`

SemVer policy for orchestrator observability metrics:

- **MAJOR**: rename/remove metric names or change semantic meaning.
- **MINOR**: add new optional metric names/labels while preserving existing semantics.
- **PATCH**: fixes only; no public metric contract semantic changes.

## Stable Metric Names

- `eigen_orch_queue_depth` (gauge)
- `eigen_orch_queue_oldest_age_seconds` (gauge)
- `eigen_orch_queue_avg_age_seconds` (gauge)
- `eigen_orch_fairness_lag_millis_total` (counter)
- `eigen_orch_fairness_lag_millis_max` (gauge)
- `eigen_orch_quota_denied_tenant_total` (counter)
- `eigen_orch_quota_denied_project_total` (counter)
- `eigen_orch_rebalance_trigger_total` (counter)
- `eigen_orch_starvation_prevention_total` (counter)

## Compatibility Rules

1. Metric names listed above are public contract surface.
2. Label cardinality must remain bounded and deterministic.
3. Deprecated metrics require at least one MINOR cycle before removal.
4. Alert and dashboard expressions must be updated in the same PR when metric additions are introduced.
