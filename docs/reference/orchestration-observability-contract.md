# Orchestration Observability Contract

- **Subsystem:** Scheduler and orchestration control plane
- **Contract type:** Stable observability contract
- **Contract version:** `3.1.0`
- **Applies to:** Scheduler, Queue Manager, Fairness Controller, Quota Manager, Rebalancer, Runtime Dispatcher, Placement Engine, Retry Controller

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
- orchestration retry telemetry,
- shard assignment observability,
- scheduling policy execution visibility,
- degraded orchestration behavior,
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
- placement evaluation,
- rebalance operations,
- starvation mitigation,
- orchestration retries,
- scheduling policy execution,
- orchestration degradation handling,
- scheduler failover behavior.

This contract does not define:

- intelligent runtime scoring metrics,
- benchmark telemetry,
- cluster-runtime telemetry,
- backend-provider telemetry.

Those are defined in separate contracts.

---

## 3. Contract versioning

### 3.1 Current Version

```text
eigen_orch_contract_info{version="3.1.0"} 1
```

### 3.2 SemVer Policy

#### MAJOR

Required for:

- metric rename/removal,
- metric semantic changes,
- metric type changes,
- incompatible label changes,
- incompatible histogram semantic changes.

#### MINOR

Used for:

- additive metrics,
- additive labels,
- histogram additions,
- bounded-cardinality extensions,
- additive telemetry dimensions.

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
- deterministic metric naming,
- stable histogram semantics,
- concurrent scrape safety,
- Prometheus text exposition format.

---

## 5. Design Principles

### 5.1 Deterministic Metric Semantics

The same orchestration condition MUST produce the same metric semantics.

---

### 5.2 Bounded Cardinality

All labels MUST remain bounded and operator-safe.

---

### 5.3 Operational Explainability

Scheduling decisions, fairness corrections, throttling, and rebalancing MUST remain observable.

---

### 5.4 Replay-Safe Telemetry

Replay or retry execution MUST NOT produce ambiguous orchestration telemetry semantics.

---

### 5.5 Failure Visibility

Control-plane degradation MUST remain externally observable.

Silent orchestration degradation is prohibited.

---

## 6. Stable Public Metrics Surface

All metric names in this section are stable public API.

---

## 7. Queue Health Metrics

### 7.1 Queue Depth

```text
eigen_orch_queue_depth{queue}
```

Type: `gauge`

Meaning:

- current number of queued orchestration tasks.

---

### 7.2 Oldest Queue Age

```text
eigen_orch_queue_oldest_age_seconds{queue}
```

Type: `gauge`

Meaning:

- age of the oldest queued item.

---

### 7.3 Average Queue Age

```text
eigen_orch_queue_avg_age_seconds{queue}
```

Type: `gauge`

Meaning:

- moving average queue wait duration.

---

### 7.4 Queue Enqueue Throughput

```text
eigen_orch_queue_enqueue_total{queue}
```

Type: `counter`

Meaning:

- total enqueue operations.

---

### 7.5 Queue Dequeue Throughput

```text
eigen_orch_queue_dequeue_total{queue}
```

Type: `counter`

Meaning:

- total dequeue operations.

---

### 7.6 Queue Dispatch Latency

```text
eigen_orch_dispatch_latency_ms_bucket{queue}
eigen_orch_dispatch_latency_ms_sum{queue}
eigen_orch_dispatch_latency_ms_count{queue}
```

Type: `histogram`

Meaning:

- scheduler-to-runtime dispatch latency.

---

## 8. Fairness Enforcement Metrics

### 8.1 Fairness Lag Cumulative

```text
eigen_orch_fairness_lag_millis_total{policy_mode}
```

Type: `counter`

Meaning:

- accumulated fairness delay introduced by scheduling policy.

---

### 8.2 Maximum Fairness Lag

```text
eigen_orch_fairness_lag_millis_max{policy_mode}
```

Type: `gauge`

Meaning:

- highest observed fairness lag.

---

### 8.3 Fairness Correction Events

```text
eigen_orch_fairness_corrections_total{reason}
```

Type: `counter`

Meaning:

- number of fairness rebalance corrections applied.

#### Allowed `reason`

```text
starvation_prevention
quota_rebalance
priority_normalization
tenant_fairness
project_fairness
manual_override
```

---

## 9. Quota Enforcement Metrics

### 9.1 Tenant Quota Denials

```text
eigen_orch_quota_denied_tenant_total{tenant}
```

Type: `counter`

Meaning:

- rejected operations due to tenant quota limits.

---

### 9.2 Project Quota Denials

```text
eigen_orch_quota_denied_project_total{project}
```

Type: `counter`

Meaning:

- rejected operations due to project quota limits.

---

### 9.3 Runtime Quota Throttling

```text
eigen_orch_quota_throttled_total{reason}
```

Type: `counter`

Meaning:

- operations delayed due to soft quota throttling.

#### Allowed `reason`

```text
tenant_limit
project_limit
cluster_capacity
fairness_guardrail
burst_control
```

---

## 10. Rebalancing Metrics

### 10.1 Rebalance Triggers

```text
eigen_orch_rebalance_trigger_total{reason}
```

Type: `counter`

Meaning:

- number of scheduler rebalance operations initiated.

#### Allowed `reason`

```text
capacity_imbalance
starvation_risk
backend_pressure
fairness_violation
topology_shift
manual_override
```

---

### 10.2 Rebalance Duration

```text
eigen_orch_rebalance_duration_ms_bucket{reason}
eigen_orch_rebalance_duration_ms_sum{reason}
eigen_orch_rebalance_duration_ms_count{reason}
```

Type: `histogram`

Meaning:

- rebalance execution duration.

---

### 10.3 Rebalance Failures

```text
eigen_orch_rebalance_failures_total{reason}
```

Type: `counter`

Meaning:

- failed rebalance operations.

---

## 11. Starvation Prevention Metrics

### 11.1 Starvation Prevention Actions

```text
eigen_orch_starvation_prevention_total{queue}
```

Type: `counter`

Meaning:

- starvation mitigation interventions.

---

### 11.2 Long-Wait Task Count

```text
eigen_orch_starved_tasks{queue}
```

Type: `gauge`

Meaning:

- currently starved queued tasks.

---

## 12. Scheduler Health Metrics

### 12.1 Scheduling Decisions

```text
eigen_orch_scheduler_decisions_total{policy_mode}
```

Type: `counter`

Meaning:

- completed scheduler decisions.

---

### 12.2 Scheduler Failures

```text
eigen_orch_scheduler_failures_total{reason}
```

Type: `counter`

Meaning:

- internal scheduler failures.

#### Allowed `reason`

```text
policy_failure
placement_failure
capacity_exhausted
timeout
state_divergence
internal_error
```

---

### 12.3 Scheduling Latency

```text
eigen_orch_scheduler_latency_ms_bucket{policy_mode}
eigen_orch_scheduler_latency_ms_sum{policy_mode}
eigen_orch_scheduler_latency_ms_count{policy_mode}
```

Type: `histogram`

Meaning:

- scheduling evaluation latency.

---

## 13. Runtime Coordination Metrics

### 13.1 Assignment Operations

```text
eigen_orch_assignments_total{queue}
```

Type:

Type: `counter`

Meaning:

- orchestration assignment operations.

---

### 13.2 Assignment Failures

```text
eigen_orch_assignment_failures_total{reason}
```

Type: `counter`

Meaning:

- failed runtime assignments.

#### Allowed `reason`

```text
backend_unavailable
lease_conflict
capacity_exhausted
network_partition
timeout
internal_error
```

---

### 13.3 Assignment Latency

```text
eigen_orch_assignment_latency_ms_bucket
eigen_orch_assignment_latency_ms_sum
eigen_orch_assignment_latency_ms_count
```

Type: `histogram`

Meaning:

- end-to-end orchestration assignment latency.

---

## 14. Retry and Redelivery Metrics

### 14.1 Retry Attempts

```text
eigen_orch_retries_total{reason}
```

Type: `counter`

Meaning:

- orchestration retry attempts.

#### Allowed `reason`

```text
transient_failure
lease_expired
worker_unavailable
dispatch_timeout
merge_retry
```

---

### 14.2 Dead Letter Events

```text
eigen_orch_dead_letter_total{reason}
```
Type: `counter`

Meaning:

- permanently failed orchestration items moved to dead-letter handling.

---

## 15. Degraded Mode Metrics

### 15.1 Degraded Mode Activation

```text
eigen_orch_degraded_mode_total{mode}
```

Type: `counter`

Meaning:

- degraded orchestration mode activations.

#### Allowed `mode`

```text
safe_scheduling
single_queue_mode
reduced_fairness
retry_only_mode
manual_dispatch
```
---

### 15.2 Scheduler Failover Events

```text
eigen_orch_failover_total{reason}
```

Type: `counter`

Meaning:

- scheduler failover activations.

---

## 16. Snapshot Freshness Metrics

### 16.1 Last Snapshot Timestamp

```text
eigen_orch_snapshot_timestamp_seconds
```

Type: `gauge`

Meaning:

- last successful exporter snapshot timestamp.

---

### 16.2 Snapshot Age

```text
eigen_orch_snapshot_age_seconds
```

Type: `gauge`

Meaning:

- current snapshot staleness.

---

## 17. Label Contract

### 17.1 Stable Labels

The following labels are allowed:

| **Label** | **Meaning** |
|---|---|
| `queue` | Queue identifier |
| `tenant` | Tenant identifier |
| `project` | Project identifier |
| `policy_mode` | Scheduler policy |
| `reason` | Failure/rebalance reason |
| `mode` | Degraded orchestration mode |

---

### 17.2 Label Cardinality Rules

All labels MUST:

- remain bounded,
- remain deterministic,
- avoid unbounded user-generated values,
- avoid trace-level identifiers,
- remain operationally enumerable.

Forbidden labels:

- `job_id`
- `trace_id`
- `request_id`
- `user_id`
- arbitrary user input
- backend payloads
- freeform error messages

---

## 18. Metric Type Guarantees

Metric types are part of the compatibility contract.

Prometheus exposition MUST include: `# TYPE`

declarations for every public metric.

Changing metric type requires a MAJOR version bump.

---

## 19. Histogram Bucket Policy

Histogram metrics SHOULD use stable buckets.

Recommended latency buckets:

```yaml
[1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000]
```

Units:

- milliseconds for latency histograms,
- seconds for age gauges.

The following metrics MUST use histograms:

- dispatch latency,
- scheduler latency,
- assignment latency,
- rebalance duration.

---

## 20. Source of Truth

Normative assets:

| **Artifact** | **Path** |
|---|---|
| Exporter | `monitoring/metrics/prometheus/exporter.py` |
| Alerts | `monitoring/metrics/prometheus/orchestrator-alerts.yaml` |
| Dashboard | `monitoring/dashboards/orchestration_dashboard.json` |
| Tests | `monitoring/metrics/tests/test_stage_observability.py` |
| Runbook | `docs/howto/orchestrator-observability-runbook.md` |

---

## 21. Alert Contract

### 21.1 Critical Alerts

The orchestration stack MUST support alerts for:

- queue stall,
- scheduler outage,
- rebalance failures,
- starvation surge,
- quota denial spike,
- assignment failure rate breach,
- stale telemetry snapshots,
- failover activation surge,
- degraded scheduling activation.

---

### 21.2 Warning Alerts

Warning-level alerts SHOULD include:

- elevated queue age,
- fairness lag increase,
- dispatch latency degradation,
- rebalance frequency increase,
- retry amplification,
- dead-letter growth.

---

## 22. Dashboard Contract

The orchestration dashboard MUST expose:

- queue depth,
- queue age,
- scheduling latency,
- fairness lag,
- rebalance activity,
- starvation events,
- quota denials,
- orchestration throughput,
- retry activity,
- degraded mode activation,
- snapshot freshness,
- contract version visibility.

---

## 23. Runtime Implementation Requirements

Conformant implementations MUST:

1. Export all required metrics.
2. Expose valid Prometheus text format.
3. Preserve metric type stability.
4. Preserve label cardinality guarantees.
5. Export contract marker metric.
6. Maintain deterministic metric semantics.
7. Preserve histogram semantic consistency.
8. Support concurrent Prometheus scraping.

---

## 24. CI and Conformance Requirements

CI MUST validate:

- required metric presence,
- metric type consistency,
- contract version marker,
- dashboard query validity,
- alert query validity,
- exporter scrape success,
- histogram family completeness,
- label cardinality constraints.

Golden tests SHOULD validate:

- scheduler fairness behavior,
- starvation prevention metrics,
- quota enforcement telemetry,
- rebalance instrumentation,
- histogram bucket consistency,
- retry instrumentation,
- degraded-mode observability.

---

## 25. Migration Policy

### 25.1 Backward Compatibility

Existing orchestration metric families MUST remain compatible across MINOR releases.

---

### 25.2 Deprecation Policy

Metrics MAY only be removed after:

1. explicit deprecation marking,
2. at least one MINOR release cycle,
3. dashboard/alert migration guidance,
4. CI migration validation.

---

## 26. Operational Requirements

Production deployments SHOULD:

1. scrape orchestration metrics continuously,
2. preserve long-term queue latency history,
3. alert on stale exporter snapshots,
4. correlate orchestration metrics with cluster-runtime telemetry,
5. preserve fairness and starvation audit history,
6. retain retry and rebalance telemetry,
7. monitor degraded orchestration modes continuously.

---

## 27. Security Considerations

The observability pipeline MUST avoid exposing:

- sensitive tenant identifiers,
- authentication material,
- user payload data,
- backend credentials,
- unbounded runtime metadata,
- secret scheduling policy inputs.

Metrics MUST remain operationally safe for multi-tenant deployments.

---

## 28. Future Evolution

Planned future extensions include:

- topology-aware scheduling metrics,
- weighted fairness telemetry,
- per-tenant SLO metrics,
- adaptive queue analytics,
- orchestration trace correlation,
- scheduling replay telemetry,
- predictive starvation analytics,
- placement explainability telemetry.

---

## 29. Invariants

The following invariants are mandatory:

1. Public metric names are stable.
2. Metric semantics are deterministic.
3. Metric types are immutable within MAJOR versions.
4. Label cardinality remains bounded.
5. Alerts and dashboards MUST evolve together with metric changes.
6. Contract version markers MUST remain synchronized across code, dashboards, tests, and documentation.
7. Orchestration telemetry MUST remain replay-safe and operationally auditable.
8. Scheduler degradation MUST remain externally observable.
9. Histogram semantics MUST remain stable within a MAJOR version.
