# RFC 0024: Phase-4 Explainability API Contract v1

- **Status**: Implemented
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-28
- **Accepted on**: 2026-04-28
- **Implemented on**: 2026-04-28
- **Target Milestone**: Phase 4
- **Tracking Issue**: P4-08 (docs/development/phase-4-issue-pack.md)
- **Replaces / Related**: docs/development/phase-4-intelligent-runtime.md, RFC 0023, RFC 0025

## Summary

This RFC defines stable, versioned explainability API envelopes for intelligent runtime decisions via:

- `/explain/backend-selection`
- `/explain/execution`

The contract standardizes rationale structure, lineage fields, and error envelopes for deterministic diagnostics and audits.

## Motivation

As runtime decisions become policy-driven and score-based, users and operators need clear, structured explanations. Without a stable explainability API contract, tooling and governance cannot reliably consume decision context.

## Goals

- Define stable explainability envelopes with explicit version markers.
- Expose decision lineage and factor contributions.
- Align error model with existing public API conventions.
- Support role-based detail levels without breaking schema compatibility.

## Non-Goals

- Designing UI experiences for explainability output.
- Exposing raw internal state that violates security boundaries.
- Replacing logs/traces as primary ops telemetry.

## Guide-level Explanation

A client can request why backend `X` was selected, or why execution followed a particular branch (fallback/retry/queue strategy). The API returns a deterministic rationale envelope tied to decision artifacts and policy versions.

## Reference-level Design

### Common envelope (v1)

- `explain_contract_version: "1.0.0"`
- `decision_id`
- `decision_timestamp`
- `policy_version`
- `scoring_contract_version` (if applicable)
- `rationale[]` (ordered factors)
- `lineage[]` (decision steps)
- `redaction_level`

### Endpoint-specific payloads

- `/explain/backend-selection`:
  - candidate scores summary,
  - selected backend reason,
  - tie-break explanation.

- `/explain/execution`:
  - policy branch selection,
  - fallback/retry reasons,
  - timing annotations.

### Explainability levels

The API supports exactly three levels:

- `L1_USER`: human-readable summary,
- `L2_ADMIN`: structured rationale,
- `L3_FORENSIC`: full trace.

`L1_USER` required fields: `selected_backend`, `decision_summary`, `top_factors`, `rejected_backends`, `confidence`, `expected_latency`, `expected_fidelity`, `expected_cost_band`.

`L2_ADMIN`/`L3_FORENSIC` required fields: `policy_version`, `feature_snapshot`, `candidate_rankings`, `score_breakdown`, `constraint_rejections`, `fallbacks_used`, `source_freshness`, `decision_hash`.

`L3_FORENSIC` responses should be exportable as JSON, event-log records, and trace-span attributes.

### Error model

- `EXPLAIN_INVALID_REQUEST`
- `EXPLAIN_DECISION_NOT_FOUND`
- `EXPLAIN_REDACTION_FORBIDDEN`

## Interfaces / APIs

- Public explanation API endpoints.
- CLI integration targets (`eigen explain ...`) in subsequent implementation issues.

## Data Models

- `ExplainResponseEnvelope`
- `RationaleFactor`
- `DecisionLineageEntry`

All include explicit version markers and stable ordering constraints.

## Security and Privacy

- Role-based response shaping controls redacted fields.
- No secrets or unsafe backend internals in user-scoped responses.

## Observability

Required metrics:

- `explain_requests_total`
- `explain_latency_ms`
- `explain_errors_total`
- `explain_redaction_applied_total`

## Performance

- Explain SLO targets:
  - `L1_USER p95 < 100ms`
  - `L2_ADMIN p95 < 200ms`
  - `L3_FORENSIC p95 < 500ms`
- Explain endpoints should use persisted decision artifacts when possible to avoid recomputation.

If forensic payload size is too large, API may return immediate summary plus async export link/job id.

## Availability and degradation behavior

- Explain API availability target: `99.5%`.
- If explain service is degraded/unavailable, scheduling path remains available via cached explanation, deferred explanation generation, or degraded-but-safe mode.

## Benchmarking/Test Plan

- Contract fixtures for both explain endpoints.
- Deterministic ordering tests for `rationale` and `lineage` arrays.
- Negative tests for missing decision and forbidden redaction levels.

## Implementation / Migration

1. Define and publish OpenAPI/proto schemas for explain endpoints.
2. Implement artifact lookup + envelope mapper.
3. Add fixture-based compatibility gate.
4. Integrate role-based redaction policy.

Migration notes:

- New API surface; existing clients unaffected unless they opt in.

## Compatibility and Versioning

- **Version impact:** New contract surface with `1.0.0` baseline proposed.
- **Compatibility:** Additive API introduction.
- **Migration notes:** Consumers should pin `explain_contract_version` and handle optional additive fields.

## Considered Alternatives

- Unstructured free-text explanations only: rejected due to weak machine consumption.
- Single merged endpoint for all explain use-cases: rejected to keep schemas focused and evolvable.

## Open Questions

- Final redaction-level policy rules for tenant-specific visibility controls.
