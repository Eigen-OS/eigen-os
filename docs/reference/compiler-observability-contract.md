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

Trace IDs, request IDs, tenant IDs, project IDs, and job IDs MUST NOT be exposed in metric labels.

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

When the symbolic rewrite pipeline is executed, logs MUST additionally include `rewrite_stage`, `rewrite_stage_index`, `rewrite_stage_outcome`, and `rewrite_stage_digest`.

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

Those payloads MUST remain deterministic for identical inputs and MUST include only bounded trace and metric fields:

- trace fields: `request_id`, `trace_id`, `traceparent`
- metric fields: `rpc`, `stage`, `outcome`, `elapsed_ms`
- label-family bounds: no request, trace, tenant, or project identifiers in metric labels

`compiler_diagnostics_json` MUST summarize the compiler stage order, the resolved workload profile, and the backend contract in a machine-readable payload that remains stable for identical inputs.

`symbolic_candidate_set_json` MUST summarize the bounded candidate set emitted by the symbolic core. Each candidate entry MUST expose a stable `candidate_id`, a compact feature map, and a boolean legality flag. The payload MUST also expose `ranked_candidates`, a legal-candidate-only list ordered by deterministic boosting usefulness scoring trained from a bounded labeled pass-path corpus, and each ranked entry MUST expose `rank`, `confidence`, the `graph_encoding` consumed by the ranker, and an `explanation` object with a human-readable `why_preferred` summary plus bounded `influential_features` and `influential_subgraph` hooks. The ranker advertises its explanation mode as `feature_attribution`. `selected_candidate_explanation` MUST mirror the applied candidate summary. When the top ranked candidate falls below the versioned confidence threshold, the compiler MUST record `fallback_used`, `fallback_reason`, and `selection_mode` in the ranker payload and fall back to the symbolic baseline candidate. The ranked candidate list remains advisory only in that case. Model ranking layers MUST only score candidates where `legal` is true.

`logical_graph_schema_json` MUST describe the canonical graph schema used by the compiler for AST, IR, and DPDA state graphs. The schema MUST be shared by training and inference consumers, MUST define bounded node and edge fields, MUST define stable labels for each graph kind, and MUST preserve deterministic ordering semantics. `logical_graph_schema_sha256` MUST be the SHA-256 digest of that canonical JSON payload.

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
