# RFC 0025: Phase-4 Scheduling Policy Engine Contract v1

- **Status**: Draft
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-28
- **Target Milestone**: Phase 4
- **Tracking Issue**: P4-08 (docs/development/phase-4-issue-pack.md)
- **Replaces / Related**: docs/development/phase-4-intelligent-runtime.md, RFC 0023

## Summary

This RFC introduces a versioned scheduling policy engine contract for Phase-4. It defines policy bundles, precedence rules, override behavior, and deterministic fallback semantics for runtime execution planning.

## Motivation

Runtime scheduling needs explicit policy governance to balance latency, throughput, cost, and reliability targets. Without a formal contract, policy behavior can drift and break compatibility expectations.

## Goals

- Define a stable policy bundle schema with versioning.
- Standardize deterministic policy precedence and override resolution.
- Define fallback behavior when policy constraints cannot be satisfied.
- Ensure policy outcomes are traceable in decision artifacts.

## Non-Goals

- Global cross-region policy federation.
- Automatic policy tuning from opaque telemetry loops.
- User-facing policy-authoring UI.

## Guide-level Explanation

The engine loads a versioned policy bundle and resolves an execution plan through deterministic rules. If constraints conflict, explicit precedence and fallback policies decide the final branch. Every step is recorded for explainability.

## Reference-level Design

### Policy contract envelope (v1)

- `policy_contract_version: "1.0.0"`
- `policy_bundle_id`
- `policy_bundle_version`
- `policy_mode` (`latency`, `throughput`, `cost`, `balanced`)
- `resolution_trace[]`
- `fallback_applied` + `fallback_reason` (optional)

### Deterministic resolution rules

1. Validate policy schema and required constraints.
2. Apply profile defaults.
3. Apply allowed overrides in canonical order.
4. Resolve conflicts using fixed precedence table.
5. Emit fallback branch if constraints unsatisfied.

### Error model

- `POLICY_BUNDLE_INVALID`
- `POLICY_MODE_UNSUPPORTED`
- `POLICY_RESOLUTION_FAILED`

## Interfaces / APIs

- Runtime scheduling engine API.
- Execution artifacts consumed by `/explain/execution` (RFC 0024).

## Data Models

- `PolicyBundle`
- `PolicyResolutionArtifact`
- `FallbackDescriptor`

## Security and Privacy

- Policy overrides must be authenticated/authorized.
- Unsafe override classes must be blocked by schema and policy guardrails.

## Observability

Required metrics:

- `policy_resolution_requests_total`
- `policy_resolution_latency_ms`
- `policy_resolution_failures_total`
- `policy_fallback_total`

## Performance

- Policy resolution target complexity: `O(num_constraints + num_overrides)`.
- Additional scheduling overhead should remain bounded by accepted latency budget.

## Benchmarking/Test Plan

- Fixture coverage for each policy mode.
- Conflict resolution determinism tests.
- Fallback path replay tests with stable outputs.

## Implementation / Migration

1. Publish policy bundle schema and validator.
2. Implement deterministic resolution engine.
3. Persist resolution artifacts with version markers.
4. Add observability and compatibility fixtures.

Migration notes:

- Existing scheduler behavior is mapped to default `balanced@1.0.0` policy profile.

## Compatibility and Versioning

- **Version impact:** New contract surface with `1.0.0` baseline proposed.
- **Compatibility:** Existing scheduling inputs continue with mapped defaults.
- **Migration notes:** Custom policy adopters must pin `policy_bundle_version` in deployment configs.

## Considered Alternatives

- Hardcoded scheduler modes only: rejected due to weak governance and portability.
- Fully dynamic policy scripts: rejected for determinism/security risks in v1.

## Open Questions

- Final precedence table across policy modes and overrides.
- Guardrail set for tenant-level policy overrides.
