RFC 0041: Phase-9A Policy Engine v2 Contract

- **Status**: Accepted
- **Authors**: Architecture WG, Runtime/Core
- **Created**: 2026-05-19
- **Target Milestone**: Phase 9A
- **Tracking Issue**: #941
- **Replaces / Related**: RFC 0025, ADR 0013, ADR 0018

## Summary

Define Policy Engine v2 contract with deterministic rule-evaluation traces, versioned policy bundles, and fail-closed authorization decisions for runtime scheduling and data-access paths.

## Motivation

Phase-8 contracts introduced versioning and observability guardrails, but policy evaluation behavior is still fragmented across schedulers and plugin-runtime surfaces.

## Goals

- Standardize policy bundle format and lifecycle.
- Enforce deterministic decision reason codes.
- Provide trace-linked auditability for every allow/deny decision.

## Non-Goals

- Replacing existing scheduler scoring logic.
- Introducing a new authentication provider.

## Guide-level Explanation

Operators publish signed policy bundles. Runtime components resolve one active bundle revision and evaluate requests through a shared Policy Engine API. Decisions include `reason_code`, `policy_revision`, and trace correlation metadata.

## Reference-level Design

- Policy bundles are immutable, semver-versioned artifacts.
- Evaluation API is pure and side-effect free.
- Deny-by-default semantics apply when bundles are missing or invalid.

## Interfaces / APIs

- `EvaluatePolicy(subject, action, resource, context) -> Decision`
- `Decision` fields: `allowed`, `reason_code`, `policy_revision`, `trace_id`

## Data Models

- `policy_bundle.json` schema v2 with explicit `rules[]`, `constraints[]`, and `metadata`.

## Security and Privacy

- Bundle signatures are mandatory for production.
- Decision logs must avoid direct PII payloads.

## Observability

- Metrics: evaluation latency, deny rate by reason code, stale-bundle count.
- Traces: one span per evaluation with bundle revision tag.

## Performance

- p95 evaluation latency target: <= 5 ms under 10k eval/sec/node.

## Testing Plan

- Determinism fixtures for repeat decision outputs.
- Compatibility fixtures for schema migration v1 -> v2.

## Implementation / Migration

1. Ship bundle schema v2 validator.
2. Integrate shared evaluation library in scheduler and plugin runtime.
3. Enable fail-closed gate in CI and canaries.

## Considered Alternatives

- Per-service policy implementations (rejected: drift risk).
- Best-effort allow on bundle failure (rejected: unsafe default).

## Open Questions

- Whether emergency override should be global or namespace-scoped.
