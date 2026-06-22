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
The boundary between KB retrieval, deterministic replay, and ML-advisor consumption is defined in `docs/architecture/components/neuro-symbolic-core.md`.

## 2. Retrieval primitives

### Candidate pattern

A candidate pattern is a historical, replay-safe pattern extracted from KB artifacts. Candidate patterns may be similar to the current request, but they are not canonical by default.

### Canonical pattern

A canonical pattern is the single template selected by `GetPattern` when the request compatibility window matches exactly. The canonical pattern is deterministic and machine-verifiable.

### Explanation pattern

An explanation pattern is a bounded diagnostic envelope that explains why a canonical pattern was selected or why no canonical pattern was available.

## 2.4 Stable request/response contract

The compiler, optimizer, and driver-manager integrations MUST use the same versioned KB envelope for both similarity lookup and canonical pattern lookup.

The envelope is deterministic and replay-safe. The ML layer may rank or explain results, but it MUST NOT invent or rewrite any authoritative field in the request, the returned pattern record, or the attached provenance.

### 2.4.1 `knowledge_context`

`knowledge_context` is the normalized request context attached to every KB call and mirrored in every response.

Required fields:

| Field | Type | Required | Semantics |
|---|---|---:|---|
| `contract_version` | string | yes | KB request/response contract version. Must be `1.0.0` for this document set. |
| `schema_version` | string | yes | Schema revision for the normalized context envelope. |
| `request_id` | string | yes | Deterministic request identifier used for replay and provenance. |
| `tenant_id` | string | yes | Tenant boundary. Never inferred. |
| `project_id` | string | yes | Project boundary. Never inferred. |
| `caller_component` | string | yes | One of `compiler`, `optimizer`, `driver_manager`, `neuro_symbolic_service`, `kernel_gateway`. |
| `request_kind` | string | yes | One of `similar_pattern_lookup`, `canonical_pattern_lookup`, `record_query`, `decision_log_query`. |
| `deterministic` | bool | yes | `true` when the caller requires exact replay semantics. |
| `seed` | uint64 | yes | Deterministic seed for ranking and tie-breaking. |
| `snapshot_id` | string | yes | Snapshot identifier for the KB and model/policy binding. |
| `policy_snapshot_version` | string | yes | Policy snapshot version used to validate the request. |
| `policy_mode` | string | yes | Policy mode used by the deterministic selection path. |
| `policy_digest` | string | yes | Canonical digest of the policy snapshot. |
| `model_snapshot_id` | string | yes | Model snapshot identifier bound to the advisory layer. |
| `model_snapshot_digest` | string | yes | Canonical digest of the model snapshot. |
| `compiler_version` | string | conditional | Required for compiler-originated requests. |
| `optimizer_version` | string | conditional | Required for optimizer-originated requests. |
| `aqo_version` | string | conditional | Required when the request references AQO. |
| `backend_class` | string | yes | Backend class used to scope canonical pattern selection. |
| `circuit_id` | string | yes | Circuit identity for the lookup scope. |
| `semantic_hash` | string | yes | Canonical semantic fingerprint for the request payload. |
| `aqo_hash` | string | conditional | Required when the request concerns AQO reuse. |
| `capability_scope` | string | yes | Normalized capability scope. Must fail closed on mismatch. |
| `capability_tags` | repeated string | yes | Normalized capability tags used to derive the capability scope. |
| `candidate_budget` | uint32 | yes | Requested candidate budget before clamping. |
| `query_mode` | string | yes | One of `structural`, `vector`, or `hybrid`. |
| `include_provenance` | bool | yes | When `true`, the response MUST include full provenance metadata. |
| `request_digest_sha256` | string | yes | Digest of the normalized request envelope. |

Normative rules:

- `knowledge_context` is authoritative input, not model output.
- The ML layer MUST NOT infer `tenant_id`, `project_id`, `snapshot_id`, `policy_digest`, `request_digest_sha256`, or any compatibility field.
- Requests that omit required boundary fields MUST fail closed.
- The same normalized `knowledge_context` MUST produce the same replay identity, candidate ordering, and provenance fields.

### 2.4.2 `PatternRecord`

`PatternRecord` is the canonical stored and returned representation of a candidate or canonical pattern.

Required fields:

| Field | Type | Required | Semantics |
|---|---|---:|---|
| `pattern_id` | string | yes | Stable record identifier. |
| `pattern_family` | string | yes | Family name used in canonical selection ordering. |
| `pattern_kind` | string | yes | Kind such as compiler pattern, optimizer pattern, or driver pattern. |
| `tenant_id` | string | yes | Tenant boundary. |
| `project_id` | string | yes | Project boundary. |
| `circuit_id` | string | yes | Circuit identity. |
| `backend_class` | string | yes | Backend scope. |
| `source_record_ids` | repeated string | yes | Primary-source record identifiers for provenance and replay. |
| `support` | uint64 | yes | Deterministic support count used for canonical ranking. |
| `compatibility_window` | object | yes | The normalized compatibility window. |
| `compatibility_signature` | string | yes | SHA-256 over the normalized compatibility window. |
| `canonical_eligible` | bool | yes | Whether the pattern satisfies the exact canonical eligibility gate. |
| `selected` | bool | yes | Whether this record was selected in the current response. |
| `rank` | uint32 | yes | Deterministic rank in the returned list. |
| `score_breakdown` | object | yes | Deterministic score components. |
| `score_total` | float | yes | Final deterministic ranking score. |
| `confidence` | float | yes | Secondary ordering key. |
| `incompatibility_reasons` | repeated string | yes | Deterministic reason codes for ineligibility. |
| `metadata` | object | yes | Additional bounded metadata, never authoritative truth. |
| `provenance` | object | yes | Attached provenance for this record. |

`compatibility_window` MUST contain the exact fields used by canonical selection:

- `schema_version`
- `compiler_version`
- `aqo_version`
- `optimizer_version`
- `policy_mode`
- `policy_digest`
- `snapshot_id`
- `backend_class`
- `capability_scope`

### 2.4.3 Response provenance

Every KB response MUST include a provenance object, including empty-result responses and diagnostics-only fallbacks.

Required provenance fields:

| Field | Type | Required | Semantics |
|---|---|---:|---|
| `contract_version` | string | yes | Provenance schema version. |
| `request_id` | string | yes | Echo of `knowledge_context.request_id`. |
| `request_digest_sha256` | string | yes | Echo of the normalized request digest. |
| `response_digest_sha256` | string | yes | Digest of the normalized response payload. |
| `snapshot_id` | string | yes | Snapshot bound to the response. |
| `policy_snapshot_version` | string | yes | Policy snapshot used for validation. |
| `model_snapshot_id` | string | yes | Model snapshot bound to advisory ranking. |
| `retrieval_mode` | string | yes | `similar_pattern_lookup`, `canonical_pattern_lookup`, `record_query`, or `decision_log_query`. |
| `selected_pattern_id` | string | conditional | Present when a canonical or best-effort pattern is selected. |
| `source_record_ids` | repeated string | yes | Source records that informed the response. |
| `generated_at` | string | yes | RFC 3339 timestamp for the deterministic response envelope. |
| `replay_safe` | bool | yes | `true` when the response is replay-safe under the same normalized input. |

The provenance object is attached to:

- `SearchSimilarResponse`
- `GetPatternResponse`
- any other KB response that can affect compiler, optimizer, or driver-manager decisions

### 2.4.4 Similar-pattern lookup

The stable request/response contract for similar-pattern lookup is:

```protobuf
message SearchSimilarRequest {
  string contract_version = 1;
  KnowledgeContext knowledge_context = 2;
  PatternQuery pattern_query = 3;
  uint32 candidate_budget = 4;
  string query_mode = 5;   // structural | vector | hybrid
  bool deterministic = 6;
}

message SearchSimilarResponse {
  string contract_version = 1;
  KnowledgeContext knowledge_context = 2;
  repeated PatternRecord candidate_patterns = 3;
  PatternRecord selected_candidate = 4;
  PatternRecord explanation_pattern = 5;
  ResponseProvenance provenance = 6;
  Diagnostics diagnostics = 7;
}
```

Semantics:

- `candidate_budget` is clamped to the service maximum of `8`.
- The response MUST preserve the ordered candidate list returned by the deterministic ranking path.
- `selected_candidate` MUST be the first ranked candidate when one exists.
- `explanation_pattern` MAY be empty, but its provenance MUST still be present.
- When there are no candidates, `candidate_patterns` MUST be empty and `selected_candidate` MUST be unset.

### 2.4.5 Canonical pattern lookup

The stable request/response contract for canonical pattern lookup is:

```protobuf
message GetPatternRequest {
  string contract_version = 1;
  KnowledgeContext knowledge_context = 2;
  PatternQuery pattern_query = 3;
  uint32 candidate_budget = 4;
  bool deterministic = 5;
}

message GetPatternResponse {
  string contract_version = 1;
  KnowledgeContext knowledge_context = 2;
  PatternRecord canonical_pattern = 3;
  repeated PatternRecord candidate_patterns = 4;
  PatternRecord explanation_pattern = 5;
  ResponseProvenance provenance = 6;
  Diagnostics diagnostics = 7;
}
```

Semantics:

- The canonical pattern is selected only when the exact compatibility window matches.
- If no canonical pattern exists, `canonical_pattern` MUST be unset and diagnostics MUST report the deterministic incompatibility reason codes.
- `candidate_patterns` MAY still contain compatible or nearly compatible records, but only `canonical_pattern` may be treated as authoritative.
- The canonical response MUST be reproducible from the same `knowledge_context` and `pattern_query`.

### 2.4.6 Pattern query

```protobuf
message PatternQuery {
  string semantic_hash = 1;
  string aqo_hash = 2;
  string circuit_id = 3;
  string backend_class = 4;
  CompatibilityWindow compatibility_window = 5;
}
```

```protobuf
message CompatibilityWindow {
  string schema_version = 1;
  string compiler_version = 2;
  string aqo_version = 3;
  string optimizer_version = 4;
  string policy_mode = 5;
  string policy_digest = 6;
  string snapshot_id = 7;
  string backend_class = 8;
  string capability_scope = 9;
}
```

```protobuf
message ResponseProvenance {
  string contract_version = 1;
  string request_id = 2;
  string request_digest_sha256 = 3;
  string response_digest_sha256 = 4;
  string snapshot_id = 5;
  string policy_snapshot_version = 6;
  string model_snapshot_id = 7;
  string retrieval_mode = 8;
  string selected_pattern_id = 9;
  repeated string source_record_ids = 10;
  string generated_at = 11;
  bool replay_safe = 12;
}
```

```protobuf
message PatternRecord {
  string pattern_id = 1;
  string pattern_family = 2;
  string pattern_kind = 3;
  string tenant_id = 4;
  string project_id = 5;
  string circuit_id = 6;
  string backend_class = 7;
  repeated string source_record_ids = 8;
  uint64 support = 9;
  CompatibilityWindow compatibility_window = 10;
  string compatibility_signature = 11;
  bool canonical_eligible = 12;
  bool selected = 13;
  uint32 rank = 14;
  map<string, double> score_breakdown = 15;
  double score_total = 16;
  double confidence = 17;
  repeated string incompatibility_reasons = 18;
  map<string, string> metadata = 19;
  ResponseProvenance provenance = 20;
}
```

`PatternQuery` is never authoritative truth; it is only a deterministic retrieval key. The model may score candidates, but it MUST NOT infer or mutate the compatibility window.

## 3. Similarity query definition

A similarity query is a deterministic ranking query over a scoped candidate pool. It MUST use the `knowledge_context`, `PatternQuery`, `PatternRecord`, and `ResponseProvenance` shapes defined above.

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

The candidate pool is bounded and deterministic. The KB may rank or return evidence, but it may not infer canonical truth for the caller.

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
- `incompatibility_reasons`
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
