# ADR 0012 — Phase-4 explainability API contract v1

- **Status**: Accepted
- **Date**: 2026-04-28
- **Deciders**: Eigen OS maintainers
- **Supersedes / Related**: RFC 0024, ADR 0011

## Context

Phase-4 introduces intelligent-runtime decisioning that requires stable explainability APIs for users, operators, and forensic workflows. RFC 0024 is implemented and defines deterministic explain envelopes, lineage structure, and role-based detail levels.

## Decision

1. Adopt explainability API contract baseline `1.0.0`.
2. Require mandatory explain envelope markers in all explain responses:
   - `explain_contract_version`
   - `policy_version`
   - `scoring_contract_version` (when scoring applies)
3. Lock v1 explainability depth model:
   - `L1_USER`
   - `L2_ADMIN`
   - `L3_FORENSIC`
4. Require deterministic rationale ordering and stable envelope structure for `/explain/backend-selection` and `/explain/execution`.
5. Govern explainability contract evolution with SemVer:
   - incompatible envelope/field semantic change => `MAJOR`
   - additive optional rationale metadata => `MINOR`
   - documentation/bug fixes with no public semantic changes => `PATCH`

## Consequences

### Positive

- Consumers can parse explain responses with stable compatibility guarantees.
- Cross-surface correlation (policy/scoring/explain) is auditable through explicit versions.
- Incident response and compliance reporting gain deterministic explain artifacts.

### Trade-offs

- Redaction-level guarantees require ongoing security and schema review.
- Additional envelope fields increase governance and conformance test scope.

## Evidence package

- RFC: `rfcs/0024-phase4-explainability-api-contract-v1.md`
- Implementation:
  - `src/services/system-api/src/explain_api.py`
  - `src/services/system-api/tests/test_explain_api_contract.py`
  - `src/services/system-api/tests/test_explain_redaction_levels.py`

## Rollout / governance

- This ADR is the normative implementation record for Phase-4 explainability contract closure.
- Any breaking explainability change requires synchronized RFC+ADR update and MAJOR planning before release approval.
- Release notes for explainability-affecting PRs must include version impact, compatibility, and migration notes.
