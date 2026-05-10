# Intelligent Runtime Observability Contract

This document defines the Phase-4 intelligent runtime observability contract and the **current implementation snapshot** for decisioning/explainability SRE coverage (P4-06).

## Contract version

- Contract version: `1.0.0`
- Version marker metric (contracted): `eigen_runtime_contract_info{version="1.0.0"}`

SemVer policy:

- `MAJOR`: incompatible metric rename/removal/semantic break;
- `MINOR`: additive metrics/labels with backward compatibility;
- `PATCH`: bugfix-only corrections without public semantic changes.

## Scope and source of truth

This contract is aligned with:

- `docs/architecture/components/observability.md`
- `docs/architecture/contract-map.md`
- Phase-4 governance package (RFC/ADR): backend-selection scoring, explainability API, scheduling policy semantics.

Supporting operator assets:

- Alerts: `monitoring/metrics/prometheus/intelligent-runtime-alerts.yaml`
- Dashboard: `monitoring/dashboards/intelligent_runtime_dashboard.json`
- Runbook: `docs/howto/intelligent-runtime-observability-runbook.md`

---

## Required metrics (contract surface)

### 1) Decision and scoring health

- `eigen_runtime_decisions_total{policy_mode}`
- `eigen_runtime_scoring_latency_ms_bucket`
- `eigen_runtime_scoring_latency_ms_sum`
- `eigen_runtime_scoring_latency_ms_count`
- `eigen_runtime_scoring_failures_total{reason}`

### 2) Policy-branch and fallback behavior

- `eigen_runtime_policy_branch_total{policy_mode,branch}`
- `eigen_runtime_fallback_total{reason}`

### 3) Explain endpoint SLO and reliability

- `eigen_runtime_explain_requests_total{endpoint,level}`
- `eigen_runtime_explain_latency_ms_bucket{endpoint,level}`
- `eigen_runtime_explain_latency_ms_sum{endpoint,level}`
- `eigen_runtime_explain_latency_ms_count{endpoint,level}`
- `eigen_runtime_explain_errors_total{endpoint,error_code}`

---

## Implementation snapshot (state fix on 2026-05-10)

### Implemented in repository today

- Prometheus alert rules are codified and connected in rule-files config for intelligent runtime coverage (scoring failures, scoring latency degradation, fallback-rate increase, explain error-rate breach, explain p95 breaches by level).
- Grafana dashboard pack exists with decision throughput by policy mode, scoring latency/failures, fallback frequency/rate, explain p95 panels, policy-branch drift indicator, and contract marker panel.
- Operational runbook exists with triage workflow and recommended investigation PromQL.
- Contract references are wired into reference index and run-observability entry points.

### Missing / not yet fully implemented

- No canonical runtime metrics exporter has been verified in code for the full `eigen_runtime_*` metric family listed in this contract.
  - Repository evidence currently shows alert/dashboard/runbook assets consuming these metrics, but there is no confirmed instrumentation source emitting them end-to-end in service runtime paths.
- `eigen_runtime_contract_info{version="1.0.0"}` is required by contract, but explicit runtime emission is not validated in the currently tracked exporter implementation.
- No dedicated CI gate currently asserts that all required `eigen_runtime_*` metric names are present in a live `/metrics` scrape.
- Label-level normalization for explain `level` requires explicit convergence in implementation:
  - alerts currently evaluate numeric labels (`level="1"|"2"|"3"`),
  - runbook/contract text also references role labels (`L1_USER`, `L2_ADMIN`, `L3_FORENSIC`).
  - A single normative encoding should be fixed in instrumentation + docs to avoid operator ambiguity.

---

## Alert pack

Prometheus alert rules for this contract are maintained in:

- `monitoring/metrics/prometheus/intelligent-runtime-alerts.yaml`

Critical alerts:

- scoring failure spike,
- explain endpoint error-rate SLO breach,
- explain p95 latency breach per level.

Warning alerts:

- scoring latency degradation,
- fallback-rate increase.

## Dashboard pack

Grafana dashboard for end-to-end decision flow:

- `monitoring/dashboards/intelligent_runtime_dashboard.json`


## Compatibility guarantees

- Existing Phase-2/3 orchestration and benchmark metric families remain unchanged.
- Intelligent-runtime metrics are additive under `eigen_runtime_*` namespace.
- Deprecation rule: metrics/labels are not removed before at least one `MINOR` release marks them deprecated.

## Migration notes

- No mandatory migration for existing operators.
- To adopt this contract in operations:
  1. expose/scrape the runtime target that publishes `eigen_runtime_*` metrics,
  2. load `monitoring/metrics/prometheus/intelligent-runtime-alerts.yaml`,
  3. import `monitoring/dashboards/intelligent_runtime_dashboard.json`,
  4. align on-call routing with `docs/howto/intelligent-runtime-observability-runbook.md`.

## Minimum closure criteria for "contract fully realized"

1. A runtime endpoint exports all required metric names from this document in at least one environment profile.
2. Contract version marker metric is exported.
3. CI check asserts required metric names exist in scrape output (or explicit allowlist for staged rollout).
4. Explain `level` encoding is standardized and reflected consistently in instrumentation, alerts, dashboard, and runbook.
