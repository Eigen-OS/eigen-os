# Phase-9C RFC/ADR Gap Analysis

## Goal

Identify whether the current RFC/ADR set is sufficient for **Stage C — Multi-tenant policy + plugin-first expansion** from `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md`.

## Inputs

- `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md`
- `docs/development/phase-9b/phase-9b-execution-plan.md` (handoff baseline)
- `rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md`
- `rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`
- `rfcs/0047-phase9b-intelligence-closure-contract-v1.md`

## Coverage matrix

| Stage-C requirement | Existing spec coverage | Gap decision |
|---|---|---|
| Core tenant/project fields + baseline quotas + fair queueing primitives | Partially covered by prior scheduling/runtime RFCs; no single Stage-C normative schema and enforcement policy | **Gap: must be formalized** |
| Advanced scheduling remains plugin-only (batch/preemption/backfill/drift-aware) | Plugin lifecycle/trust RFCs exist, but Stage-C extraction boundaries are not explicit or test-gated | **Gap: must be formalized** |
| Explain API evidence for backend/scheduling decisions (`/explain`) | Explainability RFC exists, but multi-tenant decision evidence and reason-code obligations are under-specified | **Gap: requires extension/alignment** |
| Plugin SDK updates (policy plugin templates, conformance fixtures, sandbox defaults) | Baseline in Phase-6 RFC set, but no Stage-C closure contract for policy-plugin determinism and failure isolation | **Gap: must be formalized** |
| Compatibility + migration discipline | Fully covered by RFC 0032 | **No new gap** |

## Decision

A dedicated Stage-9C RFC is required to define the strict open-core/plugin boundary for multi-tenant policy behavior and to lock deterministic fallback semantics.

- **Action:** introduce `rfcs/0048-phase9c-multitenant-plugin-boundary-contract-v1.md`.
- **ADR impact:** publish `docs/adr/0034-phase9c-multitenant-plugin-boundary-contract-v1.md` to synchronize accepted normative decisions once implementation starts.

## Follow-up checklist

- [ ] Publish RFC 0048 and review with runtime, platform, and security maintainers.
- [ ] Publish ADR 0034 and add it to `docs/adr/README.md`.
- [ ] Publish Stage-9C issue pack and link it from `docs/development/README.md`.
- [ ] Add/refresh conformance fixtures for plugin failure-isolation and deterministic fallback reason codes.
- [ ] Update compatibility matrix and migration notes for any contract additions.
- [ ] Ensure CI required checks include Stage-9C policy-plugin conformance gates.
