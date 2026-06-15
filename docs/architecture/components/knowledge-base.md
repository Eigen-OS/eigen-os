**Contract version:** 1.0.0  
**Status:** Target architecture contract for deterministic OKB candidate retrieval  
**Applies to:** `KnowledgeBaseService` similarity search, replay tooling, and optimizer reuse selection

## 1. Scope

The Knowledge Base exposes two distinct behaviors:

1. **Public record storage** — CRUD/query for KB records and decision logs.
2. **Optimization Knowledge Base (OKB) candidate retrieval** — deterministic reuse selection for optimizer/compiler workflows.

This document defines the OKB retrieval semantics only.

## 2. Similarity query definition

A similarity query is a **deterministic ranking query over a scoped candidate pool**.

Every query MUST be scoped by:

- `tenant_id`
- `project_id`

The retrieval backend MUST NOT mix candidates across tenant or project boundaries.

### Supported modes

- `structural`: rank by structural compatibility.
- `vector`: rank by deterministic vector-similarity surrogate.
- `hybrid`: rank by a combined score derived from structural and vector scores.

## 3. Candidate pool

The candidate pool is bounded and deterministic.

The backend MAY derive candidates from:

- benchmark records,
- runtime decision logs,
- other replay-safe KB artifacts that are in the same tenant/project scope.

The pool MUST be filtered before scoring. Cross-scope data MUST NOT be considered.

## 4. Rank source of truth

The final ranking score is `score_total`.

Per mode:

- `structural`: `score_total = structural_score`
- `vector`: `score_total = vector_score`
- `hybrid`: `score_total = round((structural_score * 0.6) + (vector_score * 0.4), 6)`

The secondary ordering key is `confidence`.

The final tiebreaker is `candidate_id` in ascending lexical order.

### Score bounds

- `structural_score`: `0.0..1.0`
- `vector_score`: `0.0..1.0`
- `confidence`: `0.0..1.0`
- `score_total`: `0.0..1.0`

## 5. Cardinality and replay

The candidate budget is bounded.

- `candidate_budget` is clamped to a maximum of `8`.
- Returned candidates MUST be truncated to the final budget.
- No pagination or streaming is used for this retrieval path.

Deterministic replay requires that the same normalized query input returns the same ordered candidate list.

## 6. Required deterministic inputs

A normalized query MUST include:

- `tenant_id`
- `project_id`
- `semantic_hash`
- `aqo_hash`
- `backend_profile_id`
- `topology_snapshot_digest`
- `policy_envelope_digest`
- `kb_schema_version`
- `compiler_version`
- `optimizer_version`
- `seed`
- `deterministic`
- `query_mode`
- `candidate_budget`

## 7. Contracted output fields

Returned candidates MUST include:

- `candidate_id`
- `candidate_source`
- `optimization_type`
- `transformation_ref`
- `provenance_ref`
- `compatibility_window`
- `deterministic_digest`
- `explanation_ref`
- `selection_reason`
- `confidence`
- `score_breakdown`
- `score_total`
- `selected`
- `metadata`

The output MUST also include:

- `tenant_id`
- `project_id`
- `candidate_budget`
- `selected_candidate_id`
- `okb_selection_digest`

## 8. Stable tie-breaking

If two or more candidates share the same `score_total` and `confidence`, the backend MUST sort by `candidate_id` ascending.

This guarantees replay-stable ordering when the normalized input is unchanged.

## 9. Compatibility notes

This contract is backward-compatible with the existing in-memory KB baseline because:

- the candidate pool remains bounded,
- the ranking remains deterministic,
- the scope filter is stricter, not looser,
- the output is additive.

Any caller that does not provide tenant/project scope is invalid for similarity retrieval.
