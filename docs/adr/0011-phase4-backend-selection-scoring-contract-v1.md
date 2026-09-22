# ADR 0011 — Phase-4 backend selection scoring contract v1

- **Status**: Accepted
- **Date**: 2026-04-28
- **Deciders**: Eigen OS maintainers
- **Supersedes / Related**: RFC 0023, ADR 0007

## Context

Phase-4 intelligent runtime requires deterministic backend selection semantics with explicit version markers and replay-safe artifacts. RFC 0023 is implemented and defines scoring input allowlists, tie-break behavior, and scoring profile governance.

## Decision

1. Adopt backend scoring contract baseline `1.0.0` for Phase-4 runtime decisions.
2. Require explicit version markers in every scoring decision artifact:
   - `scoring_contract_version`
   - `profile_version`
3. Freeze v1 deterministic decision semantics:
   - same normalized input + same profile version MUST yield identical candidate ordering and selected backend;
   - tie-break order is fixed and auditable (`policy priority` → `backend capability rank` → lexical `backend_id`).
4. Enforce feature governance constraints:
   - only allowlisted feature families can participate in default scoring;
   - disallowed opaque/private/non-auditable features are rejected;
   - missing features use documented fallback values with explanation annotations.
5. Govern scoring evolution with SemVer:
   - incompatible score semantics or tie-break behavior => `MAJOR`
   - additive optional explainability metadata => `MINOR`
   - implementation-only fixes with no semantic drift => `PATCH`

## Consequences

### Positive

- Backend selection becomes reproducible and explainable for audits.
- Compatibility reporting can rely on explicit artifact version markers.
- Runtime quality gates can detect contract drift via deterministic replay.

### Trade-offs

- Feature onboarding requires stricter governance and documentation overhead.
- Policy/scoring experiments must ship with explicit versioning discipline.

## Evidence package

- RFC: `rfcs/0023-phase4-backend-selection-scoring-contract-v1.md`
- Implementation:
  - `src/rust/crates/resource-manager/src/scoring.rs`
  - `src/rust/crates/resource-manager/src/scoring_profile.rs`
  - `src/rust/crates/resource-manager/tests/scoring_contract_tests.rs`

## Rollout / governance

- This ADR is the normative implementation record for Phase-4 backend scoring contract closure.
- Any incompatible scoring semantic change requires synchronized RFC+ADR update and MAJOR version planning.
- Phase-4 release sign-off depends on this ADR plus compatibility report and release-readiness checklist.
