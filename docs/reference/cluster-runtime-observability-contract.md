# Cluster Runtime Observability Contract

**Document status:** Stable
**Subsystem:** Distributed Runtime & Cluster Control Plane
**Contract version:** 1.0.0
**Applies to:** Eigen OS 1.0

This document defines the normative observability contract for distributed runtime execution, cluster scheduling, queue semantics, worker lifecycle management, tracing continuity, control-plane reliability, and distributed orchestration visibility in Eigen OS.

This contract specifies:

- mandatory cluster-runtime metrics,
- queue delivery observability,
- worker health telemetry,
- distributed execution visibility,
- tracing continuity guarantees,
- structured logging requirements,
- exporter semantics,
- alert compatibility,
- dashboard compatibility,
- telemetry cardinality constraints,
- and operational SRE invariants.

All metrics defined here are part of the stable public observability surface of Eigen OS 1.0.

---

## 1. Contract Marker

All cluster-runtime exporters MUST expose:

```text
eigen_cluster_runtime_contract_info{version="1.0.0"} 1
```
This metric is mandatory and serves as the compatibility marker for:

- dashboards,
- alerting systems,
- CI validation,
- telemetry conformance,
- runtime compatibility verification.

### SemVer Policy

#### MAJOR

Breaking changes:

- metric rename,
- metric removal,
- semantic/type changes,
- incompatible label changes,
- queue semantic changes,
- histogram incompatibility.

#### MINOR

Backward-compatible additions:

- additive metrics,
- additive labels,
- additive histogram buckets,
- delivery telemetry dimensions,
- trace attributes.

#### PATCH

Non-semantic corrections:

- exporter fixes,
- alert tuning,
- dashboard corrections,
- documentation clarifications,
- typo fixes.

---

## 2. Scope

This contract governs observability for:

- distributed runtime execution,
- cluster worker lifecycle,
- control-plane scheduling,
- distributed queue semantics,
- lease management,
- retry/redelivery behavior,
- dead-letter processing,
- distributed tracing continuity,
- cluster assignment latency,
- runtime orchestration health,
- replay/recovery workflows,
- autoscaling behavior,
- cluster failover visibility,
- distributed artifact persistence.

The contract applies to:

- standalone cluster deployments,
- multi-node runtime clusters,
- hybrid execution environments,
- elastic autoscaling deployments,
- replay/recovery environments,
- staging and canary environments.

---

## 3. Source of Truth

The following repository artifacts are normative:

```text
monitoring/metrics/prometheus/exporter.py
monitoring/metrics/prometheus/cluster-runtime-alerts.yaml
monitoring/dashboards/cluster_runtime_sre_dashboard.json
monitoring/metrics/tests/test_stage_observability.py
docs/howto/cluster-runtime-observability-runbook.md
```

Architecture references:

```text
docs/architecture/components/observability.md
docs/architecture/runtime/distributed-runtime.md
docs/architecture/contracts/telemetry.md
docs/architecture/runtime/queue-runtime.md
```

If implementation and documentation diverge:

1. exporter behavior,
2. CI validation,
3. Prometheus scrape output

take precedence over prose documentation.

---

## 4. Telemetry Architecture Requirements

Cluster-runtime observability MUST support:

- Prometheus metrics,
- distributed tracing,
- structured logs,
- replay diagnostics,
- deterministic runtime auditing,
- distributed correlation propagation.

Telemetry MUST remain operational during:

- scheduler degradation,
- partial node failures,
- worker restarts,
- queue failover,
- rolling deployments,
- partition recovery,
- exporter refreshes.

Observability systems MUST NOT become blocking dependencies for runtime execution.

---

## 5. Required Metrics

All metric families defined below are mandatory.

### 5.1 Worker Liveness & Node Availability

#### Worker heartbeats

```text
eigen_cluster_worker_heartbeats_total
```

Type:

- counter

Labels:

- `role`

Optional bounded labels:

- `node_class`

Definition:

- total successful worker heartbeat emissions.

Purpose:

- liveness validation,
- cluster availability tracking,
- partition detection.

`worker_id` MUST NOT be exposed as a metric label.

#### Worker flap events

```text
eigen_cluster_worker_flaps_total
```

Type:

- counter

Labels:

- `reason`

Allowed `reason` examples:

- `heartbeat_timeout`
- `lease_expired`
- `node_unreachable`
- `crash_restart`
- `evicted`
- `manual_restart`

Definition:

- worker availability transitions detected by the control plane.

#### Ready workers

```text
eigen_cluster_workers_ready
```

Type:

- gauge

Definition:

- workers currently eligible for task assignment.

A worker is considered ready when:

- heartbeat valid,
- lease valid,
- scheduler-visible,
- not draining,
- not quarantined,
- runtime initialized.

#### Draining workers

```text
eigen_cluster_workers_draining
```

Type:

- gauge

Definition:

- workers intentionally removed from active scheduling.

#### Worker quarantine events

```text
eigen_cluster_worker_quarantine_total
```

Type:

- counter

Labels:

- `reason`

Definition:

- workers quarantined due to reliability or policy violations.

#### Worker restart events

```text
eigen_cluster_worker_restarts_total
```

Type:

- counter

Definition:

- runtime worker process restarts.

---

### 5.2 Control Plane & Assignment Path

#### Assignment latency

```text
eigen_cluster_assignment_latency_ms
```

Type:

- histogram

Required exports:

- `_bucket`
- `_sum`
- `_count`

Definition:

- end-to-end latency between scheduling eligibility and assignment issuance.

Required buckets:

```text
1
5
10
25
50
100
250
500
1000
2500
5000
10000
+Inf
```

Histogram boundaries MUST remain backward-compatible within MAJOR version `1.x`.

#### Assignment failures

```text
eigen_cluster_assignment_failures_total
```

Type:

- counter

Labels:

- `reason`

Allowed values:

- `worker_unavailable`
- `lease_conflict`
- `capacity_exhausted`
- `routing_failure`
- `scheduler_timeout`
- `internal`

Definition:

- failed assignment attempts.

#### Scheduling decisions

```text
eigen_cluster_scheduling_decisions_total
```

Type:

- counter

Labels:

- `policy`
- `result`

Definition:

- cluster scheduling outcomes.

#### Scheduler evaluation latency

```text
eigen_cluster_scheduler_evaluation_latency_ms
```

Type:

- histogram

Definition:

- scheduler policy evaluation duration.

---

### 5.3 Queue Reliability & Delivery Semantics

#### Queue backlog depth

```text
eigen_cluster_queue_backlog_depth
```

Type:

- gauge

Labels:

- `queue`

Definition:

- pending items visible to distributed queue consumers.

#### Queue oldest age

```text
eigen_cluster_queue_oldest_age_seconds
```

Type:

- gauge

Labels:

- `queue`

Definition:

- age of the oldest non-acknowledged queue item.

Purpose:

- queue stall detection,
- starvation detection,
- scheduling degradation analysis.

#### Queue deliveries

```text
eigen_cluster_queue_deliveries_total
```

Type:

- counter

Labels:

- `queue`

Definition:

- queue item delivery attempts.

#### Queue acknowledgements

```text
eigen_cluster_queue_acknowledged_total
```

Type:

- counter

Labels:

- `queue`

Definition:

- successful queue acknowledgements.

#### Lease churn

```text
eigen_cluster_queue_lease_churn_total
```

Type:

- counter

Labels:

- `queue`
- `reason`

Allowed `reason` examples:

- `lease_expired`
- `worker_disconnect`
- `ack_timeout`
- `rebalance`
- `manual_requeue`

Definition:

- queue lease invalidation events.

#### Queue redeliveries

```text
eigen_cluster_queue_redeliveries_total
```

Type:

- counter

Labels:

- `queue`

Definition:

- queue items redelivered after lease expiration or processing interruption.

#### Dead-letter events

```text
eigen_cluster_dead_letter_total
```

Type:

- counter

Labels:

- `queue`
- `reason`

Allowed `reason` examples:

- `retry_limit_exceeded`
- `invalid_payload`
- `worker_failure`
- `execution_timeout`
- `poison_message`
- `internal`

Definition:

- queue items moved into dead-letter storage.

#### Queue replay events

```text
eigen_cluster_queue_replay_total
```

Type:

- counter

Definition:

- replay/recovery queue reinsertions.

#### Queue replay failures

```text
eigen_cluster_queue_replay_failures_total
```

Type:

- counter

Definition:

- replay/recovery failures during queue restoration.

---

### 5.4 Distributed Execution Reliability

#### Runtime execution failures

```text
eigen_cluster_execution_failures_total
```

Type:

- counter

Labels:

- `reason`

Definition:

- distributed execution failures.

#### Execution retries

```text
eigen_cluster_execution_retries_total
```

Type:

- counter

Labels:

- `reason`

Definition:

- runtime retries triggered by orchestration policies.

#### Runtime lease conflicts

```text
eigen_cluster_lease_conflicts_total
```

Type:

- counter

Definition:

- conflicting ownership or lease acquisition attempts.

#### Node partition detections

```text
eigen_cluster_partition_events_total
```

Type:

- counter

Definition:

- detected cluster network partition events.

#### Orchestrator failover events

```text
eigen_cluster_orchestrator_failover_total
```

Type:

- counter

Definition:

- orchestrator leadership or control-plane failover events.

---

### 5.5 Distributed Tracing Continuity

#### Trace continuity breakage

```text
eigen_cluster_trace_breakage_total
```

Type:

- counter

Labels:

- `stage`

Allowed `stage` examples:

- `scheduler`
- `dispatcher`
- `worker`
- `artifact_store`
- `runtime`
- `merge`

Definition:

- distributed trace continuity interruptions.

A trace breakage occurs when:

- trace propagation lost,
- parent-child relationship broken,
- trace context corrupted,
- span lineage incomplete.

#### Trace propagation latency

```text
eigen_cluster_trace_propagation_latency_ms
```

Type:

- histogram

Definition:

- latency of trace-context propagation across distributed boundaries.

---

## 6. Distributed Tracing Contract

Cluster-runtime services MUST support:

- W3C `traceparent`,
- W3C `tracestate`.

Required trace spans:

| **Span Name** | **Description** |
|----------|----------|
| `cluster.schedule` | scheduling decision |
| `cluster.assign` | worker assignment |
| `cluster.dispatch` | queue dispatch |
| `cluster.execute` | distributed execution |
| `cluster.retry` | retry orchestration |
| `cluster.replay` | replay/recovery flow |
| `cluster.persist` | distributed persistence |

Required trace attributes:

- `cluster.worker_role`
- `cluster.queue`
- `cluster.policy`
- `cluster.contract_version`
- `cluster.execution_state`

Trace continuity MUST survive:

- retries,
- queue redelivery,
- worker reassignment,
- replay recovery.

---

## 7. Structured Logging Contract

Structured logs MUST use deterministic machine-readable formats.

Recommended formats:

- JSON Lines,
- OpenTelemetry structured logs.

Required log fields:

| **Field** | **Description** |
|----------|----------|
| `timestamp` | UTC RFC3339 timestamp |
| `severity` | log severity |
| `service` | runtime component |
| `event` | deterministic event name |
| `trace_id` | distributed trace identifier |
| `queue` | logical queue identifier |

Sensitive information MUST NOT be logged.

Raw payloads MUST NOT be fully logged by default.

---

## 8. Label Contract

Label cardinality MUST remain bounded and deterministic.

### 8.1 Forbidden Labels

The following MUST NOT be used as metric labels:

- raw `job_id`
- `worker_id`
- `trace_id`
- `request_id`
- `correlation_id`
- arbitrary tenant identifiers
- arbitrary user identifiers
- payload-derived identifiers
- dynamic shard identifiers

These belong in:

- traces,
- structured logs,
- QFS artifacts,
- audit streams.

---

### 8.2 Allowed Bounded Labels

| **Label** | **Bound Type** |
|----------|----------|
| `queue` | finite configured queues |
| `reason` | stable enum taxonomy |
| `role` | finite worker roles |
| `policy` | finite scheduling policies |
| `stage` | finite pipeline stages |

---

### 8.3 Label Stability

Existing labels:

- MUST NOT change semantic meaning,
- MUST NOT become unbounded,
- MUST remain backward-compatible within MAJOR version `1.x`.

---

## 9. Queue Delivery Semantics

This contract assumes the Eigen OS distributed queue model supports:

- lease-based delivery,
- deterministic redelivery,
- replay-safe recovery,
- dead-letter routing,
- at-least-once delivery semantics,
- replay observability.

Telemetry MUST reflect:

- delivery attempts,
- acknowledgements,
- lease invalidation,
- retries,
- replay events,
- dead-letter transitions.

Queue telemetry MUST remain deterministic under replay and failover.

---

## 10. Exporter Requirements

Cluster-runtime exporters MUST:

1. expose valid Prometheus text exposition,
2. export all required metric families,
3. emit # TYPE declarations,
4. expose contract marker metric,
5. preserve snapshot consistency,
6. tolerate partial subsystem failures,
7. avoid blocking runtime execution paths,
8. avoid unbounded series generation.

Exporters MUST NOT:

- panic during scrape,
- emit unbounded labels,
- expose malformed histogram families,
- dynamically mutate metric semantics,
- emit inconsistent snapshots.

---

## 11. Alert Compatibility Contract

Prometheus alert rules are maintained in:

```text
monitoring/metrics/prometheus/cluster-runtime-alerts.yaml
```

### 11.1 Critical Alerts

#### Queue stall

Triggers when:

- queue age exceeds SLO,
- dispatch throughput collapses,
- queue backlog grows uncontrollably.

#### Redelivery-rate breach

Triggers when:

- redelivery ratio exceeds reliability budget.

#### Assignment latency SLO breach

Triggers when:

- assignment p95 exceeds configured thresholds.

#### Trace continuity breakage

Triggers when:

- distributed trace propagation fails above threshold.

#### Partition detection

Triggers when:

- cluster partition events detected.

#### Dead-letter surge

Triggers when:

- dead-letter growth exceeds error budget.

#### Exporter health degradation

Triggers when:

- scrape failures occur,
- contract marker disappears,
- telemetry freshness exceeds threshold.

---

### 11.2 Warning Alerts

#### Worker flap increase

Triggers when:

- worker instability rises above baseline.

#### Lease churn increase

Triggers when:

- lease invalidation frequency spikes.

#### Retry amplification

Triggers when:

- execution retry volume increases abnormally.

---

## 12. Dashboard Compatibility Contract

Grafana dashboard:

```text
monitoring/dashboards/cluster_runtime_sre_dashboard.json
```

Dashboard MUST include:

- worker availability,
- worker heartbeat health,
- assignment latency percentiles,
- queue backlog,
- queue age,
- lease churn,
- redelivery ratio,
- dead-letter volume,
- retry rates,
- partition events,
- trace continuity health,
- exporter health,
- contract marker visibility.

Dashboards MUST remain backward-compatible within MAJOR version `1.x`.

---

## 13. Runtime Integration Requirements

At least one live runtime environment MUST export all required metrics end-to-end.

Supported deployment topologies:

- standalone cluster runtime,
- distributed multi-node runtime,
- autoscaled execution pools,
- replay/recovery clusters,
- hybrid cloud deployments.

Metrics MUST survive:

- rolling restarts,
- worker rescheduling,
- node replacement,
- partition recovery,
- queue replay,
- exporter refreshes,
- orchestrator failover.

Observability MUST degrade gracefully under overload conditions.

---

## 14. CI & Conformance Requirements

CI MUST validate:

1. required metric family presence,
2. valid metric types,
3. histogram integrity,
4. contract marker version,
5. alert query compatibility,
6. dashboard query compatibility,
7. bounded-label enforcement,
8. trace propagation compatibility.

Required conformance tests:

- scrape validation,
- queue semantic validation,
- replay metric validation,
- dead-letter metric validation,
- redelivery semantic validation,
- trace continuity validation,
- histogram validation,
- label-cardinality validation.

CI failures MUST block incompatible observability changes.

---

## 15. Operational Invariants

The following invariants are mandatory.

#### Deterministic delivery telemetry

The same queue event MUST map to the same metric semantics.

#### Monotonic counters

Counter metrics MUST NEVER decrease.

#### Stable histogram buckets

Histogram bucket boundaries MUST remain compatible within the same MAJOR version.

#### Bounded cardinality

Runtime behavior MUST NOT generate unbounded metric series.

#### Export isolation

Telemetry failures MUST NOT terminate runtime execution.

#### Replay visibility

Replay and recovery operations MUST remain observable.

#### Trace continuity

Distributed trace propagation MUST remain deterministic across retries and redelivery paths.

---

## 16. Security & Isolation

Observability systems MUST:

- isolate tenant telemetry,
- prevent unauthorized metric exposure,
- prevent trace leakage across tenants,
- sanitize structured logs,
- redact sensitive metadata.

Exporters SHOULD support:

- TLS transport,
- authenticated scraping,
- RBAC-compatible dashboard access.

---

## 17. Migration Rules

#### Additive migration

New metrics MAY be introduced in MINOR releases.

#### Deprecation policy

Deprecated metrics MUST remain available for at least one MINOR release.

Deprecated metrics MUST:

- remain documented,
- emit compatibility telemetry,
- include migration guidance.

#### Breaking migration

Breaking changes require:

- MAJOR version bump,
- exporter updates,
- dashboard updates,
- alert updates,
- migration documentation,
- CI compatibility updates.

---

## 18. Compatibility Guarantees

Eigen OS guarantees:

- stable metric names within MAJOR versions,
- deterministic distributed-runtime telemetry semantics,
- bounded label behavior,
- backward-compatible MINOR additions,
- SemVer-governed observability evolution.

These guarantees apply to:

- operators,
- SRE automation,
- dashboards,
- alerting systems,
- distributed runtime tooling,
- enterprise monitoring integrations,
- replay tooling,
- cluster orchestration systems.
