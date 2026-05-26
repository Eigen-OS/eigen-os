# P9C-03 — Plugin-Only Advanced Scheduling Boundary Extraction

## Status

- **Issue:** #439
- **Phase:** 9C
- **Type:** Architecture Boundary / Pluginization
- **Contract baseline:** `rfcs/0048-phase9c-multitenant-plugin-boundary-contract-v1.md`

## Scope Lock

This work item formalizes Stage-C ownership boundaries for scheduling behavior:

- **Core-owned (mandatory):** deterministic weighted fair queueing, quota admission, starvation prevention.
- **Plugin-owned (optional):** batch dispatch, preemption strategies, backfill, drift-aware scheduling heuristics.

The core scheduler MUST remain fully deterministic and functional when no policy plugins are available.

## Versioning & Compatibility

- **Version impact:** MINOR
- **Compatibility matrix artifact:** `policy_capability_matrix.v1` introduced as `1.1.0`.
- **Breaking marker:** false
- **Migration notes:** None

Rationale:

1. This introduces a new versioned compatibility artifact and does not remove existing stable interfaces.
2. Ownership declarations are additive and align with RFC 0048 Stage-C contract semantics.

## Compatibility Matrix (Core vs Plugin Ownership)

Authoritative fixture:

- `docs/development/fixtures/phase9c/policy_capability_matrix_v1_1_0.json`

Declared capabilities:

- **Core:** `deterministic_weighted_fair_queueing`, `tenant_project_quota_admission`, `starvation_prevention`
- **Plugin:** `batch_dispatch`, `preemption`, `backfill`, `drift_aware_scoring`

## Deterministic Fallback Contract

When policy plugins are disabled, missing, timed out, or malformed:

- kernel lifecycle remains healthy;
- core fair scheduler continues dispatch deterministically;
- fallback pathways emit stable reason-code taxonomy per Stage-C contract.

## Reference Policy Plugin Requirement

Per `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md`, every extracted surface must have at least one reference plugin implementation.

For implementation sequencing, this boundary artifact unblocks:

1. policy plugin scaffolds (`plugin scaffold policy`),
2. policy plugin conformance gates (`plugin validate policy`),
3. failure-isolation drill fixtures tied to fallback reason-code schema.

## Validation Expectations

Required validation for closure:

- scheduler deterministic fixture evidence with plugins disabled;
- plugin failure-isolation drills for timeout/crash/malformed output;
- compatibility matrix fixture tests enforced in fail-closed CI contract drift checks.
