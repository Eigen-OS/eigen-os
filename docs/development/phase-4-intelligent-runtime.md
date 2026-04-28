# Phase 4 — Intelligent Runtime Plan

## Status

- **Phase**: 4 (Post-MVP)
- **Planning status**: Active (RFC package drafted)
- **Started on**: 2026-04-28
- **Last updated**: 2026-04-28
- **Previous phase closure**: [`phase-3-release-readiness-checklist.md`](phase-3-release-readiness-checklist.md)
- **Execution backlog**: [`phase-4-issue-pack.md`](phase-4-issue-pack.md)
- **RFC/ADR coverage check**: [`phase-4-rfc-adr-gap-analysis.md`](phase-4-rfc-adr-gap-analysis.md)

## Goal

Deliver an explainable, deterministic, and policy-configurable intelligent runtime layer that improves backend selection and scheduling outcomes without introducing opaque decision behavior.

## Scope (in)

1. **Backend scoring module**
   - Deterministic feature extraction from job/runtime/backend descriptors.
   - Weighted scoring model with explicit versioned scoring profile.
   - Explainability payloads that show factor contributions.

2. **Policy-configurable scheduling engine**
   - Policy bundles (`latency`, `throughput`, `cost`, `balanced`) with versioned defaults.
   - Deterministic tie-break and fallback rules.
   - Safe policy overrides with schema validation and guardrails.

3. **Explanation API surface (public + operator)**
   - `/explain/backend-selection`
   - `/explain/execution`
   - Stable explanation envelope with traceable rationale fields.

4. **Runtime intelligence observability**
   - Metrics for score computation latency, policy decisions, fallback frequency, and explain endpoint usage.
   - Structured logs and traces for decision lineage.
   - Dashboard + alert set for decision drift and scoring failures.

5. **Eigen-Lang integrations**
   - Compile-time diagnostics for unsupported or risky runtime targets.
   - Runtime-aware hints surfaced in compile output metadata.
   - Execution annotations carrying backend rationale identifiers.

## Scope (out)

- Black-box or proprietary model inference pipelines.
- Autonomous optimizer actions that cannot be traced to deterministic inputs.
- Distributed multi-node policy federation (Phase-5+).

## Exit criteria (Definition of Done)

1. Backend scoring contract is stable, versioned, and deterministic for identical inputs.
2. Policy engine enforces versioned policy bundles and deterministic conflict resolution.
3. Explanation APIs return structured and auditable rationale for backend and execution decisions.
4. Eigen-Lang emits runtime-intelligence metadata and diagnostics in a compatibility-tested format.
5. Observability pack covers score latency, fallback rates, explain endpoint errors, and policy drift signals.
6. Phase-4 RFC package and issue pack are published and cross-linked.

## Versioning constraints

- Scoring profile schema, policy bundle schema, and explanation API envelopes are SemVer-governed contracts.
- Breaking changes to decision semantics, explanation fields, or policy resolution rules require `MAJOR`.
- Backward-compatible optional metadata additions use `MINOR`.
- `PATCH` releases must not alter public decision or explanation semantics.
- Every decision artifact includes explicit contract-version markers.

## API/CLI targets

- API:
  - `/explain/backend-selection`
  - `/explain/execution`
- CLI (planned):
  - `eigen explain backend-selection`
  - `eigen explain execution`

## Dependencies and prerequisites

- Phase-3 runtime observability and contract baselines.
- Stable scheduler and execution metadata from Phase-2/Phase-3.
- Conformance and fixture harness for explanation outputs.

## Deliverables map

1. Planning + backlog: this document + [`phase-4-issue-pack.md`](phase-4-issue-pack.md).
2. Governance package: [`phase-4-rfc-adr-gap-analysis.md`](phase-4-rfc-adr-gap-analysis.md) + RFCs `0023/0024/0025` in `rfcs/`.
3. Implementation slices: scoring module, policy engine, explanation APIs, Eigen-Lang hints.
4. Release closure package (to be completed during execution):
   - `phase-4-release-readiness-checklist.md`
   - `phase-4-compatibility-report.md`

## Data required to finalize Phase-4 defaults

The following decisions are still required from maintainers/product owners before implementation can be finalized:

1. **Policy priority order** between `latency`, `throughput`, `cost`, and `balanced` for shared cluster modes.
2. **Allowed feature set** for backend scoring v1 (resource utilization inputs, calibration history, queue-depth limits).
3. **SLO thresholds** for explain endpoint latency and decision-fallback alerting.
4. **User-facing explainability granularity** (operator-only factors vs end-user visible factors).
