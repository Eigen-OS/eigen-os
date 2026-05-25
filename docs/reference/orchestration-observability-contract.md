# Orchestration Observability Contract

- **Subsystem:** Scheduler and orchestration control plane
- **Contract type:** Stable observability contract
- **Contract version:** `3.0.0`
- **Applies to:** Scheduler, Queue Manager, Fairness Controller, Quota Manager, Rebalancer, Runtime Dispatcher
- **Last updated:** 2026-05-24

---

## 1. Purpose

This document defines the normative observability contract for the Eigen OS orchestration layer.

The contract standardizes:

- scheduler telemetry,
- queue health metrics,
- fairness enforcement visibility,
- quota enforcement telemetry,
- starvation prevention monitoring,
- rebalance operations,
- orchestration latency monitoring,
- control-plane SLO monitoring,
- operational dashboards and alerts.

This contract defines the stable public metrics surface for all orchestration-related runtime telemetry.

---

## 2. Scope

The orchestration observability contract applies to:

- queue management,
- scheduling,
- dispatch coordination,
- fairness enforcement,
- quota enforcement,
- shard assignment,
- rebalance operations,
- starvation mitigation,
- orchestration retries,
- scheduling policy execution.

This contract does not define:

- intelligent runtime scoring metrics,
- benchmark telemetry,
- cluster-runtime telemetry,
- backend-provider telemetry.

Those are defined in separate contracts.

---

## 3. Contract versioning

### Current version

```text
eigen_orch_contract_info{version="3.0.0"} 1
```

### SemVer policy

#### MAJOR

Required for:

- metric rename/removal,
- metric semantic changes,
- metric type changes,
- incompatible label changes.

#### MINOR

Used for:

- additive metrics,
- additive labels,
- histogram additions,
- bounded-cardinality extensions.

#### PATCH

Used for:

- documentation corrections,
- alert tuning,
- dashboard fixes,
- implementation fixes without public semantic changes.

---

## 4. Observability architecture

The orchestration observability pipeline is:

```text
Scheduler
  ↓
Orchestration Telemetry Exporter
  ↓
Prometheus
  ↓
Alert Rules
  ↓
Grafana Dashboards
  ↓
Operational Runbooks
```

The orchestration exporter MUST expose:

- stable Prometheus metric families,
- explicit metric typing,
- bounded-cardinality labels,
- deterministic metric naming.

---

## 5. Stable public metrics surface

All metric names in this section are stable public API.

---

## 6. Queue health metrics

### Queue depth

```text
eigen_orch_queue_depth
```

Type:

```text
gauge
```

Meaning:

- current number of queued orchestration tasks.

---

### Oldest queue age

```text
eigen_orch_queue_oldest_age_seconds
```

Type:

```text
gauge
```

Meaning:

- age of the oldest queued item.

---

### Average queue age

```text
eigen_orch_queue_avg_age_seconds
```

Type:

```text
gauge
```

Meaning:

- moving average queue wait duration.

---

### Queue enqueue throughput

```text
eigen_orch_queue_enqueue_total
```

Type:

```text
counter
```

Meaning:

- total enqueue operations.

---

### Queue dequeue throughput

```text
eigen_orch_queue_dequeue_total
```

Type:

```text
counter
```

Meaning:

- total dequeue operations.

---

### Queue dispatch latency

```text
eigen_orch_dispatch_latency_ms
```

Type:

```text
histogram
```

Meaning:

- scheduler-to-runtime dispatch latency.

---

## 7. Fairness enforcement metrics

### Fairness lag cumulative

```text
eigen_orch_fairness_lag_millis_total
```

Type:

```text
counter
```

Meaning:

- accumulated fairness delay introduced by scheduling policy.

---

### Maximum fairness lag

```text
eigen_orch_fairness_lag_millis_max
```

Type:

```text
gauge
```

Meaning:

- highest observed fairness lag.

---

### Fairness correction events

```text
eigen_orch_fairness_corrections_total
```

Type:

```text
counter
```

Meaning:

- number of fairness rebalance corrections applied.

---

## 8. Quota enforcement metrics

### Tenant quota denials

```text
eigen_orch_quota_denied_tenant_total
```

Type:

```text
counter
```

Meaning:

- rejected operations due to tenant quota limits.

---

### Project quota denials

```text
eigen_orch_quota_denied_project_total
```

Type:

```text
counter
```

Meaning:

rejected operations due to project quota limits.

---

### Runtime quota throttling

```text
eigen_orch_quota_throttled_total
```

Type:

```text
counter
```

Meaning:

- operations delayed due to soft quota throttling.

---

## 9. Rebalancing metrics

### Rebalance triggers

```text
eigen_orch_rebalance_trigger_total
```

Type:

```text
counter
```

Meaning:

- number of scheduler rebalance operations initiated.

---

### Rebalance duration

```text
eigen_orch_rebalance_duration_ms
```

Type:

```text
histogram
```

Meaning:

- rebalance execution duration.

---

### Rebalance failures

```text
eigen_orch_rebalance_failures_total
```

Type:

```text
counter
```

Meaning:

- failed rebalance operations.

---

## 10. Starvation prevention metrics

### Starvation prevention actions

```text
eigen_orch_starvation_prevention_total
```

Type:

```text
counter
```

Meaning:

- starvation mitigation interventions.

---

### Long-wait task count

```text
eigen_orch_starved_tasks
```

Type:

```text
gauge
```

Meaning:

- currently starved queued tasks.

---

## 11. Scheduler health metrics

### Scheduling decisions

```text
eigen_orch_scheduler_decisions_total
```

Type:

```text
counter
```

Meaning:

- completed scheduler decisions.

---

### Scheduler failures

```text
eigen_orch_scheduler_failures_total
```

Type:

```text
counter
```

Meaning:

- internal scheduler failures.

---

### Scheduling latency

```text
eigen_orch_scheduler_latency_ms
```

Type:

```text
histogram
```

Meaning:

- scheduling evaluation latency.

---

## 12. Runtime coordination metrics

### Assignment operations

```text
eigen_orch_assignments_total
```

Type:

```text
counter
```

Meaning:

- orchestration assignment operations.

---

### Assignment failures

```text
eigen_orch_assignment_failures_total
```

Type:

```text
counter
```

Meaning:

- failed runtime assignments.

---

## 13. Snapshot freshness metrics

### Last snapshot timestamp

```text
eigen_orch_snapshot_timestamp_seconds
```

Type:

```text
gauge
```

Meaning:

- last successful exporter snapshot timestamp.

---

### Snapshot age

```text
eigen_orch_snapshot_age_seconds
```

Type:

```text
gauge
```

Meaning:

- current snapshot staleness.

---

## 14. Label contract

### Stable labels

The following labels are allowed:

| **Label** | **Meaning** |
|---|---|
| `queue` | Queue identifier |
| `tenant` | Tenant identifier |
| `project` | Project identifier |
| `policy_mode` | Scheduler policy |
| `reason` | Failure/rebalance reason |

---

### Label cardinality rules

All labels MUST:

- remain bounded,
- remain deterministic,
- avoid unbounded user-generated values,
- avoid trace-level identifiers.

Forbidden labels:

- `job_id`
- `trace_id`
- `request_id`
- arbitrary user input

---

## 15. Metric type guarantees

Metric types are part of the compatibility contract.

Prometheus exposition MUST include:

```text
# TYPE
```

declarations for every public metric.

Changing metric type requires a MAJOR version bump.

---

## 16. Histogram bucket policy

Histogram metrics SHOULD use stable buckets.

Recommended latency buckets:

```yaml
[1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000]
```

Units:

- milliseconds for latency histograms,
- seconds for age gauges.

---

## 17. Source of truth

Normative assets:

| **Artifact** | **Path** |
|---|---|
| Exporter | `monitoring/metrics/prometheus/exporter.py` |
| Alerts | `monitoring/metrics/prometheus/orchestrator-alerts.yaml` |
| Dashboard | `monitoring/dashboards/orchestration_dashboard.json` |
| Tests | `monitoring/metrics/tests/test_stage_observability.py` |
| Runbook | `docs/howto/orchestrator-observability-runbook.md` |

---

## 18. Alert contract

### Critical alerts

The orchestration stack MUST support alerts for:

- queue stall,
- scheduler outage,
- rebalance failures,
- starvation surge,
- quota denial spike,
- assignment failure rate breach,
- stale telemetry snapshots.

### Warning alerts

Warning-level alerts SHOULD include:

- elevated queue age,
- fairness lag increase,
- dispatch latency degradation,
- rebalance frequency increase.

---

## 19. Dashboard contract

The orchestration dashboard MUST expose:

- queue depth,
- queue age,
- scheduling latency,
- fairness lag,
- rebalance activity,
- starvation events,
- quota denials,
- orchestration throughput,
- snapshot freshness,
- contract version visibility.

---

20. Runtime implementation requirements

Conformant implementations MUST:

1. Export all required metrics.
2. Expose valid Prometheus text format.
3. Preserve metric type stability.
4. Preserve label cardinality guarantees.
5. Export contract marker metric.
6. Maintain deterministic metric semantics.

---

## 21. CI and conformance requirements

CI MUST validate:

- required metric presence,
- metric type consistency,
- contract version marker,
- dashboard query validity,
- alert query validity,
- exporter scrape success.

Golden tests SHOULD validate:

- scheduler fairness behavior,
- starvation prevention metrics,
- quota enforcement telemetry,
- rebalance instrumentation,
- histogram bucket consistency.

---

## 22. Migration policy

### Backward compatibility

Existing orchestration metric families MUST remain compatible across MINOR releases.

### Deprecation policy

Metrics MAY only be removed after:

1. explicit deprecation marking,
2. at least one MINOR release cycle,
3. dashboard/alert migration guidance.

---

## 23. Operational requirements

Production deployments SHOULD:

1. scrape orchestration metrics continuously,
2. preserve long-term queue latency history,
3. alert on stale exporter snapshots,
4. correlate orchestration metrics with cluster-runtime telemetry,
5. preserve fairness and starvation audit history.

---

## 24. Security considerations

The observability pipeline MUST avoid exposing:

- sensitive tenant identifiers,
- authentication material,
- user payload data,
- backend credentials,
- unbounded runtime metadata.

Metrics MUST remain operationally safe for multi-tenant deployments.

---

## 25. Future evolution

Planned future extensions include:

- topology-aware scheduling metrics,
- weighted fairness telemetry,
- per-tenant SLO metrics,
- adaptive queue analytics,
- orchestration trace correlation,
- scheduling replay telemetry,
- predictive starvation analytics.

---

## 26. Invariants

The following invariants are mandatory:

1. Public metric names are stable.
2. Metric semantics are deterministic.
3. Metric types are immutable within MAJOR versions.
4. Label cardinality remains bounded.
5. Alerts and dashboards MUST evolve together with metric changes.
6. Contract version markers MUST remain synchronized across code,  dashboards, tests, and documentation.
7. Orchestration telemetry MUST remain replay-safe and operationally auditable.
