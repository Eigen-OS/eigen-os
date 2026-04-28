# RFC 0023: Phase-4 Backend Selection Scoring Contract v1

- **Status**: Draft
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-28
- **Target Milestone**: Phase 4
- **Tracking Issue**: P4-08 (docs/development/phase-4-issue-pack.md)
- **Replaces / Related**: docs/development/phase-4-intelligent-runtime.md, docs/roadmap.md

## Summary

This RFC proposes a deterministic scoring contract for backend selection in the Phase-4 intelligent runtime. It defines input feature families, score vector semantics, tie-break rules, and versioned scoring profiles so runtime decisions are reproducible and auditable.

## Motivation

Backend selection currently depends on static heuristics and limited transparency. A versioned scoring contract is needed to:

- improve decision quality across workloads,
- preserve deterministic replay for incident analysis,
- make optimization behavior explainable to users and operators.

## Goals

- Define a stable scoring envelope and version markers.
- Guarantee deterministic score outputs for identical normalized inputs.
- Define deterministic tie-break rules.
- Align scoring artifacts with explainability APIs.

## Non-Goals

- Proprietary/black-box model inference.
- Distributed multi-cluster scoring federation.
- Automatic policy updates without explicit version change.

## Guide-level Explanation

The runtime computes a score per candidate backend from a normalized feature vector (workload, backend, runtime context). The highest valid score wins. If scores tie, deterministic tie-break rules apply (policy priority → backend capability rank → lexical backend id).

## Reference-level Design

### Scoring output envelope (v1)

- `scoring_contract_version: "1.0.0"`
- `profile_version: "1.0.0"`
- `decision_id`
- `candidates[]` with:
  - `backend_id`
  - `score`
  - `feature_contributions[]`
  - `eligible` + `ineligibility_reason` (optional)
- `selected_backend_id`
- `tie_break_trace[]`

### Determinism requirements

- Normalization pipeline must be pure and stable for identical inputs.
- Candidate iteration order must be canonicalized before scoring.
- Floating-point handling must follow fixed rounding strategy for persisted outputs.

### Error model

- `SCORING_INPUT_INVALID`
- `SCORING_PROFILE_UNKNOWN`
- `SCORING_NO_ELIGIBLE_BACKEND`

## Interfaces / APIs

- Runtime-internal scoring module API.
- Output feeds `/explain/backend-selection` contract (RFC 0024).

## Data Models

- `ScoringProfile` schema (weights, feature list, normalization versions).
- `ScoringDecisionArtifact` persisted with explicit version fields.

## Security and Privacy

- Scoring artifacts must not include secrets or tenant-isolating identifiers beyond approved metadata.
- Access to full feature contributions may be role-scoped.

## Observability

Required metrics:

- `runtime_scoring_requests_total`
- `runtime_scoring_latency_ms`
- `runtime_scoring_failures_total`
- `runtime_scoring_fallback_total`

## Performance

- Scoring complexity target: `O(num_candidates * num_features)`.
- p95 scoring latency budget to be finalized during acceptance.

## Benchmarking/Test Plan

- Determinism replay suite for scoring artifacts.
- Golden fixtures for tie-break paths.
- Negative tests for invalid profile and empty eligible candidate set.

## Implementation / Migration

1. Implement profile schema + validator.
2. Implement deterministic feature normalization.
3. Implement scorer + tie-break trace output.
4. Wire observability and fixtures.

Migration notes:

- Initial rollout ships with one default profile (`balanced@1.0.0`).
- Future incompatible scoring semantics require `2.0.0` contract.

## Compatibility and Versioning

- **Version impact:** New stable contract surface (`1.0.0` baseline proposed).
- **Compatibility:** Additive to existing scheduling flow.
- **Migration notes:** Consumers should rely only on versioned fields in persisted artifacts.

## Considered Alternatives

- Rule-only selection without scoring: rejected due to poor extensibility.
- Black-box ML model scoring: rejected due to explainability and determinism requirements.

## Open Questions

- Final v1 feature allowlist is pending maintainer decision.
- Precision/rounding policy for floating-point contributions is pending.
