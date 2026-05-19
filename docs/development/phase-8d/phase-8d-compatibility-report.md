# Phase-8D Compatibility Report

- **Status:** Draft (execution in progress)
- **Date:** 2026-05-19
- **Milestone:** M8D
- **Version:** 0.1.0

## Scope

This report tracks compatibility impact for hardware externalization components introduced or modified in Phase-8D:

- QDriver API v1.0 and official adapter conformance semantics,
- provider support matrix (simulator, IBM Quantum, AWS Braket),
- system-api REST parity and compatibility matrix publication,
- developer surface skeleton contracts (dashboard, VS Code, Jupyter),
- operator rollback and incident governance references.

## Compatibility policy baseline

Compatibility decisions in this report follow:
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`
- accepted governance baselines from Phase-8A/8B/8C,
- planned Phase-8D RFC package (0044, 0045, 0046) and mirrored ADRs (0030, 0031, 0032).

## Current impact classification (planning)

| Surface | Impact class | Notes |
| --- | --- | --- |
| QDriver capability descriptor schema | MINOR (expected) | additive capability flags and error-class normalization |
| Driver adapter lifecycle semantics | MINOR (expected) | additive conformance assertions, fail-closed unsupported paths |
| System API REST projection for provider metadata | MINOR (expected) | additive fields for capability/tolerance visibility |
| Compatibility matrix artifact | MINOR (expected) | new versioned artifact, no breaking change expected |
| Existing CLI + baseline submit/watch/results flow | PATCH (expected) | unchanged user flow, enriched metadata only |

## Backward-compatibility strategy

1. New fields must be additive with deterministic defaults.
2. Provider-specific capabilities must be represented as optional flags with clear fallback behavior.
3. Unsupported provider operations must fail with stable, documented error classes.
4. Deprecated adapter behavior must observe 2-minor-or-90-day support policy.
5. Breaking changes discovered during implementation require RFC revision and migration notes before release.

## Migration notes (draft)

- No migration is required for existing simulator-only workflows at planning stage.
- If provider capability naming changes or default routing policy changes, publish migration notes before release candidate cut.

## Verification artifacts required before final sign-off

- QDriver conformance suite evidence for simulator/IBM/AWS.
- Cross-provider tolerance and parity report for canonical workload set.
- REST parity check evidence and updated compatibility matrix artifact.
- Runbook drill evidence and rollback safety check logs.

## Finalization criteria

This report can be marked **Accepted** only when:
- RFC 0044/0045/0046 and ADR 0030/0031/0032 are accepted and linked,
- CI drift and parity gates pass for the final externalized contract surfaces,
- migration notes (if required) are published and linked in release notes.

## P8D-04 parity tolerance policy artifact

- Versioned tolerance policy fixture: `docs/development/fixtures/phase8d/provider_tolerance_policy_v1.json` (`policy_version: 1.0.0`).
- Release gate expectation: cross-provider comparator must fail closed when result-shape, latency-band, or noise-delta limits are exceeded.
- Official targets covered by this policy: simulator, IBM, AWS.
