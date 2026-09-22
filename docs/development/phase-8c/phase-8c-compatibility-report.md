# Phase-8C Compatibility Report

- **Status:** Accepted (milestone closure evidence recorded)
- **Date:** 2026-05-19
- **Milestone:** M8C
- **Version:** 1.0.0

## Scope

This report tracks compatibility impact for adaptive intelligence components introduced or modified in Phase-8C:

- Eigen-DPDA deterministic/model-assisted transition behavior,
- GNN optimizer evaluation/promotion lifecycle,
- continuous learning trigger/canary/rollback control-plane behavior,
- explainability/lineage metadata surfaces.

## Compatibility policy baseline

Compatibility decisions in this report follow:
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`
- accepted governance baselines: RFC 0035/0036/0040 with synchronized ADRs 0021/0022/0026.

## Current impact classification (implemented)

| Surface | Impact class | Notes |
| --- | --- | --- |
| Compiler transition metadata schema | MINOR (expected) | additive fields for decision provenance and fallback marker |
| Optimizer evaluation artifact schema | MINOR (expected) | additive metrics and lifecycle-state markers |
| Learning control-plane API/payloads | MINOR (confirmed) | additive trigger/promotion/rollback envelope remains backward-compatible |
| KB lineage indexes | MINOR (expected) | additive query dimensions |
| Existing CLI/system-api flows | PATCH (expected) | no mandatory user-facing breaking change planned |

## Backward-compatibility strategy

1. Additive schema fields must have deterministic defaults.
2. New policy controls must be optional and feature-flagged at introduction.
3. Deprecated fields/interfaces must observe the 2-minor-or-90-day support window.
4. Any breaking proposal discovered during implementation requires RFC revision before merge.

## Migration notes (draft)

- No immediate migration required for current planning artifacts.
- If MAJOR impact is introduced by accepted RFC semantics, publish migration notes and upgrade checklist before release cut.

## Verification artifacts required before final sign-off

- CI gate evidence for trigger/canary/rollback/reproducibility.
- Fixture diffs and compatibility matrix update.
- Release-note impact summary and rollout/rollback operator guidance.

## Finalization criteria

This report can be marked **Accepted** only when:
- accepted governance baselines (RFC 0035/0036/0040 + ADR 0021/0022/0026) are linked and unchanged,
- CI compatibility and drift gates pass for the updated KB decision-log and lineage-index schema,
- migration notes (if required) are published and linked.
