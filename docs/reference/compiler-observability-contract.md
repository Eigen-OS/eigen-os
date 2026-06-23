# Compiler Observability Contract

- **Subsystem:** Compiler Service
- **Contract version:** `1.0.0`
- **Status:** Normative
- **Applies to:** parsing, validation, AQO emission, compiler request tracing, replay evidence

---

## 1. Purpose

This document defines the observability contract for the Eigen compiler service. The contract standardizes:

- stable metric families,
- bounded-cardinality labels,
- deterministic stage timing,
- replay/duplicate compile evidence,
- structured logs with stable correlation fields.

The compiler observability surface MUST remain bounded and replay-safe.

---

## 2. Stable metric marker

The compiler service MUST expose:

```text
eigen_compiler_contract_info{version="1.0.0"} 1
```

This metric is the contract marker for compiler observability conformance.

---

## 3. Required metric families

The compiler observability surface MUST include:

- `eigen_compiler_rpc_total{rpc,outcome}`
- `eigen_compiler_stage_duration_seconds_count{stage,outcome}`
- `eigen_compiler_stage_duration_seconds_sum{stage,outcome}`
- `eigen_compiler_validation_failures_total{stage,reason}`
- `eigen_compiler_aqo_digest_emitted_total{kind}`
- `eigen_compiler_replay_compiles_total{kind}`
- `eigen_compiler_evaluation_total{compiler_version,job_type,decision_source}`
- `eigen_compiler_evaluation_latency_seconds_count{compiler_version,job_type,decision_source}`
- `eigen_compiler_evaluation_latency_seconds_sum{compiler_version,job_type,decision_source}`
- `eigen_compiler_symbolic_rewrite_stage_duration_seconds_count{stage,outcome}`
- `eigen_compiler_symbolic_rewrite_stage_duration_seconds_sum{stage,outcome}`

### Allowed label values

**rpc**

- `CompileCircuit`
- `CompileJob`

**stage**

- `request_validation`
- `parse`
- `validate_ast`
- `annotate`
- `lower_to_ir`
- `eigen_dpda`
- `canonicalize_aqo`
- `emit`

**symbolic_rewrite_stage**

- `parse`
- `normalize`
- `candidate_generation`
- `legality_check`
- `rewrite`
- `emit_aqo`

**outcome**

- `success`
- `failure`

**reason**

- `invalid_argument`
- `not_found`
- `resource_exhausted`
- `unimplemented`
- `internal`

**kind**

- `aqo`
- `duplicate`

**compiler_version**

- bounded compiler contract version string emitted in compile metadata (for example, `1.0.0`)

**job_type**

- `QuantumJob`
- `HybridWorkflow`
- `DistributedJob`
- `BenchmarkJob`
- `PipelineJob`
- `ReplayJob`

**decision_source**

- `symbolic_rules`
- `gnn_ranking`
- `boosting_ranking`
- `fallback`

Trace IDs, request IDs, tenant IDs, project IDs, and job IDs MUST NOT be exposed in metric labels.

The evaluation metric families above MUST record successful compile traces and expose the final decision source and latency sliced by compiler version and job type so dashboards can compute model-assisted acceptance rate, fallback rate, and latency.

### 3.1 Evaluation dashboards

For A/B or shadow evaluations, dashboards MUST compare the baseline symbolic core against hybrid mode using the metric families above. For current compiler traffic, `QuantumJob` is the baseline symbolic-core slice and `HybridWorkflow` is the hybrid-mode slice.

The canonical dashboard specification lives in `docs/reference/compiler-evaluation-dashboard.md`.

---

## 4. Structured logs

Compiler logs MUST include stable correlation fields:

- `rpc`
- `job_id`
- `request_id`
- `trace_id`
- `traceparent`
- `stage`
- `outcome`
- `elapsed_ms`
- `aqo_sha256`
- `source_sha256`
- `decision_source`

When the symbolic rewrite pipeline is executed, logs MUST additionally include `rewrite_stage`, `rewrite_stage_index`, `rewrite_stage_outcome`, and `rewrite_stage_digest`. For compile-end traces, logs MUST also include `decision_source` with one of `symbolic_rules`, `gnn_ranking`, `boosting_ranking`, or `fallback`.

---

## 5. Explainability and lineage payloads

The compiler MUST emit bounded explainability metadata that can be copied into the optimizer handoff without introducing hidden state.

Required payload fields:

- `decision_lineage_json`
- `observability_json`
- `explainability_json`
- `compiler_replay_json`
- `compiler_replay_sha256`
- `compiler_diagnostics_json`
- `symbolic_candidate_set_json`
- `symbolic_candidate_set_sha256`
- `logical_graph_schema_json`
- `logical_graph_schema_sha256`
- `telemetry_feature_set_json`
- `telemetry_feature_set_sha256`
- `decision_source`

Those payloads MUST remain deterministic for identical inputs and MUST include only bounded trace and metric fields:

- trace fields: `request_id`, `trace_id`, `traceparent`
- metric fields: `rpc`, `stage`, `outcome`, `elapsed_ms`
- label-family bounds: no request, trace, tenant, or project identifiers in metric labels

`compiler_diagnostics_json` MUST summarize the compiler stage order, the resolved workload profile, the backend contract, and the final `decision_source` in a machine-readable payload that remains stable for identical inputs.

`symbolic_candidate_set_json` MUST summarize the bounded candidate set emitted by the symbolic core. Each candidate entry MUST expose a stable `candidate_id`, a compact feature map, and a boolean legality flag. The payload MUST also expose `ranked_candidates`, a legal-candidate-only list ordered by deterministic compiler-side advisory ordering. The ML advisor is a separate sidecar service and may be disabled without changing compiler correctness. Each ranked entry MUST expose `rank`, `confidence`, the `graph_encoding` consumed by the advisory layer, and an `explanation` object with a human-readable `why_preferred` summary plus bounded `influential_features` and `influential_subgraph` hooks. `selected_candidate_explanation` MUST mirror the first ranked candidate summary. Advisory layers MUST only score candidates where `legal` is true.

`logical_graph_schema_json` MUST describe the canonical graph schema used by the compiler for AST, IR, and DPDA state graphs. The schema MUST be shared by training and inference consumers, MUST define bounded node and edge fields, MUST define stable labels for each graph kind, and MUST preserve deterministic ordering semantics. `logical_graph_schema_sha256` MUST be the SHA-256 digest of that canonical JSON payload.

This compiler-side schema is the logical-graph contract that the Optimizer Service matches against the Driver Manager physical graph via `graph_pair_id` and `graph_interface_id`. It MUST stay aligned with `logical-compiler-graph-v1` in the internal optimizer contract.

`telemetry_feature_set_json` MUST describe the stable tabular telemetry feature set used for compiler and KB telemetry parity. The schema version MUST be `telemetry-tabular-v1`, and the payload MUST expose graph size, fanout, stage counts, historical success rate, latency, backend, and policy-state features in a deterministic order. `telemetry_feature_set_sha256` MUST be the SHA-256 digest of that canonical JSON payload.

Validation failures MUST also carry structured gRPC details with:

- `google.rpc.BadRequest` for field-level violations,
- `google.rpc.ErrorInfo` for stage/rule/pass attribution,
- a bounded `diagnostics_json` metadata value containing the same machine-readable diagnostic payload.

The lineage payload MUST preserve the compiler-to-optimizer boundary contract:

- contract versions,
- source precedence,
- source and AQO digests,
- request digest,
- stable stage order,
- deterministic replay bundle digest,
- symbolic rule provenance for the lowering pipeline.

---

## 6. Replay evidence

Repeated compilation of identical inputs MUST be observable as:

- identical AQO bytes,
- identical AQO hash,
- identical `compiler_replay_json` and `compiler_replay_sha256`,
- incremented duplicate/replay counter,
- stable request-correlation logs.

---

## 7. Deferred telemetry

Intentionally deferred telemetry MUST be documented rather than introduced as ad-hoc labels. Deferred items include:

- per-request identifiers in metric labels,
- per-tenant metric cardinality,
- backend-specific compiler internals,
- QFS storage internals that are covered by the QFS contract instead.
