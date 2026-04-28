# Explain API — Backend Selection (`/explain/backend-selection`)

This page defines the stable Phase-4 backend-selection explain contract.

## Contract versions

- Explain request DTO version: `1.0.0`
- Explain response envelope version: `1.0.0`
- Explain contract version marker (`explain_contract_version`): `1.0.0`
- Referenced backend scoring contract: `1.0.0`

Versioning follows the Phase-4 SemVer policy:

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

## Determinism and compatibility gate

The contract is enforced by fixture-based tests:

- `src/rust/crates/resource-manager/tests/explain_backend_selection_contract.rs`
- `src/rust/crates/resource-manager/tests/fixtures/explain_contracts/backend_selection_explain_v1_0_0.json`

The test suite ensures:

1. exact response shape/ordering remains stable against golden fixture,
2. identical decision artifacts produce identical explain responses,
3. explicit version markers remain present and pinned.
