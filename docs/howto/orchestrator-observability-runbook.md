# Orchestrator Observability Runbook (Phase-2)

## Purpose

Use this runbook when queue pressure, fairness skew, quota pressure, or rebalance churn impacts orchestration SLOs.

## Public Metrics Contract

Metric names below are part of the public observability contract for Phase-2 orchestrator and must remain SemVer-governed.

- `eigen_orch_queue_depth`
- `eigen_orch_queue_oldest_age_seconds`
- `eigen_orch_queue_avg_age_seconds`
- `eigen_orch_fairness_lag_millis_total`
- `eigen_orch_fairness_lag_millis_max`
- `eigen_orch_quota_denied_tenant_total`
- `eigen_orch_quota_denied_project_total`
- `eigen_orch_rebalance_trigger_total`
- `eigen_orch_starvation_prevention_total`
- `eigen_orch_contract_info{version="2.3.0"}`

## Dashboard and Alerts

- Dashboard: `monitoring/dashboards/orchestration_dashboard.json`
- Alert rules: `monitoring/metrics/prometheus/orchestrator-alerts.yaml`

## Triage Flow

1. **Confirm overload vs starvation signal**
   - Overload: `eigen_orch_queue_depth > 250` for 10m.
   - Starvation: `eigen_orch_queue_oldest_age_seconds > 120` for 10m.

2. **Assess fairness health**
   - Inspect `eigen_orch_fairness_lag_millis_max` and 5m increase of `eigen_orch_fairness_lag_millis_total`.
   - If max lag is elevated and queue depth is moderate, suspect skewed weight configuration or hot tenant.

3. **Check quota pressure**
   - Compare `increase(eigen_orch_quota_denied_tenant_total[10m])` and `increase(eigen_orch_quota_denied_project_total[10m])`.
   - Tenant-heavy spikes indicate per-tenant quota saturation; project-heavy spikes indicate local project burst.

4. **Validate rebalance behavior**
   - Review `increase(eigen_orch_rebalance_trigger_total[15m])` together with starvation counters.
   - High rebalance with growing starvation can indicate oscillation; reduce rebalance aggressiveness and verify low/high watermark gap.

5. **Action checklist**
   - If pure overload: scale orchestrator workers and/or tighten admission defer threshold.
   - If starvation with low throughput: lower starvation threshold and verify fairness weights for impacted tenant/project.
   - If quota deny spike: coordinate with tenant/project owners to resize quotas or smooth submissions.
   - If rebalance oscillation: increase `min_imbalance_gap` and reduce `max_preemptions_per_rebalance`.

## Post-Incident Notes

Capture in incident record:

- Alert name, start/end time, and impacted tenants/projects.
- Metric snapshots before and after mitigation.
- Any policy changes (with contract version impact and compatibility notes).
