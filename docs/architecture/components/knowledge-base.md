# Knowledge Base: canonical patterns and candidate retrieval

**Contract version:** 1.0.0  
**Status:** Target architecture contract for deterministic KB reuse and canonical pattern selection  
**Applies to:** `KnowledgeBaseService` similarity search, canonical pattern retrieval, replay tooling, and optimizer reuse selection

## 1. Scope

The Knowledge Base exposes two distinct behaviors:

1. **Public record storage** — CRUD/query for KB records and decision logs.
2. **Optimization Knowledge Base (OKB) retrieval** — deterministic reuse selection for compiler / AQO workflows.

Runtime decision logs are append-only and MUST preserve the audit trail fields required by the neuro-symbolic compliance contract: caller identity, tenant, policy snapshot version, model version, retrieval sources, and final decision.

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
- capability scope, when the request carries capability tags or capability metadata

The retrieval backend MUST NOT mix candidates across tenant, project, or capability boundaries.

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
When capability metadata is present, the pool MUST also be filtered to the request capability scope and MUST fail closed on mismatch.
Mixed-tenant, mixed-project, or mixed-capability snapshots are invalid and MUST be rejected before retrieval.
All explanation and replay outputs MUST stay within the same tenant/project/capability boundary and MUST NOT echo foreign identifiers or payload fragments.

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
- `capability_scope` / `capability_tags` / `capabilities` or an equivalent backend capability discriminator
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
Snapshot ingest MUST preserve the snapshot's tenant/project/capability scope, and retrieval helpers MUST fail closed when the request scope does not match that stored boundary.

## 11. Index synchronization, recovery, and backfill

The KB uses the primary store as the source of truth.

Primary store:
- record documents,
- decision logs,
- replay-safe evidence.

Derived indexes:
- structural index,
- vector index.

### Build order

When a scope is synchronized, the backend MUST build derived indexes in this order:

1. structural index,
2. vector index,
3. health reconciliation.

The build is deterministic and idempotent. Re-running the same rebuild or backfill with the same primary-store snapshot MUST produce the same derived index state.

### Recovery procedure

After a cold start or crash restart:

1. inspect index health,
2. recover from the primary store,
3. verify the derived index fingerprint matches the primary snapshot,
4. resume queries only after the scope reports `ready`.

### Backfill procedure

Backfill is used to catch up historical primary-store records after a partial outage.

- Backfill MUST only read from the primary store.
- Backfill MUST NOT mutate primary records.
- Backfill MAY be rerun safely.
- Backfill MUST be scope-aware and tenant/project isolated.

### Health states

The operational status model is:

- `ready` — primary store and derived index match,
- `rebuilding` — a scope is actively being synchronized,
- `degraded` — a mismatch or partial failure was detected,
- `unavailable` — the index is not currently present or the storage layer is disabled.

### Partial failure behavior

If one derived index fails while another succeeds, the scope MUST be marked `degraded`. The primary store remains the source of truth, and the scope can be repaired by `recover_indexes` or `rebuild_indexes`.

### Query-time behavior

Similarity queries MUST:

- verify scope health before ranking,
- recover a missing scope from the primary store,
- never return cross-tenant/project candidates,
- expose the current health snapshot in diagnostics.

## 12. KB-backed training datasets

Neuro-Symbolic Service may ingest offline training datasets into the KB-backed corpus for replay-safe later training runs.

### 12.1 Dataset manifest requirements

A training dataset manifest MUST include:

- `schema_version`
- `contract_version`
- `dataset_id`
- `dataset_version`
- `record_schema_version`
- `tenant_id`
- `project_id`
- `policy_snapshot_version`
- `ownership`
- `provenance`
- `redaction`
- `records`
- `manifest_digest_sha256`

### 12.2 Validation rules

Ingestion MUST fail closed unless:

- the manifest schema matches the documented version,
- ownership resolves to the internal ingest caller,
- provenance digests are present and verifiable,
- redaction has been applied and validated,
- every record is already redacted,
- every record digest matches the canonical payload,
- the active policy snapshot version matches the manifest.

### 12.3 Replayability

The corpus MUST preserve the dataset version, record digests, provenance, and redaction metadata so the same manifest can be re-ingested deterministically and later consumed by the training pipeline without live lookups.
