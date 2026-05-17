# ADR 0026: Phase-8B Runtime/Data Observability and SLO Gates Contract v1

- **Status**: Accepted
- **Date**: 2026-05-17
- **Decision owners**: Observability/SRE, QA/CI, Runtime/Core, Architecture/Governance
- **Supersedes / Related**: RFC 0040, ADR 0018, ADR 0019

## Context

Phase-8B exit criteria depend on enforceable operational evidence rather than manual inspection. RFC 0040 defines lifecycle span correlation, runtime/data alert packs, queue-scale and latency SLO gates, integrity gate evidence, and fail-closed diagnostics.

## Decision

Adopt RFC 0040 as the operational baseline for runtime/data observability and SLO gates contract v1:

1. Runtime lifecycle spans must correlate queue, schedule, dispatch, execute, persist, and checkpoint stages through stable identifiers.
2. Hardware, driver, compiler, runtime, and QFS telemetry joins must preserve trace-linked diagnostics.
3. Queue pressure, compiler regression, and driver degradation alerts must include runbook-linked mitigation hints.
4. Phase-8B CI gates must validate queue scale at or above 10,000 jobs, enqueue p95 latency at or below 100 ms, and artifact/checkpoint integrity markers.
5. Gate failures must be fail-closed and emit deterministic reason codes with mitigation hints.

## Consequences

- Release readiness is tied to repeatable SLO and integrity evidence.
- Operational triage can navigate from alerts to trace-linked runtime/data artifacts.
- Telemetry field removal, required metric renames, or reason-code breakage require MAJOR classification and migration notes.

## Verification and evidence

- RFC source: `rfcs/0040-phase8b-runtime-data-observability-and-slo-gates-v1.md`
- Phase-8B fixture gate: `docs/development/fixtures/phase8b/ci_gate_bundle_v1.json`
- Gate entrypoint: `scripts/ci/check-phase8b-gates.sh`
- Phase-8B closure docs: gap analysis, readiness checklist, compatibility report, and exit evidence bundle
