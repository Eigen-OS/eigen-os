# ADR 0010 — Phase-3 comparison methodology and history contract v1

- **Status**: Accepted
- **Date**: 2026-04-27
- **Deciders**: Eigen OS maintainers
- **Supersedes / Related**: RFC 0022, ADR 0008, ADR 0009

## Context

Phase-3 requires reliable run-to-run comparison and trend analysis semantics. RFC 0022 is implemented and defines deterministic comparison deltas/regression signaling, methodology metadata requirements, and stable history pagination/ordering guarantees.

## Decision

1. Adopt comparison/history contract baseline version `1.0.0` for Phase-3.
2. Require explicit version markers in persisted and returned artifacts:
   - `comparison_version`
   - `methodology_version`
   - `history_contract_version`
3. Freeze v1 deterministic semantics:
   - Compare outputs are deterministic for identical inputs and thresholds.
   - History ordering is stable: `created_at DESC, run_id ASC`.
   - History pagination is deterministic via cursor token (`page_token`).
4. Require structured compare/history validation errors with stable fields:
   - `code`
   - `field`
   - `message`
5. Govern evolution with SemVer:
   - Incompatible compare semantics, ordering, or pagination behavior => `MAJOR`
   - Backward-compatible optional metadata fields => `MINOR`
   - Non-semantic fixes only => `PATCH`

## Consequences

### Positive

- Regression decisions become reproducible and auditable across releases.
- History clients can rely on stable ordering and pagination guarantees.
- Methodology metadata and version markers enable formal compatibility reporting.

### Trade-offs

- Analytics contract changes require explicit compatibility/migration handling.
- Teams must maintain deterministic behavior under concurrent data growth.

## Evidence package

- RFC: `rfcs/0022-phase3-compare-history-contract-v1.md`
- Implementation:
  - `src/services/benchmark-service/src/benchmark_service/compare.py`
  - `src/services/benchmark-service/src/benchmark_service/history.py`
  - `src/services/benchmark-service/tests/test_compare_contract.py`
  - `src/services/benchmark-service/tests/test_history_contract.py`

## Rollout / governance

- This ADR is the normative implementation record for P3-04/P3-05/P3-09 outcomes.
- Phase-3 release readiness requires compare/history compatibility sign-off in `docs/development/phase-3-compatibility-report.md`.
- Any incompatible semantics update requires synchronized RFC+ADR updates and explicit migration notes before release gate approval.
