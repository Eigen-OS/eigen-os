# Benchmark Observability Contract

**Document status:** Stable
**Subsystem:** Benchmark Runtime & SRE Telemetry
**Contract version:** `1.0.0`
**Applies to:** Eigen OS 1.0

This document defines the normative observability contract for benchmark execution, ingestion, scheduling visibility, reliability monitoring, and operational SRE coverage in Eigen OS.

The contract specifies:

- mandatory metric families,

- semantic guarantees,

- label constraints,

- alerting compatibility,

- dashboard compatibility,

- exporter behavior,

- and operational invariants.

This contract is part of the stable public observability surface of Eigen OS 1.0.

---

## 1. Contract Marker

All benchmark telemetry exporters MUST expose:

```text
eigen_bench_contract_info{version="1.0.0"} 1
```

### SemVer Policy

#### MAJOR

Breaking changes:

- metric rename,

- metric removal,

- semantic/type changes,

- incompatible label changes.

#### MINOR

Backward-compatible additions:

- additive metrics,

- additive labels,

- new histogram buckets,

- new optional telemetry dimensions.

#### PATCH

Non-semantic corrections:

- exporter fixes,

- documentation clarifications,

- alert tuning,

- dashboard corrections.

---

## 2. Scope

This contract governs observability for:

- benchmark scheduling,

- benchmark queue lifecycle,

- benchmark execution,

- ingestion pipelines,

- benchmark artifact persistence,

- benchmark replay,

- benchmark result validation,

- benchmark runtime reliability,

- benchmark orchestration health.

The contract applies to:

- standalone benchmark runtime,

- distributed benchmark execution,

- CI benchmark environments,

- replay environments,

- production observability deployments.

---

## 3. Source of Truth

The following repository artifacts are normative:

- `monitoring/metrics/prometheus/exporter.py`

- `monitoring/metrics/prometheus/benchmark-alerts.yaml`

- `monitoring/dashboards/benchmark_dashboard.json`

- `monitoring/metrics/tests/test_stage_observability.py`

- `docs/howto/benchmark-observability-runbook.md`

Architecture references:

- `docs/architecture/components/observability.md`

- `docs/architecture/runtime/benchmark-runtime.md`

- `docs/architecture/contracts/telemetry.md`

---

## 4. Required Metrics

All metrics listed below are mandatory.

### 4.1 Queue Health

#### Queue depth

```text
eigen_bench_queue_depth
```

Type:

- gauge

Definition:

- current number of queued benchmark executions awaiting scheduling.

Invariants:

- MUST NOT be negative,

- MUST reflect scheduler-visible queue state,

- MUST update monotonically with enqueue/dequeue events.

### Oldest queued benchmark age

```text
eigen_bench_queue_oldest_age_seconds
```

Type:

- gauge

Definition:

- age in seconds of the oldest benchmark still waiting for execution.

Purpose:

- starvation detection,

- scheduler degradation detection,

- stuck queue detection.

### Queue throughput

```text
eigen_bench_queue_dispatch_total
```

Type:

- counter

Labels:

- `result`

Allowed values:

- `scheduled`

- `rejected`

- `delayed`

Definition:

- total benchmark dispatch decisions.

---

### 4.2 Benchmark Execution Lifecycle

#### Benchmark runtime duration

```text
eigen_bench_run_duration_seconds
```

Type:

- histogram

Required histogram exports:

- `_bucket`

- `_sum`

- `_count`

Definition:

- total benchmark runtime duration from execution start to terminal completion.

Required buckets:

```text
0.1
0.5
1
2
5
10
30
60
120
300
600
1800
3600
+Inf
```

#### Successful benchmark executions

```text
eigen_bench_runs_succeeded_total
```

Type:

- counter

Labels:

- `backend`

- `mode`

Definition:

- successful benchmark completions.

#### Failed benchmark executions

```text
eigen_bench_runs_failed_total
```

Type:

- counter

Labels:

- `backend`

- `reason`

Definition:

- benchmark executions ending in terminal failure state.

Allowed `reason` examples:

- `timeout`

- `backend_unavailable`

- `validation_failed`

- `quota_exceeded`

- `internal`

- `cancelled`

#### Cancelled benchmark executions

```text
eigen_bench_runs_cancelled_total
```

Type:

- counter

Definition:

- benchmarks cancelled before successful completion.

#### Active benchmark executions

```text
eigen_bench_active_runs
```

Type:

- gauge

Definition:

-  benchmarks currently executing.

---

### 4.3 Ingestion & Artifact Pipeline

#### Ingestion failures

```text
eigen_bench_ingestion_failures_total
```

Type:

- counter

Labels:

- `stage`

- `reason`

Definition:

- failures while ingesting benchmark artifacts, telemetry, traces, or result payloads.

#### Artifact persistence latency

```text
eigen_bench_artifact_persist_latency_seconds
```

Type:

- histogram

Definition:

- latency for durable persistence of benchmark artifacts.

#### Artifact validation failures

```text
eigen_bench_artifact_validation_failures_total
```

Type:

- counter

Definition:

- benchmark artifacts rejected due to schema/checksum/contract violations.

---

### 4.4 Reliability & Runtime Safety

#### Stalled benchmark runs

```text
eigen_bench_stalled_runs
```

Type:

- gauge

Definition:

- benchmarks exceeding configured runtime liveness thresholds.

A run is considered stalled when:

- no progress heartbeat exceeds runtime policy,

- no terminal state emitted,

- runtime lease expired,

- or orchestration continuity is lost.

#### Benchmark replay mismatches

```text
eigen_bench_replay_mismatch_total
```

Type:

- counter

Definition:

- deterministic replay output mismatches.

#### Benchmark runtime panics

```text
eigen_bench_runtime_panics_total
```

Type:

- counter

Definition:

- unrecoverable runtime faults during benchmark execution.

---

### 4.5 Scheduler & Resource Pressure

#### Scheduler latency

```text
eigen_bench_scheduler_latency_seconds
```

Type:

- histogram

Definition:

- latency between enqueue and scheduling decision.

#### Resource exhaustion events

```text
eigen_bench_resource_exhausted_total
```

Type:

- counter

Labels:

- `resource`

Allowed values:

- `cpu`

- `memory`

- `gpu`

- `disk`

- `network`

- `quota`

---

## 5. Label Contract

Label cardinality MUST remain bounded and deterministic.

### Forbidden labels

The following MUST NOT be used directly as metric labels:

- `job_id`

- `trace_id`

- `request_id`

- `correlation_id`

- raw user identifiers,

- raw tenant identifiers,

- arbitrary backend payloads.

These belong in:

- traces,

- logs,

- structured events,

- QFS artifacts.

### Allowed bounded labels

Examples:

| **Label** | **Bound Type** |
|---|---|
| `backend` | finite configured set |
| `mode` | finite enum |
| `reason` | stable taxonomy |
| `stage` | finite pipeline stages |
| `resource` | finite enum |

---

## 6. Exporter Requirements

All benchmark exporters MUST:

1. expose valid Prometheus text exposition,

2. include `# TYPE` declarations,

3. export contract marker metric,

4. guarantee snapshot consistency,

5. tolerate partial subsystem failures,

6. avoid blocking benchmark runtime critical paths.

Exporters MUST NOT:

- panic on scrape,

- emit unbounded labels,

- expose partial malformed histogram families,

- mutate metric semantics dynamically.

---

## 7. Alert Compatibility Contract

Prometheus alert rules are maintained in:

```text
monitoring/metrics/prometheus/benchmark-alerts.yaml
```

### Required critical alerts

#### Queue stall detection

Triggers when:

- queue age exceeds SLO,

- dispatch throughput drops,

- or scheduler starvation detected.

#### Ingestion failure surge

Triggers when:

- ingestion failures exceed configured error budget.

#### Benchmark failure-rate breach

Triggers when:

- failure ratio exceeds runtime SLO.

#### Stalled execution detection

Triggers when:

- stalled runs exceed threshold.

#### Replay divergence detection

Triggers when:

- replay mismatch count increases.

---

## 8. Dashboard Compatibility Contract

Grafana dashboard:

```text
monitoring/dashboards/benchmark_dashboard.json
```

Dashboard MUST include:

- queue depth,

- queue age,

- scheduler latency,

- benchmark throughput,

- success/failure ratio,

- runtime duration percentiles,

- ingestion failures,

- stalled executions,

- replay mismatches,

- contract marker visibility.

---

## 9. Runtime Integration Requirements

At least one runtime environment MUST expose all benchmark metrics end-to-end.

Supported deployment models:

- standalone runtime,

- orchestration runtime,

- distributed cluster runtime,

- CI replay runtime.

Metrics MUST survive:

- runtime restarts,

- rolling deployments,

- exporter refreshes,

- scheduler topology changes.

---

## 10. CI & Conformance Requirements

CI MUST validate:

1. required metric family presence,

2. valid metric types,

3. contract marker version,

4. histogram integrity,

5. alert query compatibility,

6. dashboard query compatibility,

7. bounded-label enforcement.

Required conformance tests:

- scrape validation,

- exporter snapshot validation,

- alert expression validation,

- dashboard metric existence validation.

---

## 11. Operational Invariants

The following invariants are mandatory.

#### Deterministic semantics

The same runtime condition MUST map to the same metric semantics.

#### Monotonic counters

Counter metrics MUST NEVER decrease.

#### Stable histograms

Histogram bucket boundaries MUST remain backward-compatible within the same MAJOR version.

#### Bounded cardinality

No runtime condition may generate unbounded metric series.

#### Export safety

Telemetry failures MUST NOT terminate benchmark execution runtime.

---

## 12. Migration Rules

#### Additive migration

New metrics MAY be added in MINOR releases.

#### Deprecation policy

Metrics MUST remain supported for at least one MINOR release after deprecation.

Deprecated metrics MUST:

- remain documented,

- emit compatibility telemetry,

- include migration guidance.

#### Breaking migration

Breaking changes require:

- MAJOR version bump,

- dashboard updates,

- alert updates,

- exporter updates,

- migration documentation.

---

## 13. Minimum Closure Criteria

The benchmark observability contract is considered fully realized only when:

1. all required metrics are exported in live runtime environments,

2. contract marker metric is emitted,

3. dashboards validate against live scrape output,

4. alert rules validate against live scrape output,

5. CI gates enforce contract completeness,

6. replay/runtime telemetry is fully wired end-to-end,

7. benchmark ingestion/export pipelines expose full observability coverage.

---

## 14. Compatibility Guarantees

Eigen OS guarantees:

- stable metric names within MAJOR versions,

- deterministic metric semantics,

- bounded label behavior,

- backward-compatible MINOR additions,

- SemVer-governed observability evolution.

These guarantees apply to:

- operators,

- dashboards,

- SRE automation,

- alerting systems,

- SDK telemetry integrations,

- enterprise monitoring integrations.
