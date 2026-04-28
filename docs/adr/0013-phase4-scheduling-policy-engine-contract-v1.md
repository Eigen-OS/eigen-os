# ADR 0013 — Phase-4 scheduling policy engine contract v1

- **Status**: Accepted
- **Date**: 2026-04-28
- **Deciders**: Eigen OS maintainers
- **Supersedes / Related**: RFC 0025, ADR 0011, ADR 0012

## Context

The Phase-4 intelligent runtime requires deterministic policy resolution over latency/throughput/cost objectives with explicit precedence and fallback semantics. RFC 0025 is implemented and defines policy bundle schema governance and resolution determinism.

## Decision

1. Adopt scheduling policy engine contract baseline `1.0.0`.
2. Require mandatory policy decision markers in every policy artifact:
   - `policy_contract_version`
   - `policy_bundle_id`
   - `policy_bundle_version`
3. Freeze v1 policy resolution determinism:
   - canonical precedence ladder and override order are fixed;
   - same input + same policy version + same feature snapshot MUST produce same decision.
4. Require explicit fallback signaling (`fallback_applied`, `fallback_reason`) when constraints cannot be satisfied.
5. Govern policy-engine evolution with SemVer:
   - incompatible precedence or fallback semantic changes => `MAJOR`
   - additive optional policy metadata => `MINOR`
   - bug fixes without public policy-semantic changes => `PATCH`

## Consequences

### Positive

- Policy outcomes are reproducible and explainable across releases.
- Release compatibility reports can lock policy schema and semantics cleanly.
- Operational rollback becomes safer via explicit policy bundle/version pinning.

### Trade-offs

- Policy rollout requires stricter schema governance and version-management process.
- More deterministic constraints can slow exploratory policy experimentation.

## Evidence package

- RFC: `rfcs/0025-phase4-scheduling-policy-engine-contract-v1.md`
- Implementation:
  - `src/rust/crates/resource-manager/src/policy_engine.rs`
  - `src/rust/crates/resource-manager/src/policy_bundle.rs`
  - `src/rust/crates/resource-manager/tests/policy_contract_tests.rs`

## Rollout / governance

- This ADR is the normative implementation record for Phase-4 scheduling policy contract closure.
- Any incompatible policy-resolution change requires synchronized RFC+ADR updates and MAJOR planning.
- Phase-4 release closure requires this ADR plus signed compatibility and readiness package.
