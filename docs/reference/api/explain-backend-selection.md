# Explain API — Backend Selection (`/explain/backend-selection`)

This page records the current state of the explain contract for backend selection and its coverage in code/tests.

## Current implementation status (as of 2026-05-09)

- Status: **implemented at domain/service layer** in `resource-manager` as a stable versioned DTO + deterministic mapper.
- Status: **conformance covered** by golden-fixture and deterministic replay tests.
- Status: **transport binding is not documented/locked here** (there is no separate HTTP/gRPC handler contract locked on this page).

Primary implementation points:

- Request DTO: `ExplainBackendSelectionRequest`.  
- Response DTO: `ExplainBackendSelectionResponse`.  
- Builder/mapper: `explain_backend_selection(request, decision)`.  
- Version constants: request/response/scoring contracts are pinned to `1.0.0`.  


## Contract versions

- Explain request DTO version: `1.0.0`
- Explain response envelope version: `1.0.0`
- Explain contract version marker (`explain_contract_version`): `1.0.0`
- Referenced backend scoring contract: `1.0.0`
- Profile schema version (from decision artifact): `1.0.0`

SemVer policy:

- breaking envelope or semantic changes require `MAJOR`;
- additive optional fields require `MINOR`;
- fixes without public semantic changes require `PATCH`.

## Request schema

```json
{
  "request_version": "1.0.0",
  "response_version": "1.0.0",
  "decision_id": "backend-selection-decision-001",
  "include_rejected_candidates": true
}
```

### Fields

- `request_version` (string, required): request DTO version marker.
- `response_version` (string, required): expected response DTO version marker.
- `decision_id` (string, required): identifier of persisted scoring decision artifact.
- `include_rejected_candidates` (boolean, required): include ineligible candidates in `candidate_scores` when true.

## Response schema

```json
{
  "explain_contract_version": "1.0.0",
  "request_version": "1.0.0",
  "response_version": "1.0.0",
  "scoring_contract_version": "1.0.0",
  "profile_schema_version": "1.0.0",
  "profile_version": "1.0.0",
  "decision_id": "backend-selection-decision-001",
  "selected_backend_id": "sim:cpu-a",
  "tie_break_trace": ["score-desc"],
  "candidate_scores": [
    {
      "backend_id": "sim:cpu-a",
      "score_millis": 942,
      "eligible": true,
      "ineligibility_reason": null,
      "feature_contributions": [
        {"feature": "queue_length", "contribution_millis": 197}
      ]
    }
  ],
  "factor_contributions": [
    {
      "backend_id": "sim:cpu-a",
      "factor": "queue_length",
      "contribution_millis": 197
    }
  ],
  "confidence": {
    "score_margin_millis": 3,
    "selected_score_millis": 942,
    "runner_up_score_millis": 939,
    "confidence": 0.0031847133757961785
  }
}
```

### Fields

- `explain_contract_version` (string, required): explain envelope version marker.
- `request_version` (string, required): echoed request version.
- `response_version` (string, required): echoed response target version.
- `scoring_contract_version` (string, required): version of source scoring artifact.
- `profile_schema_version` (string, required): scoring profile schema version.
- `profile_version` (string, required): concrete profile version used for scoring.
- `decision_id` (string, required): stable source decision identifier.
- `selected_backend_id` (string|null, required): winning backend or `null` when no eligible candidate exists.
- `tie_break_trace` (array<string>, required): deterministic tie-break trace.
- `candidate_scores` (array<object>, required): per-candidate score snapshot.
- `factor_contributions` (array<object>, required): flattened ordered factor contributions.
- `confidence` (object, required): confidence metadata from score margin.

## Runtime semantics (фиксируем текущее поведение)

1. Confidence computes only over **eligible** candidates.
2. `selected_score_millis = 0` yields `confidence = 0.0`.
3. If `include_rejected_candidates=false`, rejected candidates are removed from:
   - `candidate_scores`,
   - and therefore from `factor_contributions` as well.
4. `factor_contributions` are sorted deterministically by:
   - `backend_id` (asc), then
   - `factor` (asc).
5. `tie_break_trace` is copied from the scoring artifact (not recomputed by explain layer).

## Determinism and compatibility gate

Contract stability is enforced by fixture-based tests:

- `src/rust/crates/resource-manager/tests/explain_backend_selection_contract.rs`
- `src/rust/crates/resource-manager/tests/fixtures/explain_contracts/backend_selection_explain_v1_0_0.json`
- `src/rust/crates/resource-manager/tests/deterministic_replay_gate.rs`

The suite guards:

1. exact response shape/value stability against golden fixture,
2. deterministic replay for identical decision artifacts,
3. explicit pinned version markers.

## Known gaps / what is missing

Чтобы зафиксировать состояние системы, ниже список пробелов между текущей реализацией и целевой архитектурной картиной (`docs/architecture/*`):

1. **Transport-level contract binding is under-specified**
   - Эта страница описывает domain DTO, но не фиксирует wire-level endpoint contract (HTTP/gRPC mapping, status codes, error envelope) для `/explain/backend-selection`.

2. **Error model alignment is not fully specified for explain path**
   - Не описано поведение для cases вроде `decision_id not found`, version mismatch, corrupted artifact; отсутствует явная ссылка на mapping в error-model/error-mapping для этого endpoint.

3. **Observability contract for explain requests is missing**
   - Нет фиксированного набора span/event names, metrics и audit fields именно для explain-вызовов.

4. **Security and access-control requirements are not fixed in this API page**
   - Не закреплены authn/authz, tenancy boundaries и redaction policy для explain payloads.

5. **Cross-component explainability linkage remains partial**
   - В архитектуре есть TODO по explainability в HWE/GNN/Neuro-symbolic слоях; для backend-selection explain нет единого end-to-end trace contract между compile intent → decision artifact → backend invocation.

## Recommended next documentation steps

1. Add transport binding subsection here (or separate page) with canonical wire schema + errors.
2. Cross-link to `docs/reference/error-model.md` + `docs/reference/error-mapping.md` with endpoint-specific cases.
3. Define explain observability mini-contract (trace/span/metrics/audit keys).
4. Add explicit security section (auth scopes, tenant isolation, sensitive fields policy).
5. Add integration test matrix for negative scenarios (`missing decision`, `bad versions`, `no eligible backend`).
