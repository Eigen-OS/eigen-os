# Knowledge Base: canonical patterns and candidate retrieval

**Contract version:** 1.0.0  
**Status:** Target architecture contract for deterministic KB reuse and canonical pattern selection  
**Applies to:** `KnowledgeBaseService` similarity search, canonical pattern retrieval, replay tooling, and optimizer reuse selection

## 1. Scope

The Knowledge Base exposes two distinct behaviors:

1. **Public record storage** — CRUD/query for KB records and decision logs.
2. **Optimization Knowledge Base (OKB) retrieval** — deterministic reuse selection for compiler / AQO workflows.

This document defines the retrieval semantics for both candidate similarity search and canonical pattern lookup.

## 2. Retrieval primitives

### Candidate pattern

A candidate pattern is a historical, replay-safe pattern extracted from KB artifacts. Candidate patterns may be similar to the current request, but they are not canonical by default.

### Canonical pattern

A canonical pattern is the single template selected by `GetPattern` when the request compatibility window matches exactly. The canonical pattern is deterministic and machine-verifiable.

### Explanation pattern

An explanation pattern is a bounded diagnostic envelope that explains why a canonical pattern was selected or why no canonical pattern was available.

## 3. Similarity query definition

A similarity query is a deterministic ranking query over a scoped candidate pool.

Every query MUST be scoped by:

- `tenant_id`
- `project_id`

The retrieval backend MUST NOT mix candidates across tenant or project boundaries.

### Supported modes

- `structural`: rank by structural compatibility and support.
- `vector`: rank by deterministic vector-similarity surrogate.
- `hybrid`: rank by a combined score derived from structural and vector scores.

## 4. Candidate pool

The candidate pool is bounded and deterministic.

The backend MAY derive candidates from:

- benchmark records,
- runtime decision logs,
- other replay-safe KB artifacts that are in the same tenant/project scope.

The pool MUST be filtered before scoring. Cross-scope data MUST NOT be considered.

## 5. Rank source of truth

For candidate retrieval, the final ranking score is `score_total`.

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

## 6. Canonical pattern selection (`GetPattern`)

`GetPattern` returns a canonical template, not just a similar historical object.

The canonical pattern MUST satisfy the exact compatibility window for the request:

- `schema_version`
- `compiler_version`
- `aqo_version`
- `optimizer_version`
- `policy_mode`
- `policy_digest`

Compatibility metadata MUST be machine-verifiable by exact string equality and a deterministic `compatibility_signature` hash over the normalized compatibility window.

### Canonical selection rule

Among compatible candidates, the canonical pattern is selected deterministically using:

1. `support` descending,
2. `pattern_family` ascending,
3. `pattern_id` ascending.

This rule is independent from candidate similarity scoring.

### Incompatibility reason codes

When a pattern is not canonical-eligible, the backend MUST report deterministic reason codes:

- `SCHEMA_MISMATCH`
- `COMPILER_MISMATCH`
- `AQO_MISMATCH`
- `OPTIMIZER_MISMATCH`
- `POLICY_MISMATCH`

## 7. Cardinality and replay

The candidate budget is bounded.

- `candidate_budget` is clamped to a maximum of `8`.
- Returned candidates MUST be truncated to the final budget.
- No pagination or streaming is used for this retrieval path.

Deterministic replay requires that the same normalized query input returns the same ordered candidate list and the same canonical selection.

## 8. Required deterministic inputs

A normalized query MUST include:

- `tenant_id`
- `project_id`
- `snapshot_id`
- `circuit_id`
- `backend_class`
- `semantic_hash`
- `aqo_hash`
- `schema_version`
- `compiler_version`
- `aqo_version`
- `optimizer_version`
- `policy_mode`
- `policy_digest`
- `seed`
- `deterministic`
- `query_mode`
- `candidate_budget`

## 9. Contracted output fields

Returned candidate patterns MUST include:

- `pattern_id`
- `pattern_family`
- `pattern_kind`
- `circuit_id`
- `backend_class`
- `source_record_ids`
- `support`
- `compatibility_window`
- `compatibility_signature`
- `canonical_eligible`
- `selected`
- `rank`
- `score_breakdown`
- `score_total`
- `confidence`
- `incompatibility_reasons
- `metadata`

The canonical response MUST also include:

- `tenant_id`
- `project_id`
- `candidate_budget`
- `canonical_pattern_id`
- `canonical_pattern`
- `candidate_patterns`
- `explanation_pattern`
- `diagnostics`

## 10. Compatibility notes

This contract is backward-compatible with the existing in-memory KB baseline because:

- the candidate pool remains bounded,
- the ranking remains deterministic,
- the scope filter is stricter, not looser,
- the output is additive,
- canonical lookup is separated from similarity lookup.

Any caller that does not provide tenant/project scope is invalid for similarity retrieval.
