# ADR 0024: Phase-8B QRTX Scheduling and Lifecycle Hardening Contract v1

- **Status**: Accepted
- **Date**: 2026-05-17
- **Decision owners**: Runtime/Core, Scheduler, Architecture/Governance
- **Supersedes / Related**: RFC 0038, ADR 0018, ADR 0019

## Context

Phase-8B closes the gap between the baseline QRTX runtime and production-grade scheduling behavior for research-scale workloads. RFC 0038 defines deterministic DAG resolution, priority/quota scheduling, topology/noise-aware dispatch fallback behavior, and idempotent lifecycle transitions.

## Decision

Adopt RFC 0038 as the operational baseline for QRTX scheduling and lifecycle hardening contract v1:

1. DAG dependency resolution must be deterministic and emit stable cycle, missing-edge, and invalid-node reason codes.
2. Priority and quota policy hooks must preserve deterministic tie-breaking, fairness, and starvation guardrails.
3. Topology/noise-aware dispatch must use stable telemetry inputs when available and deterministic fallback markers when telemetry is missing.
4. Submit, schedule, dispatch, retry, and cancel transitions must be idempotent and replay-safe.
5. Drift in lifecycle semantics, reason codes, or scheduler policy behavior is CI-gated and requires SemVer classification with migration policy compliance.

## Consequences

- Runtime scheduling decisions become reproducible under high-volume queue profiles.
- Operators and tests can diagnose scheduling/lifecycle failures through stable reason codes.
- Future scheduler extensions must preserve replay safety or ship as governed contract changes.

## Verification and evidence

- RFC source: `rfcs/0038-phase8b-qrtx-scheduling-and-lifecycle-hardening-contract-v1.md`
- Phase-8B fixture gate: `docs/development/fixtures/phase8b/ci_gate_bundle_v1.json`
- Gate entrypoint: `scripts/ci/check-phase8b-gates.sh`
- Phase-8B closure docs: gap analysis, readiness checklist, compatibility report, and exit evidence bundle
