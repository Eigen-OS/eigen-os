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
- tracing integration,
- structured logging expectations,
- and operational invariants.

This contract is part of the stable public observability surface of Eigen OS 1.0.

---

## 1. Contract Marker

All benchmark telemetry exporters MUST expose: `eigen_bench_contract_info{version="1.0.0"} 1`

This metric is mandatory and serves as the runtime compatibility marker for dashboards, alerting systems, CI validation, and observability tooling.

---

### 1.1 SemVer Policy

#### MAJOR

Breaking changes:

- metric rename,
- metric removal,
- semantic/type changes,
- incompatible label changes,
- histogram bucket incompatibility.

#### MINOR

Backward-compatible additions:

- additive metrics,
- additive labels,
- new histogram buckets,
- new optional telemetry dimensions,
- new structured events.

#### PATCH

Non-semantic corrections:

- exporter fixes,
- documentation clarifications,
- alert tuning,
- dashboard corrections,
- typo fixes.

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
- benchmark orchestration health,
- checkpoint/restore execution,
- benchmark cancellation,
- benchmark retries,

Benchmark telemetry MUST be emitted under an isolated benchmark scope. It MUST NOT reuse production job trace parents or unbounded production trace labels, and it MUST preserve artifact references separately from general runtime/job traces.

The contract applies to:

- standalone benchmark runtime,
- distributed benchmark execution,
- CI benchmark environments,
- replay environments,
- production observability deployments,
- staging and canary environments.

---

## 3. Source of Truth

The following repository artifacts are normative:

```text
monitoring/metrics/prometheus/exporter.py
monitoring/metrics/prometheus/benchmark-alerts.yaml
monitoring/dashboards/benchmark_dashboard.json
monitoring/metrics/tests/test_stage_observability.py
docs/howto/benchmark-observability-runbook.md
```

Architecture references:

```text
docs/architecture/components/observability.md
docs/architecture/runtime/benchmark-runtime.md
docs/architecture/contracts/telemetry.md
```

If implementation and documentation diverge:

- exporter behavior,
- CI conformance tests,
- Prometheus exposition output

take precedence over prose documentation.

---

## 4. Telemetry Architecture Requirements

Benchmark observability MUST support:

- Prometheus metrics,
- distributed tracing,
- structured logs,
- correlation propagation,
- replay diagnostics,
- deterministic runtime auditability.

Telemetry MUST remain operational during:

- partial subsystem failures,
- backend degradation,
- scheduler failover,
- exporter restarts,
- rolling deployments.

Observability MUST NOT become a hard dependency for benchmark execution progress.

---

## 5. Required Metrics

All metrics listed below are mandatory.

### 5.1 Queue Health

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
- MUST update consistently with enqueue/dequeue operations.

#### Oldest queued benchmark age

```text
eigen_bench_queue_oldest_age_seconds
```

Type:

- gauge

Definition:

- age in seconds of the oldest queued benchmark awaiting scheduling.

Purpose:

- starvation detection,
- scheduler degradation detection,
- stuck queue detection.

#### Queue throughput

```text
eigen_bench_queue_dispatch_total
```

Type:

- `counter`

Labels:

- `result`

Allowed values:

- `scheduled`
- `rejected`
- `delayed`

Definition:

- total benchmark dispatch decisions emitted by the scheduler.

Counters MUST remain monotonic.

---

### 5.2 Benchmark Execution Lifecycle

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

total benchmark runtime duration from execution start until terminal completion.

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

Bucket boundaries MUST remain stable within MAJOR version `1.x`.

#### Successful benchmark executions

```text
eigen_bench_runs_succeeded_total
```

Type:

- counter

Labels:

- backend
- mode

Definition:

- benchmark executions completing successfully.

#### Failed benchmark executions

```text
eigen_bench_runs_failed_total
```

Type:

- counter

Labels:

- `backend`
- `reason`

Allowed `reason` examples:

- `timeout`
- `backend_unavailable`
- `validation_failed`
- `quota_exceeded`
- `internal`
- `cancelled`
- `panic`
- `artifact_corruption`
- `scheduler_failure`

Definition:

- benchmark executions ending in terminal failure state.

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

- benchmarks currently executing.

Invariant:

- MUST NOT become negative.

---

### 5.3 Ingestion & Artifact Pipeline

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

- benchmark artifacts rejected due to schema, checksum, or contract violations.

#### Artifact persistence failures

```text
eigen_bench_artifact_persist_failures_total
```

Type:

- counter

Definition:

- durable storage failures during benchmark artifact persistence.

---

### 5.4 Reliability & Runtime Safety

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
- orchestration continuity lost,
- checkpoint progress halted.

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

#### Runtime restart count

```text
eigen_bench_runtime_restarts_total
```

Type:

- counter

Definition:

- benchmark runtime process restarts.

### 5.5 Scheduler & Resource Pressure

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

Definition:

- resource exhaustion events affecting benchmark execution.

#### Scheduler retry count

```text
eigen_bench_scheduler_retries_total
```

Type:

- counter

Definition:

- scheduler retries triggered due to transient execution failures.

---

## 6. Label Contract

Label cardinality MUST remain bounded and deterministic.

### 6.1 Forbidden Labels

The following MUST NOT be used directly as metric labels:

- `job_id`
- `trace_id`
- `request_id`
- `correlation_id`
- raw user identifiers
- raw tenant identifiers
- raw AQO hashes
- arbitrary backend payloads
- freeform metadata

These belong in:

- traces,
- logs,
- structured events,
- QFS artifacts.

---

### 6.2 Allowed Bounded Labels

| **Label** | **Bound Type** |
|----------|----------|
| `backend` | finite configured set |
| `mode` | finite enum |
| `reason` | stable taxonomy |
| `stage` | finite pipeline stages |
| `resource` | finite enum |

---

### 6.3 Label Stability

Existing labels:

- MUST NOT change semantic meaning,
- MUST NOT change type,
- MUST NOT become unbounded within MAJOR version `1.x`.

---

## 7. Tracing Contract

Benchmark runtimes MUST support distributed tracing.

Required propagation:

- W3C `traceparent`
- W3C `tracestate`

Minimum trace spans:

| **Span Name** | **Description** |
|----------|----------|
| `benchmark.enqueue` | benchmark submission |
| `benchmark.schedule` | scheduling decision |
| `benchmark.execute` | benchmark execution |
| `benchmark.persist` | artifact persistence |
| `benchmark.replay` | replay validation |
| `benchmark.ingest` | ingestion pipeline |

Required trace attributes:

- `benchmark.run_id`
- `benchmark.backend`
- `benchmark.mode`
- `benchmark.contract_version`
- `benchmark.scheduler`
- `benchmark.result_state`

Trace correlation MUST remain stable across retries and distributed execution hops.

---

## 8. Structured Logging Contract

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
| `run_id` | benchmark run identifier |
| `trace_id` | distributed trace identifier |
| `event` | deterministic event name |

Sensitive data MUST NOT be logged.

AQO payloads MUST NOT be fully logged by default.

---

## 9. Exporter Requirements

All benchmark exporters MUST:

1. expose valid Prometheus text exposition,
2. include `# TYPE` declarations,
3. export contract marker metric,
4. guarantee snapshot consistency,
5. tolerate partial subsystem failures,
6. avoid blocking benchmark runtime critical paths,
7. avoid high-cardinality metric explosions.

Exporters MUST NOT:

- panic on scrape,
- emit unbounded labels,
- expose malformed histogram families,
- mutate metric semantics dynamically,
- emit duplicate TYPE declarations.

---

## 10. Alert Compatibility Contract

Prometheus alert rules are maintained in: `monitoring/metrics/prometheus/benchmark-alerts.yaml`

---

### 10.1 Required Critical Alerts

#### Queue stall detection

Triggers when:

- queue age exceeds SLO,
- dispatch throughput drops,
- scheduler starvation detected.

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

#### Exporter health degradation

Triggers when:

- exporter scrape failures occur,
- contract marker disappears,
- telemetry freshness exceeds threshold.

---

## 11. Dashboard Compatibility Contract

Grafana dashboard: `monitoring/dashboards/benchmark_dashboard.json`

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
- exporter health,
- contract marker visibility.

Dashboards MUST remain backward-compatible within MAJOR version `1.x`.

---

## 12. Runtime Integration Requirements

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
- scheduler topology changes,
- backend failover events.

Telemetry pipelines SHOULD support graceful degradation under overload.

---

## 13. CI & Conformance Requirements

CI MUST validate:

1. required metric family presence,
2. valid metric types,
3. contract marker version,
4. histogram integrity,
5. alert query compatibility,
6. dashboard query compatibility,
7. bounded-label enforcement,
8. exporter scrape validity,
9. trace propagation compatibility.

Required conformance tests:

- scrape validation,
- exporter snapshot validation,
- alert expression validation,
- dashboard metric existence validation,
- histogram bucket validation,
- label cardinality validation.

CI failures MUST block incompatible observability changes.

---

## 14. Operational Invariants

The following invariants are mandatory.

#### Deterministic semantics

The same runtime condition MUST map to the same metric semantics.

### Monotonic counters

Counter metrics MUST NEVER decrease.

### Stable histograms

Histogram bucket boundaries MUST remain backward-compatible within the same MAJOR version.

### Bounded cardinality

No runtime condition may generate unbounded metric series.

### Export safety

Telemetry failures MUST NOT terminate benchmark execution runtime.

### Replay determinism

Replay telemetry MUST remain deterministic across identical replay executions.

---

## 15. Security & Isolation

Observability systems MUST:

- isolate tenant telemetry,
- prevent unauthorized metric exposure,
- prevent trace leakage across tenants,
- sanitize structured logs,
- redact sensitive metadata.

Observability exporters MUST support:

- TLS transport,
- authenticated scraping where required,
- RBAC-compatible dashboard access.

---

## 16. Migration Rules

### Additive migration

New metrics MAY be added in MINOR releases.

### Deprecation policy

Metrics MUST remain supported for at least one MINOR release after deprecation.

Deprecated metrics MUST:

- remain documented,
- emit compatibility telemetry,
- include migration guidance.

### Breaking migration

Breaking changes require:

- MAJOR version bump,
- dashboard updates,
- alert updates,
- exporter updates,
- migration documentation,
- CI compatibility updates.

---

## 17. Compatibility Guarantees

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
- enterprise monitoring integrations,
- replay tooling,
- distributed runtime orchestration systems.

---

## Appendix A. Diagrams

### A.1 Telemetry Architecture Requirements

![Telemetry Architecture Requirements](https://i.imgur.com/Vccyldh.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Runtime
    SCH[Benchmark Scheduler]
    RUN[Benchmark Runtime]
    ING[Ingestion Pipeline]
    REP[Replay Validator]
    QFS[(QFS / CircuitFS)]
  end

  subgraph Telemetry
    EXP[Prometheus Exporter\n/metrics]
    OTEL[OpenTelemetry SDK]
    LOG[Structured Logs]
  end

  subgraph Backends
    SIM[Simulators]
    HW[Quantum Hardware]
  end

  subgraph ObservabilityStack
    PROM[Prometheus]
    GRAF[Grafana]
    LOKI[Loki/ES]
    JAEG[Jaeger/Tempo]
    AM[Alertmanager]
  end

  SCH --> RUN
  RUN --> SIM
  RUN --> HW

  RUN --> QFS
  ING --> QFS
  REP --> QFS

  SCH --> OTEL
  RUN --> OTEL
  ING --> OTEL
  REP --> OTEL

  SCH --> LOG
  RUN --> LOG
  ING --> LOG
  REP --> LOG

  EXP --> PROM
  OTEL --> JAEG
  LOG --> LOKI
  PROM --> GRAF
  PROM --> AM

  note1{{Telemetry MUST NOT be a hard dependency\nfor execution progress}}
  EXP --- note1
```

</details>

---

### A.2 Required Metrics

![Required Metrics](https://i.imgur.com/rH2XSvq.png)

<details>
<summary>code</summary>

```text
flowchart LR
  Q[Queue Health] --> Q1[eigen_bench_queue_depth]
  Q --> Q2[eigen_bench_queue_oldest_age_seconds]
  Q --> Q3["eigen_bench_queue_dispatch_total{result}"]

  L[Execution Lifecycle] --> L1[eigen_bench_run_duration_seconds_bucket]
  L --> L2["eigen_bench_runs_succeeded_total{backend,mode}"]
  L --> L3["eigen_bench_runs_failed_total{backend,reason}"]
  L --> L4[eigen_bench_runs_cancelled_total]
  L --> L5[eigen_bench_active_runs]

  I[Ingestion & Artifacts] --> I1["eigen_bench_ingestion_failures_total{stage,reason}"]
  I --> I2[eigen_bench_artifact_persist_latency_seconds_bucket]
  I --> I3[eigen_bench_artifact_validation_failures_total]
  I --> I4[eigen_bench_artifact_persist_failures_total]

  R[Reliability & Safety] --> R1[eigen_bench_stalled_runs]
  R --> R2[eigen_bench_replay_mismatch_total]
  R --> R3[eigen_bench_runtime_panics_total]
  R --> R4[eigen_bench_runtime_restarts_total]

  S[Scheduler & Resource Pressure] --> S1[eigen_bench_scheduler_latency_seconds_bucket]
  S --> S2["eigen_bench_resource_exhausted_total{resource}"]
  S --> S3[eigen_bench_scheduler_retries_total]
```

</details>

---

### A.3 Queue Health

![Queue Health](https://i.imgur.com/XVjzm76.png)

<details>
<summary>code</summary>

```text
stateDiagram-v2
  [*] --> Enqueued: enqueue
  Enqueued --> Scheduled: dispatch result=scheduled
  Enqueued --> Rejected: dispatch result=rejected
  Enqueued --> Delayed: dispatch result=delayed
  Delayed --> Scheduled: later scheduled
  Delayed --> Rejected: later rejected

  note right of Enqueued
    eigen_bench_queue_depth tracks count of Enqueued + Delayed (queued)
    eigen_bench_queue_oldest_age_seconds tracks max age among queued items
  end note
```

</details>

---

### A.4 Benchmark Execution Lifecycle

![Benchmark Execution Lifecycle](https://i.imgur.com/um8n3tb.png)

<details>
<summary>code</summary>

```text
flowchart LR
  P[PENDING/QUEUED] --> ST[START]
  ST --> EX[EXECUTING]
  EX -->|success| OK[DONE]
  EX -->|failure| ER[ERROR]
  EX -->|cancel| CA[CANCELLED]

  subgraph Metrics
    D["eigen_bench_run_duration_seconds (hist: start->terminal)"]
    A["eigen_bench_active_runs (gauge)"]
    S[eigen_bench_runs_succeeded_total]
    F["eigen_bench_runs_failed_total{reason}"]
    C[eigen_bench_runs_cancelled_total]
  end

  ST --- A
  EX --- A
  ST --- D
  OK --- S
  ER --- F
  CA --- C
```

</details>

---

### A.5 Label Contract

![Label Contract](https://i.imgur.com/YSrSNv5.png)

<details>
<summary>code</summary>

```text
flowchart TB
  M[Metric emission] --> L{Label candidate}
  L -->|bounded enum / finite configured set| OK[Allowed label]
  L -->|correlation id / unbounded string| NO[FORBIDDEN as label]
  NO --> ALT[Put into traces/logs/events/QFS artifacts]

  subgraph Forbidden Examples
    F1[job_id]
    F2[trace_id]
    F3[request_id]
    F4[correlation_id]
    F5[raw tenant/user ids]
    F6[raw AQO hashes]
  end

  NO --- F1
  NO --- F2
  NO --- F3
  NO --- F4
  NO --- F5
  NO --- F6
```

</details>

---

### A.6 Tracing Contract

![Tracing Contract](https://i.imgur.com/ytsEJbH.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant CLI as Client/CI
  participant SCH as Scheduler
  participant RUN as Runtime
  participant QFS as QFS
  participant ING as Ingestion
  participant REP as Replay

  CLI->>SCH: benchmark.enqueue (traceparent propagated)
  SCH->>RUN: benchmark.schedule (decision + placement)
  RUN->>RUN: benchmark.execute (runtime spans)
  RUN->>QFS: benchmark.persist (artifacts)
  RUN->>ING: benchmark.ingest (telemetry/artifacts)
  ING->>REP: benchmark.replay (optional)
  REP-->>ING: replay verdict

  Note over CLI,REP: Required attributes (bounded):run_id, backend, mode, contract_version, result_state
```

</details>

---

### A.7 Exporter Requirements

![Exporter Requirements](https://i.imgur.com/2DBzQdb.png)

<details>
<summary>code</summary>

```text
flowchart LR
  RT[Benchmark runtime hot path] -->|updates| REG[In-process metrics registry]
  SCRAPE[Prometheus scrape] --> EXP[Exporter /metrics endpoint]
  EXP --> REG
  EXP --> OUT[Text exposition snapshot]

  OUT -->|success| PROM[Prometheus]
  OUT -->|failure| ERR[Scrape error]

  note1{{Exporter MUST NOT block runtime progress; napshot consistency required; No panics on scrape}}
  EXP --- note1
```

</details>

---

### A.8 Alert Compatibility Contract

![Alert Compatibility Contract](https://i.imgur.com/TS5PPYk.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Signals
    QD[eigen_bench_queue_depth]
    QA[eigen_bench_queue_oldest_age_seconds]
    SL[eigen_bench_scheduler_latency_seconds]
    FR[eigen_bench_runs_failed_total / succeeded_total]
    ING[eigen_bench_ingestion_failures_total]
    ST[eigen_bench_stalled_runs]
    RP[eigen_bench_replay_mismatch_total]
    EH[eigen_bench_runtime_restarts_total + exporter freshness]
  end

  subgraph Alerts
    A1[Queue stall]
    A2[Scheduler degradation]
    A3[Failure-rate breach]
    A4[Ingestion surge]
    A5[Stalled execution]
    A6[Replay divergence]
    A7[Exporter health]
  end

  QD --> A1
  QA --> A1
  SL --> A2
  FR --> A3
  ING --> A4
  ST --> A5
  RP --> A6
  EH --> A7
```

</details>

---

### A.9 CI & Conformance Requirements

![CI & Conformance Requirements](https://i.imgur.com/LgGSP0Y.png)

<details>
<summary>code</summary>

```text
flowchart LR
  PR[Change set] --> CI[CI pipeline]
  CI --> T1["Scrape validation (text format + TYPE)"]
  CI --> T2[Metric family presence]
  CI --> T3["Type validation (counter/gauge/hist)"]
  CI --> T4["Histogram bucket validation (stable boundaries)"]
  CI --> T5[Alert query validation]
  CI --> T6[Dashboard query validation]
  CI --> T7[Label boundedness checks]
  CI --> T8[Trace propagation smoke test]
  T1 --> PASS{All pass?}
  T2 --> PASS
  T3 --> PASS
  T4 --> PASS
  T5 --> PASS
  T6 --> PASS
  T7 --> PASS
  T8 --> PASS
  PASS -->|yes| MERGE[Merge allowed]
  PASS -->|no| BLOCK[Block incompatible change]
```

</details>
