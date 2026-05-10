# Cluster Runtime Observability Contract

This document defines the Phase-5 distributed execution observability contract and the **current implementation snapshot** for cluster-runtime SRE coverage (P5-06).

## Contract version

- Contract version: `1.0.0`
- Version marker metric (contracted): `eigen_cluster_runtime_contract_info{version="1.0.0"}`

SemVer policy:

- `MAJOR`: incompatible metric rename/removal/semantic break;
- `MINOR`: additive metrics/labels with backward compatibility;
- `PATCH`: bugfix-only corrections without public semantic changes.

## Scope and source of truth

This contract is aligned with:

- `docs/architecture/components/observability.md`
- `docs/architecture/contract-map.md`
- Phase-5 governance package (RFC/ADR): cluster control plane, distributed queue semantics, distributed tracing topology.

Supporting operator assets:

- Alerts: `monitoring/metrics/prometheus/cluster-runtime-alerts.yaml`
- Dashboard: `monitoring/dashboards/cluster_runtime_sre_dashboard.json`
- Runbook: `docs/howto/cluster-runtime-observability-runbook.md`

---

## Required metrics (contract surface)

### 1) Worker liveness and node availability

- `eigen_cluster_worker_heartbeats_total{worker_id}`
- `eigen_cluster_worker_flaps_total{worker_id,reason}`
- `eigen_cluster_workers_ready`

### 2) Control-plane assignment critical path

- `eigen_cluster_assignment_latency_ms_bucket`
- `eigen_cluster_assignment_latency_ms_sum`
- `eigen_cluster_assignment_latency_ms_count`

### 3) Queue reliability and delivery semantics

- `eigen_cluster_queue_backlog_depth{queue}`
- `eigen_cluster_queue_oldest_age_seconds{queue}`
- `eigen_cluster_queue_deliveries_total{queue}`
- `eigen_cluster_queue_lease_churn_total{queue,reason}`
- `eigen_cluster_queue_redeliveries_total{queue}`
- `eigen_cluster_dead_letter_total{queue,reason}`

### 4) Tracing continuity

- `eigen_cluster_trace_breakage_total{stage}`

---

## Implementation snapshot (state fix on 2026-05-10)

### Implemented in repository today

- Alert rules and thresholds are already codified and wired in Prometheus config:
  - queue stall,
  - worker flap surge,
  - redelivery-rate breach,
  - dead-letter surge,
  - assignment p95 breach,
  - trace continuity breakage.
- Grafana dashboard pack exists with panels for assignment latency, backlog/age, worker health, lease churn + redelivery ratio, dead-letter volume, trace breakage.
- Operational runbook exists and references the full cluster metric family and triage workflow.
- Queue delivery semantics are implemented and test-covered in Resource Manager (`redelivery`, `dead-letter`, lease expiration behavior, deterministic replay fixtures).

### Missing / not yet fully implemented

- No canonical producer/exporter in runtime services has been verified in code for all `eigen_cluster_*` metric families listed above.
  - Current repository has contract + alerts + dashboard + runbook, but metric instrumentation appears partially or not yet fully wired end-to-end in service runtime paths.
- `eigen_cluster_runtime_contract_info{version="1.0.0"}` emitter is required by contract, but explicit runtime emission must be validated/added where cluster metrics are exposed.
- Cluster-runtime observability ownership is still distributed across services (matching architecture status), not centralized in a dedicated observability core.
- End-to-end CI gate that validates "metric family present in live `/metrics` scrape" for the full `eigen_cluster_*` set is not yet formalized in this contract.

---

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

## Compatibility guarantees

- Existing Phase-2/3/4 metrics families remain unchanged.
- Cluster-runtime metrics are additive under `eigen_cluster_*` namespace.
- Deprecation rule: metrics/labels are not removed before at least one `MINOR` release marks them deprecated.

## Migration notes

- No mandatory migration for deployments that do not enable distributed runtime features.
- To adopt this contract in operations:
  1. expose/scrape the runtime target that publishes `eigen_cluster_*` metrics,
  2. load `monitoring/metrics/prometheus/cluster-runtime-alerts.yaml`,
  3. import `monitoring/dashboards/cluster_runtime_sre_dashboard.json`,
  4. align on-call routing with `docs/howto/cluster-runtime-observability-runbook.md`.

## Minimum closure criteria for "contract fully realized"

1. A runtime endpoint exports all required metric names from this document in one environment profile.
2. Contract version marker metric is exported.
3. CI check asserts required metric names exist in scrape output (or explicit allowlist for staged rollout).
4. Runbook references are validated against live alert names and dashboard panel queries.
