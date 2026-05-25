# REST API: Explain Backend Selection (`POST /explain/backend-selection`)

**Purpose:** Explain why a given backend was selected for a quantum job. It returns decision rationale including candidate scores and contributions.

## 1. Implementation Status

- The *domain/service layer* exists (Rust) that builds the `ExplainBackendSelectionResponse` from a stored decision.

- Versioned DTOs exist (`ExplainBackendSelectionRequest/Response`, v1.0.0) with deterministic mapping logic (`explain_backend_selection` function).

- Golden-fixture and replay tests (`explain_backend_selection_contract.rs`) enforce response stability and schema.

**Note: No transport-level endpoint is yet defined**. The current code does not expose an HTTP/gRPC API for this explain functionality; it's only used internally in Rust tests.

## 2. Contract Versioning

- **Explain API request version:** `1.0.0`

- **Explain API response (envelope) version:** `1.0.0` (fields in payload)

- **Backend scoring contract version:** `1.0.0` (the decision artifact format)

- **Profile schema version:** `1.0.0` (the schema of the scoring profile)

Versioning is SemVer: breaking changes need MAJOR bump.

## 3. Request Schema

```json
{
  "request_version": "1.0.0",
  "response_version": "1.0.0",
  "decision_id": "backend-selection-decision-001",
  "include_rejected_candidates": true
}
```

- `request_version`: (string) API request version (must be "`1.0.0`").

- `response_version`: (string) Target response version (must be "`1.0.0`").

- `decision_id`: (string) Identifier of a stored backend selection decision.

- `include_rejected_candidates`: (boolean) If `true`, include ineligible candidates in the output lists; if `false`, omit them.

## 4. Response Schema

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
        // ... other feature contributions
      ]
    }
    // ... other candidates
  ],
  "factor_contributions": [
    {
      "backend_id": "sim:cpu-a",
      "factor": "queue_length",
      "contribution_millis": 197
    }
    // ... potentially multiple entries
  ],
  "confidence": {
    "score_margin_millis": 3,
    "selected_score_millis": 942,
    "runner_up_score_millis": 939,
    "confidence": 0.0031847133757961785
  }
}
```

- `explain_contract_version`: API response envelope version (1.0.0).

- `request_version` / `response_version`: Echoed from request, must both be "1.0.0".

- `scoring_contract_version`: Version of the referenced scoring decision (1.0.0).

- `profile_schema_version` / `profile_version`: Version of the scoring profile used.

- `decision_id`: The same ID from the request.

- `selected_backend_id`: The winning backend ID (or `null` if none eligible).

- `tie_break_trace`: Array of strings showing deterministic tie-break steps (copied from decision).

- `candidate_scores`: List of candidates with fields:

  - `backend_id`, `score_millis` (raw score),

  - `eligible`: boolean,

  - `ineligibility_reason`: null or string if not eligible,

  - `feature_contributions`: list of `{feature, contribution_millis}` entries that sum to the candidate’s score.

- `factor_contributions`: Flattened list of all feature contributions, sorted by `backend_id` and `factor`.

- `confidence`: Contains:

  - `score_margin_millis`, `selected_score_millis`, `runner_up_score_millis`, `confidence` (a float between 0 and 1).

## 5. Runtime Semantics

Based on current implementation:

- Confidence is computed only among *eligible* candidates (ineligible are ignored).

- If `selected_score_millis` is 0 (no selection), `confidence` is 0.0.

- If `include_rejected_candidates` is `false`, any `eligible: false` entries are omitted from both `candidate_scores` and `factor_contributions`.

- `factor_contributions` entries are sorted by `backend_id` (lexicographically), then `factor` (lexicographically).

- `tie_break_trace` is directly copied from the decision record; the explain API does not recompute it.

## 6. Observations and Gaps

- **Transport:** No HTTP or gRPC endpoint is defined. We need to decide on a transport (e.g. add `POST /explain/backend-selection`) and implement it.

- **Errors:** Not specified how errors are reported (e.g. decision ID not found, version mismatch, etc.). We should define error codes and mapping in the Error Model (e.g. a 404 NOT_FOUND for unknown `decision_id`).

- **Observability:** No fixed tracing or metrics contract for explain calls. We should define span names and events (for auditing usage).

- **Security:** No authN/authZ is specified. We should require the same token scopes as for other scheduler or QA APIs.

- **End-to-End Explainability:** There’s no integrated trace linking from job submission → scheduling decision → explain endpoint. We should plan how to propagate context/IDs for full auditing.

**Tasks to complete:**

1. **Define Endpoint:** Add a REST handler (or gRPC) for `POST /explain/backend-selection`. Map JSON to `ExplainBackendSelectionRequest` and call into Rust logic.

2. **Error Handling:** Specify HTTP status codes and error envelopes for cases like `NOT_FOUND`, `INVALID_ARGUMENT`, etc., and implement them.

3. **Metrics/Tracing:** Decide on telemetry keys (e.g. `explain.backend_selection.request`) and ensure instrumentation is in code.

4. **Security Policy:** Assign an auth scope (e.g. `jobs:explain`) and enforce it.

5. **Integrate with KB:** Optionally expose result storage or auditing of explain calls.
