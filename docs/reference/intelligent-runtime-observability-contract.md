# Intelligent Runtime Observability Contract

**Status:** Stable observability contract for intelligent scheduling, backend selection, explainability, policy execution, adaptive routing, and runtime decision transparency.

**Contract class:** Public SRE / Operations contract.
**Applies to:** Runtime Controller, Scheduler, Explain API, Policy Engine, Driver Manager, Adaptive Routing Layer, Runtime Telemetry Exporters.

---

## 1. Purpose

This document defines the normative observability contract for the Eigen OS intelligent runtime subsystem.

The contract standardizes:

- runtime decision telemetry,
- scoring and routing observability,
- policy execution visibility,
- explainability endpoint telemetry,
- fallback and degradation behavior,
- runtime adaptation metrics,
- operator-facing SLO signals,
- Prometheus/Grafana integration,
- CI observability conformance requirements.

This contract is authoritative for all `eigen_runtime_*` metrics.

---

## 2. Contract Version

- Contract version: `2.0.0`
- Version marker metric:

```text
eigen_runtime_contract_info{version="2.0.0"} 1
```

---

## 3. SemVer Policy

### MAJOR

Incremented when:

- metric names are renamed or removed,
- metric semantics change incompatibly,
- label meaning changes incompatibly,
- histogram semantics change,
- runtime decision taxonomy changes incompatibly.

### MINOR

Incremented when:

- new metrics are added,
- optional labels are introduced,
- new explainability levels are added,
- new fallback reasons are introduced,
- additional runtime telemetry dimensions are added compatibly.

### PATCH

Incremented for:

- documentation fixes,
- alert tuning,
- dashboard corrections,
- exporter implementation fixes without semantic changes.

---

## 4. Scope

This contract governs observability for:

- intelligent backend selection,
- adaptive scheduling,
- policy evaluation,
- explainability APIs,
- routing fallback logic,
- scoring engines,
- execution heuristics,
- runtime optimization loops,
- dispatch rationale generation,
- runtime degradation handling,
- policy drift monitoring,
- distributed decision propagation.

---

## 5. Source of Truth

### Architecture References

- `docs/architecture/components/runtime-controller.md`
- `docs/architecture/components/policy-engine.md`
- `docs/architecture/components/explainability.md`
- `docs/architecture/components/observability.md`
- `docs/architecture/contracts/runtime-decisioning.md`

### Operational Assets

#### Alerts

```text
monitoring/metrics/prometheus/intelligent-runtime-alerts.yaml
```

#### Dashboards

```text
monitoring/dashboards/intelligent_runtime_dashboard.json
```

#### Runbooks

```text
docs/howto/intelligent-runtime-observability-runbook.md
```

---

## 6. Observability Design Principles

### 6.1 Deterministic Decision Visibility

Every runtime scheduling or backend-selection decision MUST produce observable telemetry.

### 6.2 Explainability Consistency

Explain APIs MUST expose telemetry aligned with runtime decision semantics.

### 6.3 Stable Metric Semantics

Metric meanings MUST remain stable across MINOR/PATCH releases.

### 6.4 Bounded Cardinality

All runtime metric labels MUST remain bounded and deterministic.

### 6.5 Runtime Transparency

Fallbacks, degraded execution, policy overrides, and emergency routing MUST be observable.

---

## 7. Required Metrics (Public Contract Surface)

### 7.1 Runtime Decision Metrics

#### Decision Throughput

```text
eigen_runtime_decisions_total{policy_mode}
```

Counter.

Counts runtime scheduling/backend-selection decisions.

#### Allowed `policy_mode`

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

---

### Decision Duration Histogram

```text
eigen_runtime_decision_latency_ms_bucket
eigen_runtime_decision_latency_ms_sum
eigen_runtime_decision_latency_ms_count
```

Histogram.

Measures total runtime decision latency.

Includes:

- policy evaluation,
- backend scoring,
- routing resolution,
- fallback selection,
- explain snapshot generation.

---

### Runtime Decision Failures

```text
eigen_runtime_decision_failures_total{reason}
```

Counter.

#### Allowed reason

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

---

### 7.2 Backend Scoring Metrics

#### Scoring Requests

```text
eigen_runtime_scoring_requests_total
```

Counter.

---

#### Scoring Latency

```text
eigen_runtime_scoring_latency_ms_bucket
eigen_runtime_scoring_latency_ms_sum
eigen_runtime_scoring_latency_ms_count
```

Histogram.

---

#### Scoring Failures

```text
eigen_runtime_scoring_failures_total{reason}
```

#### Allowed reason

```text
missing_backend_state
invalid_score_model
feature_extraction_failure
timeout
resource_exhausted
internal_error
```

---

#### Backend Score Distribution

```text
eigen_runtime_backend_score
```

Gauge.

Represents normalized backend score selected during latest evaluation cycle.

---

### 7.3 Policy Execution Metrics

#### Policy Branch Traversal

```text
eigen_runtime_policy_branch_total{policy_mode,branch}
```

Counter.

#### Allowed `branch`

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

---

#### Policy Evaluation Latency

```text
eigen_runtime_policy_eval_latency_ms_bucket
eigen_runtime_policy_eval_latency_ms_sum
eigen_runtime_policy_eval_latency_ms_count
```

Histogram.

---

#### Policy Evaluation Failures

```text
eigen_runtime_policy_failures_total{reason}
```

#### Allowed reason

```text
rule_parse_error
invalid_context
missing_input
timeout
policy_conflict
internal_error
```

---

### 7.4 Fallback and Degradation Metrics

#### Runtime Fallback Events

```text
eigen_runtime_fallback_total{reason}
```

Counter.

#### Allowed `reason`

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

---

#### Degraded Routing Activation

```text
eigen_runtime_degraded_mode_total{mode}
```

Counter.

#### Allowed `mode`

```text
reduced_scoring
safe_routing
single_backend_mode
cached_decisions
explain_disabled
```

---

#### Backend Ejection Events

```text
eigen_runtime_backend_ejections_total{reason}
```

Counter.

---

### 7.5 Explainability Metrics

#### Explain Requests

```text
eigen_runtime_explain_requests_total{endpoint,level}
```

Counter.

#### Allowed `level`

Normative encoding:

```text
L1_USER
L2_OPERATOR
L3_FORENSIC
```

Numeric encodings are prohibited beginning with contract `2.0.0`.

---

#### Explain Latency

```text
eigen_runtime_explain_latency_ms_bucket{endpoint,level}
eigen_runtime_explain_latency_ms_sum{endpoint,level}
eigen_runtime_explain_latency_ms_count{endpoint,level}
```

Histogram.

---

#### Explain Errors

```text
eigen_runtime_explain_errors_total{endpoint,error_code}
```

Counter.

---

#### Explain Payload Size

```text
eigen_runtime_explain_payload_bytes_bucket
eigen_runtime_explain_payload_bytes_sum
eigen_runtime_explain_payload_bytes_count
```

Histogram.

---

### 7.6 Runtime Adaptation Metrics

#### Adaptive Reconfiguration Events

```text
eigen_runtime_reconfigurations_total{reason}
```

Counter.

---

#### Runtime Model Refreshes

```text
eigen_runtime_model_refresh_total{model}
```

Counter.

---

#### Runtime State Divergence

```text
eigen_runtime_state_divergence_total{component}
```

Counter.

Counts runtime state inconsistencies across replicated decision components.

---

### 7.7 Reliability Metrics

#### Runtime Internal Errors

```text
eigen_runtime_internal_errors_total{component}
```

Counter.

---

#### Runtime Trace Breakage

```text
eigen_runtime_trace_breakage_total{stage}
```

Counter.

---

## 8. Label Cardinality Rules

### Mandatory Constraints

#### Labels MUST NOT include:

- `job_id`
- `trace_id`
- `tenant_id`
- `user_id`
- arbitrary backend payloads
- freeform error messages
- dynamic policy expressions

#### Labels MUST remain:

- deterministic,
- enumerable,
- bounded,
- operator-safe.

---

## 9. Histogram Requirements

The following metrics MUST use Prometheus histograms:

- decision latency,
- scoring latency,
- explain latency,
- explain payload size,
- policy evaluation latency.

---

## 10. Runtime Exporter Requirements

Runtime exporters MUST:

- expose `/metrics`,
- emit all required metrics,
- emit contract marker metric,
- preserve stable metric types,
- preserve stable labels,
- support concurrent scraping,
- support Prometheus text exposition format.

---

## 11. Alert Pack

Prometheus alert rules are maintained in:

```text
monitoring/metrics/prometheus/intelligent-runtime-alerts.yaml
```

---

## 12. Required Critical Alerts

### Runtime Decision Failure Spike

Triggers on abnormal increase in runtime decision failures.

### Scoring Latency SLO Breach

Triggers when scoring latency exceeds SLO thresholds.

### Explain Endpoint Error Rate Breach

Triggers on explain endpoint reliability degradation.

### Fallback Surge

Triggers when fallback routing frequency exceeds expected baseline.

### Trace Continuity Breakage

Triggers on distributed trace fragmentation.

### Runtime Divergence Detection

Triggers on replicated runtime state inconsistencies.

---

## 13. Dashboard Pack

Grafana dashboard:

```text
monitoring/dashboards/intelligent_runtime_dashboard.json
```

Dashboard MUST include:

- decision throughput,
- scoring latency,
- fallback rates,
- backend ejections,
- explain endpoint health,
- policy branch distribution,
- degraded mode activation,
- runtime divergence,
- contract marker visibility,
- trace continuity.

---

## 14. Explainability SLO Requirements

### L1_USER

#### Availability Target

```text
99.9%
```

#### P95 Latency Target

```text
< 250ms
```

---

### L2_OPERATOR

#### Availability Target

```text
99.5%
```

#### P95 Latency Target

```text
< 1000ms
```

---

### L3_FORENSIC

#### Availability Target

```text
99.0%
```

#### P95 Latency Target

```text
< 5000ms
```

---

## 15. CI / Conformance Requirements

CI MUST verify:

1. all required metric names exist,
2. contract marker metric exists,
3. histogram families are complete,
4. label cardinality rules are enforced,
5. explain `level` encoding matches normative contract,
6. dashboards reference valid metrics,
7. alert expressions reference valid metrics,
8. exporters expose stable metric types.

---

## 16. Compatibility Guarantees

### Stable Guarantees

The following are stable public contract surfaces:

- metric names,
- histogram semantics,
- label meanings,
- explainability levels,
- alert compatibility expectations.

---

## 17. Migration Notes

To adopt this contract:

1. expose runtime `/metrics`,
2. emit all `eigen_runtime_*` metrics,
3. load alert pack,
4. import Grafana dashboards,
5. configure explainability telemetry collection,
6. validate CI observability conformance,
7. align runbooks with alert taxonomy.

---

## 18. Minimum Closure Criteria

The contract is considered fully realized only if:

1. all required metrics are emitted in production,
2. explainability telemetry is fully instrumented,
3. policy execution telemetry is complete,
4. fallback routing is observable,
5. degraded-mode transitions are observable,
6. CI validates runtime metric presence,
7. dashboards and alerts validate against live scrape output,
8. runtime exporters are integrated into all execution profiles.

---

## 19. Invariants

The following MUST remain true:

- all runtime decisions are observable,
- explainability telemetry matches runtime behavior,
- fallback routing is visible,
- metric labels remain bounded,
- histogram semantics remain stable,
- runtime degradation cannot occur silently,
- trace continuity failures are observable,
- public metric names remain backward compatible within a MAJOR version.
