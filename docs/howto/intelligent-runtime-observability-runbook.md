# Intelligent Runtime Observability Runbook (Phase-4)

## Purpose

Use this runbook when intelligent runtime decision quality degrades, fallback rates spike, or explain endpoint SLO breaches are triggered.

## Public Metrics Contract

Metric names below are part of the public Phase-4 observability contract and are SemVer-governed.

- `eigen_runtime_decisions_total`
- `eigen_runtime_scoring_latency_ms_bucket`
- `eigen_runtime_scoring_failures_total`
- `eigen_runtime_policy_branch_total`
- `eigen_runtime_fallback_total`
- `eigen_runtime_explain_requests_total`
- `eigen_runtime_explain_latency_ms_bucket`
- `eigen_runtime_explain_errors_total`
- `eigen_runtime_contract_info{version="1.0.0"}`

## Dashboard and Alerts

- Dashboard: `monitoring/dashboards/intelligent_runtime_dashboard.json`
- Alert rules: `monitoring/metrics/prometheus/intelligent-runtime-alerts.yaml`

## Triage Flow

1. **Confirm scoring path health**
   - Check `increase(eigen_runtime_scoring_failures_total[10m])`.
   - If failures are elevated, inspect top `reason` label values and correlate with rollout window.

2. **Validate explain endpoint SLO**
   - Error budget breach condition:
     - `increase(eigen_runtime_explain_errors_total[10m]) / clamp_min(increase(eigen_runtime_explain_requests_total[10m]), 1) > 1%`
   - Latency SLOs:
     - `L1_USER` p95 `< 100ms`
     - `L2_ADMIN` p95 `< 200ms`
     - `L3_FORENSIC` p95 `< 500ms`

3. **Assess fallback pressure and decision drift**
   - Fallback rate:
     - `increase(eigen_runtime_fallback_total[15m]) / clamp_min(increase(eigen_runtime_decisions_total[15m]), 1)`
   - Branch drift signal:
     - compare `increase(eigen_runtime_policy_branch_total{branch=...}[30m])` across policy modes.
   - If drift/fallback rises after policy changes, freeze or roll back policy bundle version first.

4. **Rollback procedure (safe mode)**
   - Pin scheduler to previously stable `policy_bundle_version`.
   - Disable recently enabled optional scoring features that introduced new `reason` error classes.
   - Switch explain path to cached-artifact mode for `L3_FORENSIC` if backend pressure is high.

5. **Recovery verification checklist**
   - `scoring_failures_total` returns to baseline.
   - fallback rate returns below 5% steady-state target.
   - explain error rate remains below 1% for at least 30 minutes.
   - explain p95 latency is back within level-specific SLOs.

## Post-Incident Capture

Record in incident report:

- alert names and UTC start/end time,
- impacted policy modes and explain levels,
- policy/scoring profile versions before/after mitigation,
- whether rollback was required,
- follow-up action items for deterministic replay coverage.
