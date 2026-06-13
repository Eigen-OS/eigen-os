# Intelligent Runtime Observability Contract

**Document status:** Stable
**Subsystem:** Intelligent Runtime, Scheduler, Policy Engine, Explainability Layer, Adaptive Routing, Driver Manager
**Contract class:** Public SRE / Operations contract
**Contract version:** `2.1.0`
**Applies to:** Eigen OS 1.0

This document defines the normative observability contract for the Eigen OS intelligent runtime subsystem.

The contract standardizes:

- runtime decision telemetry,
- backend-selection observability,
- adaptive scheduling visibility,
- policy execution telemetry,
- explainability endpoint instrumentation,
- runtime degradation visibility,
- fallback routing observability,
- distributed runtime decision propagation,
- operator-facing SLO signals,
- alert compatibility,
- dashboard compatibility,
- Prometheus/OpenTelemetry interoperability,
- and CI conformance requirements.

All metrics defined in this document are part of the stable public observability surface of Eigen OS 1.0.

---

# 1. Contract Marker

All intelligent-runtime exporters MUST expose:

```text
eigen_runtime_contract_info{version="2.1.0"} 1
```

For Kernel/QRTX and Resource Manager conformance, the same scrape surface MAY also expose bounded companion markers for orchestration, cluster, and multi-device surfaces.

The contract marker metric:

- MUST be exported on every scrape,
- MUST remain stable within a MAJOR version,
- MUST be visible in dashboards,
- MUST be validated by CI,
- MUST be included in exporter conformance tests.

---

# 2. SemVer Policy

## MAJOR

Breaking changes:

- metric renames,
- metric removals,
- incompatible semantic changes,
- incompatible label changes,
- histogram semantic changes,
- explainability taxonomy changes,
- incompatible runtime-decision taxonomy changes.

## MINOR

Backward-compatible additions:

- additive metrics,
- additive labels,
- additive histogram buckets,
- new explainability levels,
- new runtime telemetry dimensions,
- additive policy/fallback reasons.

## PATCH

Non-semantic corrections:

- documentation fixes,
- exporter implementation fixes,
- alert tuning,
- dashboard corrections,
- metadata clarifications.

---

# 3. Scope

This contract governs observability for:

- intelligent backend selection,
- adaptive scheduling,
- runtime scoring,
- routing optimization,
- policy evaluation,
- explainability APIs,
- runtime heuristics,
- execution optimization loops,
- runtime degradation handling,
- fallback routing,
- distributed decision propagation,
- runtime state reconciliation,
- backend ejection logic,
- emergency policy overrides,
- operator-directed runtime controls.

The contract applies to:

- standalone runtime deployments,
- distributed runtime clusters,
- hybrid execution environments,
- autoscaled execution pools,
- replay/recovery environments,
- multi-provider orchestration environments.

---

# 4. Source of Truth

The following repository artifacts are normative:

- `monitoring/metrics/prometheus/exporter.py`
- `monitoring/metrics/prometheus/intelligent-runtime-alerts.yaml`
- `monitoring/dashboards/intelligent_runtime_dashboard.json`
- `monitoring/metrics/tests/test_intelligent_runtime_observability.py`
- `docs/howto/intelligent-runtime-observability-runbook.md`
- `docs/reference/intelligent-runtime-observability-contract.md`

---

# 5. Observability Design Principles

## 5.1 Deterministic Decision Visibility

Every runtime scheduling or backend-selection decision MUST produce observable telemetry.

## 5.2 Explainability Consistency

Explainability telemetry MUST remain semantically aligned with runtime decision behavior.

## 5.3 Stable Metric Semantics

Metric meanings MUST remain stable within the same MAJOR version.

## 5.4 Bounded Cardinality

All labels MUST remain bounded, enumerable, deterministic, and operator-safe.

## 5.5 Runtime Transparency

Fallbacks, degraded execution, policy overrides, backend ejections, and emergency routing MUST remain observable.

## 5.6 Distributed Trace Continuity

Runtime decisions MUST remain trace-correlatable across:

- scheduler,
- policy engine,
- dispatcher,
- runtime workers,
- explainability layer,
- artifact systems,
- replay/recovery systems.

Trace continuity evidence SHOULD include stable `trace_id`, `request_id` (where applicable), `job_id`, `stage`, and `attempt` fields in logs or durable artifacts. These fields MUST NOT be introduced as unbounded metric labels.

---

# 6. Required Metrics

All metric families defined below are mandatory.

---

# 6.1 Runtime Decision Metrics

## Decision Throughput

```text
eigen_runtime_decisions_total
```

Type:

- counter

Labels:

- `policy_mode`
- `result`

Allowed `policy_mode` values:

```text
balanced
latency_optimized
cost_optimized
availability_optimized
deterministic
compliance
emergency
manual_override
```

Allowed `result` values:

```text
success
fallback
degraded
rejected
failed
```

Where replay or recovery flows are exported, they SHOULD use bounded result families such as `replayed`, `recovered`, or `conflict`, and MUST remain stable within the contract major version.

Definition:

- total runtime scheduling/backend-selection decisions.

---

## Runtime Decision Latency

```text
eigen_runtime_decision_latency_ms
```

Type:

- histogram

Required exports:

```text
_bucket
_sum
_count
```

Definition:

- total latency for runtime decision resolution.

Includes:

- policy evaluation,
- backend scoring,
- routing resolution,
- fallback selection,
- explain snapshot generation.

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

---

## Runtime Decision Failures

```text
eigen_runtime_decision_failures_total
```

Type:

- counter

Labels:

- `reason`

Allowed `reason` values:

```text
policy_failure
backend_unavailable
scoring_failure
capacity_exhausted
compliance_violation
timeout
internal_error
explain_generation_failure
```

Definition:

- failed runtime decision attempts.

Fallback routing telemetry MUST include bounded, deterministic metadata for:

- fallback_reason
- fallback_reason_code
- model_version where a concrete model selection exists

These fields MUST remain stable within the same MAJOR contract version and MUST NOT be promoted into unbounded metric labels.

---

# 6.2 Backend Scoring Metrics

## Scoring Requests

```text
eigen_runtime_scoring_requests_total
```

Type:

- counter

Definition:

- total backend-scoring requests.

---

## Scoring Latency

```text
eigen_runtime_scoring_latency_ms
```

Type:

- histogram

Required exports:

```text
_bucket
_sum
_count
```

Definition:

- backend scoring execution latency.

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
+Inf
```

---

## Scoring Failures

```text
eigen_runtime_scoring_failures_total
```

Type:

- counter

Labels:

- `reason`

Allowed `reason` values:

```text
missing_backend_state
invalid_score_model
feature_extraction_failure
timeout
resource_exhausted
internal_error
```

Definition:

- failed backend-scoring attempts.

---

## Backend Score Distribution

```text
eigen_runtime_backend_score
```

Type:

- gauge

Labels:

- `backend`
- `policy_mode`

Definition:

- normalized backend score emitted during latest evaluation cycle.

---

## 6.3.1 Optimization Candidate Evidence Metrics

Wave 7a optimizer evidence MUST remain bounded and trace-correlated across the Kernel/QRTX → optimizer → downstream handoff path. The following metrics are part of the intelligent-runtime contract surface:

### Optimization Candidate Traces

```text
eigen_runtime_optimizer_candidate_traces_total
```

Type:

- counter

Labels:

- `objective`
- `result`

Allowed `objective` values:

```text
balanced
latency_optimized
cost_optimized
availability_optimized
deterministic
compliance
emergency
manual_override
```

Allowed `result` values:

```text
selected
fallback
```

Definition:

- bounded candidate trace evidence for optimizer selections and deterministic fallbacks.

---

### Optimization Fallback Reasons

```text
eigen_runtime_optimizer_fallbacks_total
```

Type:

- counter

Labels:

- `reason`

Allowed `reason` values:

```text
backend_unavailable
confidence_too_low
model_unavailable
timeout
internal_error
policy_rejected
other
```

Definition:

- bounded fallback evidence emitted when the optimizer cannot promote a candidate.

---

### Optimizer Confidence

```text
eigen_runtime_optimizer_last_confidence_score
```

Type:

- gauge

Definition:

- latest bounded optimizer confidence score used for operator visibility and thresholding.

---

### Optimizer Trace Handoff Continuity

```text
eigen_runtime_optimizer_trace_handoff_total
```

Type:

- counter

Labels:

- `handoff`

Allowed `handoff` values:

```text
kernel_to_optimizer
optimizer_to_downstream
```

Definition:

- trace continuity evidence for handoff continuity across the Wave 7a optimizer path.

---

# 6.3 Policy Execution Metrics

## Policy Branch Traversal

```text
eigen_runtime_policy_branch_total
```

Type:

- counter

Labels:

- `policy_mode`
- `branch`

Allowed `branch` values:

```text
primary
fallback
emergency
compliance_override
cost_guardrail
latency_guardrail
availability_guardrail
manual_override
```

Definition:

- policy branch traversal events.

---

## Policy Evaluation Latency

```text
eigen_runtime_policy_eval_latency_ms
```

Type:

- histogram

Required exports:

```text
_bucket
_sum
_count
```

Definition:

- latency for policy evaluation execution.

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
+Inf
```

---

## Policy Evaluation Failures

```text
eigen_runtime_policy_failures_total
```

Type:

- counter

Labels:

- `reason`

Allowed `reason` values:

```text
rule_parse_error
invalid_context
missing_input
timeout
policy_conflict
internal_error
```

Definition:

- failed policy evaluation executions.

---

# 6.4 Fallback & Degradation Metrics

## Runtime Fallback Events

```text
eigen_runtime_fallback_total
```

Type:

- counter

Labels:

- `reason`

Allowed `reason` values:

```text
backend_unavailable
quota_exceeded
latency_slo_breach
capacity_shortage
policy_failure
network_partition
compliance_requirement
manual_override
```

Definition:

- fallback-routing activations.

---

## Degraded Routing Activation

```text
eigen_runtime_degraded_mode_total
```

Type:

- counter

Labels:

- `mode`

Allowed `mode` values:

```text
reduced_scoring
safe_routing
single_backend_mode
cached_decisions
explain_disabled
```

Definition:

- degraded runtime-mode activations.

---

## Backend Ejection Events

```text
eigen_runtime_backend_ejections_total
```

Type:

- counter

Labels:

- `backend`
- `reason`

Allowed `reason` examples:

```text
health_failure
latency_slo_breach
quota_exhausted
partition_detected
policy_violation
manual_override
```

Definition:

- backend removal/ejection events from scheduling eligibility.

---

# 6.5 Explainability Metrics

## Explain Requests

```text
eigen_runtime_explain_requests_total
```

Type:

- counter

Labels:

- `endpoint`
- `level`

Allowed `level` values:

```text
L1_USER
L2_OPERATOR
L3_FORENSIC
```

Numeric explainability encodings are prohibited beginning with contract `2.1.0`.

Definition:

- explainability API requests.

---

## Explain Latency

```text
eigen_runtime_explain_latency_ms
```

Type:

- histogram

Labels:

- `endpoint`
- `level`

Required exports:

```text
_bucket
_sum
_count
```

Definition:

- explainability request latency.

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

---

## Explain Errors

```text
eigen_runtime_explain_errors_total
```

Type:

- counter

Labels:

- `endpoint`
- `error_code`

Definition:

- explainability API failures.

---

## Explain Payload Size

```text
eigen_runtime_explain_payload_bytes
```

Type:

- histogram

Required exports:

```text
_bucket
_sum
_count
```

Definition:

- explainability payload size.

Required buckets:

```text
256
512
1024
4096
16384
65536
262144
1048576
+Inf
```

---

# 6.6 Runtime Adaptation Metrics

## Adaptive Reconfiguration Events

```text
eigen_runtime_reconfigurations_total
```

Type:

- counter

Labels:

- `reason`

Definition:

- runtime adaptive reconfiguration events.

---

## Runtime Model Refreshes

```text
eigen_runtime_model_refresh_total
```

Type:

- counter

Labels:

- `model`

Definition:

- scoring/runtime-model refresh events.

---

## Runtime State Divergence

```text
eigen_runtime_state_divergence_total
```

Type:

- counter

Labels:

- `component`

Definition:

- runtime state inconsistencies across replicated decision components.

---

# 6.7 Reliability Metrics

## Runtime Internal Errors

```text
eigen_runtime_internal_errors_total
```

Type:

- counter

Labels:

- `component`

Definition:

- internal runtime invariant failures.

---

## Runtime Trace Breakage

```text
eigen_runtime_trace_breakage_total
```

Type:

- counter

Labels:

- `stage`

Allowed `stage` examples:

```text
scheduler
policy_engine
dispatcher
worker
explainability
artifact_store
merge
```

Definition:

- distributed trace continuity interruptions.

---

# 7. Label Contract

Label cardinality MUST remain bounded and deterministic.

## 7.1 Forbidden Labels

The following MUST NOT be used as metric labels:

- `job_id`
- `trace_id`
- `tenant_id`
- `user_id`
- arbitrary backend payloads
- freeform error messages
- dynamic policy expressions
- request identifiers
- correlation identifiers
- arbitrary resource identifiers

These belong in:

- traces,
- structured logs,
- QFS artifacts,
- audit streams.

---

## 7.2 Allowed Bounded Labels

Examples:

| Label | Bound Type |
|---|---|
| `policy_mode` | stable runtime enum |
| `reason` | stable enum taxonomy |
| `branch` | finite policy branches |
| `backend` | configured backend set |
| `component` | finite runtime components |
| `level` | finite explainability levels |

---

# 8. Histogram Requirements

The following metrics MUST use Prometheus histograms:

- runtime decision latency,
- scoring latency,
- explain latency,
- explain payload size,
- policy evaluation latency.

Histogram families MUST:

- export `_bucket`, `_sum`, `_count`,
- maintain monotonic bucket ordering,
- preserve bucket compatibility within the same MAJOR version,
- remain scrape-compatible with Prometheus.

---

# 9. Exporter Requirements

Runtime exporters MUST:

1. expose valid Prometheus text exposition,
2. export all required metric families,
3. emit `# TYPE` declarations,
4. expose the contract marker metric,
5. preserve snapshot consistency,
6. support concurrent scraping,
7. tolerate partial subsystem failures,
8. avoid blocking runtime execution paths,
9. preserve metric semantic stability.

Runtime exporters MUST NOT:

- panic during scrape,
- emit malformed histogram families,
- expose unbounded labels,
- dynamically mutate metric semantics,
- expose raw provider payloads.

---

# 10. OpenTelemetry Compatibility

If OpenTelemetry exporters are enabled:

- metric names MUST preserve semantic compatibility,
- histogram semantics MUST remain equivalent,
- trace correlation MUST remain stable,
- runtime decision spans MUST preserve causal lineage.

Distributed runtime traces SHOULD remain correlatable across:

- scheduler,
- policy engine,
- dispatcher,
- worker execution,
- explainability APIs,
- artifact storage,
- replay systems.

---

# 11. Alert Compatibility Contract

Prometheus alert rules are maintained in:

```text
monitoring/metrics/prometheus/intelligent-runtime-alerts.yaml
```

---

## 11.1 Critical Alerts

### Runtime Decision Failure Spike

Triggers on abnormal increase in runtime decision failures.

### Scoring Latency SLO Breach

Triggers when scoring latency exceeds configured SLO thresholds.

### Explain Endpoint Error Rate Breach

Triggers on explainability endpoint reliability degradation.

### Fallback Surge

Triggers when fallback-routing frequency exceeds expected baseline.

### Trace Continuity Breakage

Triggers on distributed trace fragmentation.

### Runtime Divergence Detection

Triggers on replicated runtime-state inconsistencies.

---

## 11.2 Warning Alerts

### Backend Ejection Increase

Triggers when backend ejection frequency rises above baseline.

### Degraded Mode Activation

Triggers when degraded routing modes become active.

### Policy Failure Increase

Triggers when policy-evaluation failures increase abnormally.

---

# 12. Dashboard Compatibility Contract

Grafana dashboard:

```text
monitoring/dashboards/intelligent_runtime_dashboard.json
```

Dashboard MUST include:

- decision throughput,
- decision latency percentiles,
- scoring latency,
- fallback rates,
- backend ejections,
- explain endpoint health,
- policy branch distribution,
- degraded mode activation,
- optimizer candidate traces,
- optimizer fallback rates,
- optimizer confidence,
- runtime divergence,
- trace continuity,
- contract marker visibility.

---

# 13. Explainability SLO Requirements

## L1_USER

### Availability Target

```text
99.9%
```

### P95 Latency Target

```text
< 250ms
```

---

## L2_OPERATOR

### Availability Target

```text
99.5%
```

### P95 Latency Target

```text
< 1000ms
```

---

## L3_FORENSIC

### Availability Target

```text
99.0%
```

### P95 Latency Target

```text
< 5000ms
```

---

# 14. Runtime Integration Requirements

At least one live runtime environment MUST export all required metrics end-to-end.

Metrics MUST survive:

- rolling restarts,
- runtime failovers,
- backend replacement,
- replay/recovery execution,
- exporter refreshes,
- distributed reconciliation events.

---

# 15. CI & Conformance Requirements

CI MUST validate:

1. all required metric names exist,
2. contract marker metric exists,
3. histogram families are complete,
4. label cardinality rules are enforced,
5. explainability level encoding matches normative contract,
6. dashboards reference valid metrics,
7. alert expressions reference valid metrics,
8. exporters expose stable metric types,
9. OpenTelemetry compatibility remains intact.

Required conformance tests:

- runtime decision telemetry validation,
- fallback telemetry validation,
- explainability telemetry validation,
- degraded-mode telemetry validation,
- histogram integrity validation,
- trace continuity validation,
- bounded-label enforcement validation.

---

# 16. Operational Invariants

The following invariants are mandatory.

## Deterministic Decision Telemetry

The same runtime decision MUST map to the same telemetry semantics.

## Monotonic Counters

Counter metrics MUST NEVER decrease.

## Stable Histogram Buckets

Histogram bucket boundaries MUST remain compatible within the same MAJOR version.

## Bounded Cardinality

Runtime behavior MUST NOT generate unbounded metric series.

## Export Isolation

Telemetry failures MUST NOT terminate runtime execution.

## Runtime Transparency

Fallback routing and degraded execution MUST remain observable.

## Explainability Consistency

Explainability telemetry MUST remain semantically aligned with runtime behavior.

---

# 17. Compatibility Guarantees

Eigen OS guarantees:

- stable metric names within MAJOR versions,
- deterministic runtime telemetry semantics,
- bounded label behavior,
- backward-compatible MINOR additions,
- SemVer-governed observability evolution.

These guarantees apply to:

- operators,
- SRE automation,
- dashboards,
- alerting systems,
- runtime tooling,
- enterprise monitoring integrations.

---

# 18. Migration Rules

## Additive Migration

New metrics MAY be introduced in MINOR releases.

## Deprecation Policy

Deprecated metrics MUST:

- remain available for at least one MINOR release,
- remain documented,
- emit compatibility telemetry,
- include migration guidance.

## Breaking Migration

Breaking changes require:

- MAJOR version bump,
- exporter compatibility updates,
- dashboard updates,
- alert updates,
- migration documentation,
- conformance test updates.

---

## Appendix A. Diagrams

### A.1 Contract Marker

![Contract Marker](https://i.imgur.com/WBGnmwL.png)

<details>
<summary>code</summary>

```text
flowchart TB
  S[Prometheus scrape] --> E[Exporter endpoint]
  E --> M["eigen_runtime_contract_info{version=&quot;2.1.0&quot;} 1"]
  M --> D[Dashboards]
  M --> A[Alerts]
  M --> CI[CI conformance]
  M --> Ops[Ops tooling]
```

</details>

---

### A.2 Observability Design Principles

![Observability Design Principles](https://i.imgur.com/gXhMIVa.png)

<details>
<summary>code</summary>

```text
flowchart LR
  D[Runtime decision] --> T[Telemetry emitted]
  T --> P["Prometheus metrics (bounded labels)"]
  T --> Tr["Traces (W3C TraceContext)"]
  T --> L["Structured logs (JSON/OTel logs)"]
  T --> Art["Artifacts (QFS/KB snapshots)"]
  P --> SLO[SLO/SRE signals]
  Tr --> Corr[Cross-hop correlation]
  Art --> Replay[Replay & forensics]
```

</details>

---

### A.3 Required Metrics

![Required Metrics](https://i.imgur.com/gvBs7Hx.png)

<details>
<summary>code</summary>

```text
flowchart LR
  M[Metrics families] --> D1[Decisions throughput/latency/failures]
  M --> S1[Scoring latency/failures/score gauge]
  M --> P1[Policy branches/latency/failures]
  M --> F1[Fallback & degraded fallbacks/degraded modes/ejections]
  M --> E1[Explainability req/lat/err/payload bytes]
  M --> A1[Adaptation reconfigs/model refresh/divergence]
  M --> R1[Reliability internal errors/trace breakage]
```

</details>

---

### A.4 Runtime Decision Metrics

![Runtime Decision Metrics](https://i.imgur.com/0pNTxg0.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant Sch as Scheduler
  participant Pol as Policy Engine
  participant Sc as Scoring
  participant Ex as Explain Snapshot
  participant Obs as Exporter/Telemetry

  Sch->>Pol: Evaluate policy_mode + constraints
  Obs-->>Obs: eigen_runtime_policy_branch_total{policy_mode,branch}++
  Pol-->>Sch: Policy outcome

  Sch->>Sc: Score candidates
  Obs-->>Obs: eigen_runtime_scoring_requests_total++
  Sc-->>Sch: scores + features
  Obs-->>Obs: eigen_runtime_scoring_latency_ms observe

  Sch->>Ex: Generate decision snapshot (if enabled)
  Obs-->>Obs: eigen_runtime_decision_latency_ms observe
  Obs-->>Obs: eigen_runtime_decisions_total{policy_mode,result}++
  alt failure
    Obs-->>Obs: eigen_runtime_decision_failures_total{reason}++
  end
```

</details>

---

### A.5 Backend Scoring Metrics

![Backend Scoring Metrics](https://i.imgur.com/N8485Yo.png)

<details>
<summary>code</summary>

```text
flowchart TB
  Start[Scoring cycle] --> Feat[Feature extraction]
  Feat --> Score[Model scoring]
  Score --> Norm[Normalize to score gauge]
  Norm --> Emit[Emit metrics]
  Emit --> R1[eigen_runtime_scoring_latency_ms]
  Emit --> R2["eigen_runtime_scoring_failures_total{reason}"]
  Emit --> R3["eigen_runtime_backend_score{backend,policy_mode}"]
  Feat -.fail.-> F1[reason=feature_extraction_failure]
  Score -.fail.-> F2[reason=invalid_score_model/internal_error/timeout]
```

</details>

---

### A.6 Policy Execution Metrics

![Policy Execution Metrics](https://i.imgur.com/XQE1hES.pngg)

<details>
<summary>code</summary>

```text
flowchart LR
  PM[policy_mode] --> B1[primary]
  PM --> B2[fallback]
  PM --> B3[emergency]
  PM --> B4[compliance_override]
  PM --> B5[cost_guardrail]
  PM --> B6[latency_guardrail]
  PM --> B7[availability_guardrail]
  PM --> B8[manual_override]
  B1 --> C1["eigen_runtime_policy_branch_total{policy_mode,branch}++"]
  B2 --> C1
  B3 --> C1
  B4 --> C1
  B5 --> C1
  B6 --> C1
  B7 --> C1
  B8 --> C1
```

</details>

---

### A.7 Fallback & Degradation Metrics

![Fallback & Degradation Metrics](https://i.imgur.com/J0pWDuZ.png)

<details>
<summary>code</summary>

```text
flowchart LR
  D[Decision attempt] --> O{Outcome}
  O -->|success| S[Normal routing]
  O -->|fallback| F[Fallback routing]
  O -->|degraded| G[Degraded mode]
  O -->|rejected| R[Rejected]
  O -->|failed| X[Failed]

  F --> MF["eigen_runtime_fallback_total{reason}"]
  G --> MG["eigen_runtime_degraded_mode_total{mode}"]
  G --> EJ["eigen_runtime_backend_ejections_total{backend,reason} (if ejection triggers)"]
```

</details>

---

### A.8 Explainability Metrics

![Explainability Metrics](https://i.imgur.com/OQTdxjz.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant C as Client
  participant Exp as Explain API
  participant Store as Snapshot Store (QFS/KB)
  participant Obs as Exporter/Telemetry

  C->>Exp: POST /explain/* (endpoint, level)
  Obs-->>Obs: eigen_runtime_explain_requests_total{endpoint,level}
  Exp->>Store: Load decision snapshot
  Store-->>Exp: snapshot + provenance
  Exp-->>C: Explain response
  Obs-->>Obs: eigen_runtime_explain_latency_ms{endpoint,level} observe
  Obs-->>Obs: eigen_runtime_explain_payload_bytes observe
  alt error
    Obs-->>Obs: eigen_runtime_explain_errors_total{endpoint,error_code}
  end
```

</details>

---

### A.9 Label Contract

![Label Contract](https://i.imgur.com/1KD2TSP.png)

<details>
<summary>code</summary>

```text
flowchart TB
  Good["Bounded labels (policy_mode, reason, branch, backend set, component, level)"] --> OK[Safe series growth]
  Bad["Forbidden labels (job_id, trace_id, tenant_id, user_id, request_id, correlation_id, freeform msg)"] --> Boom[Cardinality explosion + cost + instability]
  Bad --> Rule[Must go to traces/logs/artifacts]
  Rule --> Tr[Traces]
  Rule --> Log[Structured logs]
  Rule --> Art[QFS/KB]
```

</details>

---

### A.10 Histogram Requirements

![Histogram Requirements](https://i.imgur.com/yyPJOGL.png)

<details>
<summary>code</summary>

```text
flowchart LR
  H[Prometheus histogram family] --> B[Monotonic buckets]
  H --> E[Exports _bucket/_sum/_count]
  H --> C[Bucket compatibility within MAJOR]
  H --> S[Scrape-safe exposition]
  C --> CI[CI bucket validation]
```

</details>

---

### A.11 OpenTelemetry Compatibility

![OpenTelemetry Compatibility](https://i.imgur.com/MR3UUHq.png)

<details>
<summary>code</summary>

```text
flowchart TB
  Ingress[Request enters runtime] --> Sch[Scheduler span]
  Sch --> Pol[Policy span]
  Pol --> Disp[Dispatcher span]
  Disp --> W[Worker/Execution span]
  Sch --> Exp["Explainability span (if requested)"]
  W --> Art[Artifact store span]
  Art --> Replay["Replay/Recovery span (optional)"]
  Sch -.propagate traceparent.-> Pol
  Pol -.propagate traceparent.-> Disp
  Disp -.propagate traceparent.-> W
  W -.propagate traceparent.-> Art
```

</details>

---

### A.12 Operational Invariants

![Operational Invariants](https://i.imgur.com/VsI7HeS.png)

<details>
<summary>code</summary>

```text
flowchart TB
  I1[Deterministic decision telemetry] --> I2[Monotonic counters]
  I2 --> I3[Stable histogram buckets]
  I3 --> I4[Bounded cardinality]
  I4 --> I5["Export isolation (telemetry must not block)"]
  I5 --> I6["Runtime transparency (fallback/degraded visible)"]
  I6 --> I7["Explainability consistency (aligned with decisions)"]
  I7 --> I8["Trace continuity (across all hops)"]
```

</details>
