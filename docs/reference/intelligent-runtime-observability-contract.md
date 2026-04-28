# Intelligent Runtime Observability Contract

This document defines the stable metrics contract for Phase-4 intelligent runtime observability (P4-06).

## Contract version

- Contract version: `1.0.0`
- Version marker metric: `eigen_runtime_contract_info{version="1.0.0"}`

SemVer policy:

- `MAJOR`: incompatible metric rename/removal/semantic break;
- `MINOR`: additive metrics/labels with backward compatibility;
- `PATCH`: bugfix-only corrections without public semantic changes.

## Required metrics

### Decision and scoring health

- `eigen_runtime_decisions_total{policy_mode}`
- `eigen_runtime_scoring_latency_ms_bucket`
- `eigen_runtime_scoring_latency_ms_sum`
- `eigen_runtime_scoring_latency_ms_count`
- `eigen_runtime_scoring_failures_total{reason}`

### Policy-branch and fallback behavior

- `eigen_runtime_policy_branch_total{policy_mode,branch}`
- `eigen_runtime_fallback_total{reason}`

### Explain endpoint SLO and reliability

- `eigen_runtime_explain_requests_total{endpoint,level}`
- `eigen_runtime_explain_latency_ms_bucket{endpoint,level}`
- `eigen_runtime_explain_latency_ms_sum{endpoint,level}`
- `eigen_runtime_explain_latency_ms_count{endpoint,level}`
- `eigen_runtime_explain_errors_total{endpoint,error_code}`

## Alert pack

Prometheus alert rules for this contract are maintained in:

- `monitoring/metrics/prometheus/intelligent-runtime-alerts.yaml`

Critical alerts:

- scoring failure spike,
- explain endpoint error-rate SLO breach,
- explain p95 latency breach per level (`L1_USER`, `L2_ADMIN`, `L3_FORENSIC`).

Warning alerts:

- scoring latency degradation,
- fallback-rate increase.

## Dashboard pack

Grafana dashboard for end-to-end decision flow:

- `monitoring/dashboards/intelligent_runtime_dashboard.json`

The dashboard includes decision throughput by policy mode, scoring latency/failure panels, fallback frequency, explain p95 by level, and a policy-branch drift indicator.

## Compatibility guarantees

- Existing Phase-3 benchmark and Phase-2 orchestrator metric families remain unchanged.
- New metrics are additive under `eigen_runtime_*` namespace.
- Deprecation follows Phase-4 rule: metrics/labels are not removed before at least one `MINOR` release marks them deprecated.

## Migration notes

- No mandatory migration for existing operators.
- To adopt this contract, ingest `eigen_runtime_*` metrics, import the dashboard, and load `intelligent-runtime-alerts.yaml` in Prometheus rule files.
