# Cluster Runtime Observability Contract

This document defines the stable metrics contract for Phase-5 distributed execution SRE coverage (P5-06).

## Contract version

- Contract version: `1.0.0`
- Version marker metric: `eigen_cluster_runtime_contract_info{version="1.0.0"}`

SemVer policy:

- `MAJOR`: incompatible metric rename/removal/semantic break;
- `MINOR`: additive metrics/labels with backward compatibility;
- `PATCH`: bugfix-only corrections without public semantic changes.

## Required metrics

### Worker liveness and node availability

- `eigen_cluster_worker_heartbeats_total{worker_id}`
- `eigen_cluster_worker_flaps_total{worker_id,reason}`
- `eigen_cluster_workers_ready`

### Control-plane assignment critical path

- `eigen_cluster_assignment_latency_ms_bucket`
- `eigen_cluster_assignment_latency_ms_sum`
- `eigen_cluster_assignment_latency_ms_count`

### Queue reliability and delivery semantics

- `eigen_cluster_queue_backlog_depth{queue}`
- `eigen_cluster_queue_oldest_age_seconds{queue}`
- `eigen_cluster_queue_deliveries_total{queue}`
- `eigen_cluster_queue_lease_churn_total{queue,reason}`
- `eigen_cluster_queue_redeliveries_total{queue}`
- `eigen_cluster_dead_letter_total{queue,reason}`

### Tracing continuity

- `eigen_cluster_trace_breakage_total{stage}`

## Alert pack

Prometheus alert rules for this contract are maintained in:

- `monitoring/metrics/prometheus/cluster-runtime-alerts.yaml`

Critical alerts:

- queue stall,
- redelivery rate breach,
- assignment p95 SLO breach,
- trace continuity breakage.

Warning alerts:

- worker flap rate increase,
- dead-letter volume increase.

## Dashboard pack

Grafana dashboard for control-plane -> queue -> worker health:

- `monitoring/dashboards/cluster_runtime_sre_dashboard.json`

The dashboard includes assignment latency, queue backlog/age, worker availability + heartbeat trends, lease churn + redelivery ratio, dead-letter volume, and trace breakage.

## Compatibility guarantees

- Existing Phase-2/3/4 metrics families remain unchanged.
- New metrics are additive under `eigen_cluster_*` namespace.
- Deprecation follows Phase-5 rule: metrics/labels are not removed before at least one `MINOR` release marks them deprecated.

## Migration notes

- No mandatory migration for existing deployments.
- To adopt this contract, ingest `eigen_cluster_*` metrics, import the dashboard, load `cluster-runtime-alerts.yaml`, and enforce SLO alert routes for distributed runtime on-call.
