# Compiler Evaluation Dashboard

- **Document status:** Normative reference
- **Subsystem:** Compiler Service
- **Contract version:** `1.0.0`
- **Applies to:** A/B and shadow evaluations for baseline symbolic core versus hybrid mode

This document defines the dashboard slice for issue #781. The compiler already emits bounded evaluation metrics with `compiler_version`, `job_type`, and `decision_source` labels. The dashboard uses those metrics to compare the baseline symbolic core against hybrid mode without introducing any new labels or unbounded trace identifiers.

---

## 1. Comparison model

For current compiler traffic:

- `QuantumJob` is the baseline symbolic-core slice.
- `HybridWorkflow` is the hybrid-mode slice.

The dashboard SHOULD compare both slices over the same time window and the same compiler version whenever possible.

The primary signals are:

- acceptance rate,
- fallback rate,
- decision-source mix,
- average latency.

Acceptance rate and fallback rate are quality proxies. Lower fallback rate and higher acceptance rate are stronger signals that hybrid mode is helping.

---

## 2. Required panels

### 2.1 Acceptance rate

This panel shows the share of compile traces whose final decision source is symbolic rules.

```promql
sum by (compiler_version, job_type) (
  rate(eigen_compiler_evaluation_total{decision_source="symbolic_rules"}[5m])
)
/
sum by (compiler_version, job_type) (
  rate(eigen_compiler_evaluation_total[5m])
)
```

### 2.2 Fallback rate

This panel shows the share of compile traces that had to fall back to the safe default path.

```promql
+sum by (compiler_version, job_type) (
  rate(eigen_compiler_evaluation_total{decision_source="fallback"}[5m])
)
/
sum by (compiler_version, job_type) (
  rate(eigen_compiler_evaluation_total[5m])
)
```

### 2.3 Average latency

The contract exposes latency as count and sum, so the dashboard SHOULD render average latency as `sum / count`.

```promql
sum by (compiler_version, job_type, decision_source) (
  rate(eigen_compiler_evaluation_latency_seconds_sum[5m])
)
/
sum by (compiler_version, job_type, decision_source) (
  rate(eigen_compiler_evaluation_latency_seconds_count[5m])
)
```

### 2.4 Decision-source mix

This panel should show how the final choice is distributed across symbolic rules, GNN ranking, boosting ranking, and fallback. It helps verify whether hybrid mode is changing the decision surface or merely adding latency.

```promql
sum by (compiler_version, job_type, decision_source) (
  rate(eigen_compiler_evaluation_total[5m])
)
```

---

## 3. Interpretation

Hybrid mode is considered better when, for the same compiler version and comparable workload mix, it improves one or more of the following:

- increases acceptance rate,
- decreases fallback rate,
- decreases average latency.

The dashboard SHOULD use the same dashboard time range for both slices and SHOULD keep the grouping bounded to `compiler_version`, `job_type`, and `decision_source`.
