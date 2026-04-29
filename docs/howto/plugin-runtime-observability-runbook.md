# Plugin Runtime Observability Runbook (Phase-6)

## Purpose

Use this runbook when plugin discovery/activation health degrades, or when trust/compatibility/sandbox policy rejects increase.

## Public Metrics Contract

Metric names below are part of the public Phase-6 plugin observability contract and are SemVer-governed.

- `eigen_plugin_inventory_total`
- `eigen_plugin_attempts_total`
- `eigen_plugin_failures_total`
- `eigen_plugin_discovery_failures_total`
- `eigen_plugin_activation_failures_total`
- `eigen_plugin_compatibility_rejects_total`
- `eigen_plugin_signature_rejects_total`
- `eigen_plugin_sandbox_rejects_total`
- `eigen_plugin_rejections_total{reason_code="..."}`
- `eigen_plugin_activation_latency_ms_bucket`
- `eigen_plugin_activation_latency_ms_sum`
- `eigen_plugin_activation_latency_ms_count`
- `eigen_plugin_startup_critical_path_ms_bucket`
- `eigen_plugin_startup_critical_path_ms_sum`
- `eigen_plugin_startup_critical_path_ms_count`
- `eigen_plugin_startup_slo_breaches_total`
- `eigen_plugin_observability_contract_info{version="1.0.0"}`

## Dashboard and Alerts

- Dashboard: `monitoring/dashboards/plugin_runtime_sre_dashboard.json`
- Alert rules: `monitoring/metrics/prometheus/plugin-runtime-alerts.yaml`

## Deterministic Triage Flow

1. **Confirm startup critical path health first**
   - `histogram_quantile(0.95, sum by (le) (rate(eigen_plugin_startup_critical_path_ms_bucket[5m])))`
   - If p95 is `> 2000ms` for 10 minutes, prioritize startup-path rollback before plugin-level tuning.

2. **Quantify failure-rate scope**
   - `increase(eigen_plugin_failures_total[15m]) / clamp_min(increase(eigen_plugin_attempts_total[15m]), 1)`
   - If failure rate exceeds 10%, classify incident as plugin activation degradation.

3. **Split failures by lifecycle stage**
   - Discovery: `increase(eigen_plugin_discovery_failures_total[15m])`
   - Activation: `increase(eigen_plugin_activation_failures_total[15m])`
   - Prioritize discovery-path fixes if discovery failures dominate; otherwise continue with load-time gate diagnostics.

4. **Classify load-time gate rejects**
   - Compatibility: `increase(eigen_plugin_compatibility_rejects_total[15m])`
   - Signature/trust: `increase(eigen_plugin_signature_rejects_total[15m])`
   - Sandbox: `increase(eigen_plugin_sandbox_rejects_total[15m])`
   - Top reasons: `topk(10, sum by (reason_code) (increase(eigen_plugin_rejections_total[15m])))`

5. **Validate activation latency for surviving plugins**
   - `histogram_quantile(0.95, sum by (le) (rate(eigen_plugin_activation_latency_ms_bucket[5m])))`
   - If latency rises while reject counters stay flat, investigate runtime saturation rather than policy gates.

## Rollback Procedure

1. Revert latest plugin bundle/registry snapshot to last known-good signed set.
2. Revert trust-profile or signer-identity policy changes if signature rejects spike.
3. Revert compatibility matrix updates if compatibility rejects spike.
4. Revert sandbox policy profile changes (`runsc` policy/cgroup/profile) if sandbox rejects appear.
5. Disable newly introduced plugin(s) by type/id and restore previous activation order.

## Recovery Verification Checklist

- Plugin failure-rate alert clears and remains below 5% for at least 30 minutes.
- Startup critical-path p95 returns below 2000ms for at least 30 minutes.
- Compatibility/signature/sandbox reject counters return to baseline.
- Top rejection reasons are stable and understood.
- Plugin inventory and active plugin count match expected rollout manifest.

## Post-Incident Capture

Record in the incident report:

- alert names and UTC start/end timestamps,
- plugin bundle or registry snapshot IDs before/after rollback,
- trust profile and policy digest before/after mitigation,
- compatibility matrix/version tuple changes before/after,
- sandbox profile revision before/after,
- deterministic validation evidence for restored startup/activation path.

## Compatibility matrix and upgrade order (Phase-7)

- Canonical machine-readable manifest: `src/rust/apps/cli/tests/fixtures/plugin_compatibility_matrix_v1.json`.
- Support window policy: deprecated interfaces stay supported for **2 minor releases or 90 days** (whichever is longer).
- Deterministic upgrade order for multi-component deployments: **runtime -> cli -> plugin_api -> eigen_lang**.
- Unsupported version combinations are rejected with stable reason code `PLUGIN_COMPATIBILITY_MATRIX_UNSUPPORTED` and actionable remediation hints.
