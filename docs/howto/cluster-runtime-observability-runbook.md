# Cluster Runtime Observability Runbook (Phase-5)

## Purpose

Use this runbook when distributed execution reliability degrades in the control-plane -> queue -> worker critical path.

## Public Metrics Contract

Metric names below are part of the public Phase-5 observability contract and are SemVer-governed.

- `eigen_cluster_worker_heartbeats_total`
- `eigen_cluster_worker_flaps_total`
- `eigen_cluster_workers_ready`
- `eigen_cluster_assignment_latency_ms_bucket`
- `eigen_cluster_assignment_latency_ms_sum`
- `eigen_cluster_assignment_latency_ms_count`
- `eigen_cluster_queue_backlog_depth`
- `eigen_cluster_queue_oldest_age_seconds`
- `eigen_cluster_queue_deliveries_total`
- `eigen_cluster_queue_lease_churn_total`
- `eigen_cluster_queue_redeliveries_total`
- `eigen_cluster_dead_letter_total`
- `eigen_cluster_trace_breakage_total`
- `eigen_cluster_runtime_contract_info{version="1.0.0"}`

## Dashboard and Alerts

- Dashboard: `monitoring/dashboards/cluster_runtime_sre_dashboard.json`
- Alert rules: `monitoring/metrics/prometheus/cluster-runtime-alerts.yaml`

## Deterministic Triage Flow

1. **Confirm queue movement first (stall gate)**
   - Evaluate backlog and delivery delta:
     - `eigen_cluster_queue_backlog_depth`
     - `increase(eigen_cluster_queue_deliveries_total[10m])`
   - If backlog is non-zero while delivery delta is zero for 10 minutes, treat as a queue stall incident.

2. **Check control-plane assignment SLO**
   - `histogram_quantile(0.95, sum by (le) (rate(eigen_cluster_assignment_latency_ms_bucket[5m])))`
   - SLO breach threshold: p95 `> 200ms` for 10 minutes.
   - If breached with normal queue movement, prioritize control-plane scheduler/load diagnosis.

3. **Check worker stability and node availability**
   - Heartbeats: `increase(eigen_cluster_worker_heartbeats_total[5m])`
   - Flaps: `increase(eigen_cluster_worker_flaps_total[15m])`
   - Ready capacity: `eigen_cluster_workers_ready`
   - If flaps rise and ready workers drop, isolate unstable workers before queue tuning.

4. **Validate delivery reliability path**
   - Lease churn: `increase(eigen_cluster_queue_lease_churn_total[15m])`
   - Redelivery ratio:
     - `increase(eigen_cluster_queue_redeliveries_total[15m]) / clamp_min(increase(eigen_cluster_queue_deliveries_total[15m]), 1)`
   - Dead-letter pressure: `increase(eigen_cluster_dead_letter_total[15m])`
   - If redelivery ratio > 20% or dead-letter spikes, treat as lease visibility/handler timeout reliability regression.

5. **Validate tracing continuity**
   - `increase(eigen_cluster_trace_breakage_total[10m])`
   - Any positive value indicates broken lineage propagation across control-plane -> queue -> worker and requires immediate rollback of recent propagation changes.

## Rollback Procedure

1. Roll queue provider settings to last known-good lease visibility timeout and retry budget.
2. Disable or roll back the latest worker image with heartbeat/ack behavioral changes.
3. Revert control-plane assignment policy to previous deterministic release.
4. Freeze topology/trace propagation changes if `trace_breakage_total` remains non-zero.

## Recovery Verification Checklist

- Queue stall alert clears and deliveries resume.
- Assignment latency p95 returns below 200ms for at least 30 minutes.
- Worker flap rate remains below warning threshold for at least 30 minutes.
- Redelivery ratio returns below 10% steady-state target.
- Dead-letter volume stabilizes at baseline.
- Trace breakage remains zero over a full on-call window.

## Post-Incident Capture

Record in the incident report:

- alert names and UTC start/end timestamps,
- queue provider and lease configuration before/after mitigation,
- worker image/control-plane version before/after rollback,
- whether deterministic reassignment and replay checks were executed,
- follow-up tasks for conformance and regression fixtures.
