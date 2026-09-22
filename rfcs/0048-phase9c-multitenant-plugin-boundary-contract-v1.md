# RFC-0048: Phase-9C Multi-tenant Plugin Boundary Contract v1

- Status: Proposed
- Created: 2026-05-21
- Target milestone: Phase-9C Multi-tenant Plugin Boundary
- Depends on: RFC-0024, RFC-0030, RFC-0031, RFC-0032, RFC-0047

## Summary

This RFC defines the normative Stage-9C contract for multi-tenant controls in open core, strict plugin-only advanced scheduling policy surfaces, deterministic kernel fallback semantics, and explainability evidence requirements.

## Motivation

Stage-C in the TZ v1.3.0 open-core alignment plan requires a clean boundary: deterministic baseline behavior MUST stay in kernel, while high-variance policy behavior MUST be externalized to plugins/SaaS. Existing RFCs cover parts of plugin lifecycle and trust, but do not lock Stage-C boundary semantics and deterministic failure isolation as one contract.

## Normative requirements

1. **Tenant envelope in core:** Canonical `tenant_id` and `project_id` fields MUST be present in core submission/runtime envelopes.
2. **Baseline quotas in core:** Quota evaluation (capacity and policy hard limits) MUST execute in kernel path with deterministic reason codes.
3. **Fair queueing baseline:** Core scheduler MUST provide deterministic fair queueing primitives that remain fully functional when policy plugins are disabled.
4. **Advanced policy plugin-only:** Batch/preemption/backfill/drift-aware or tenant-custom heuristics MUST execute only through versioned policy-plugin interfaces.
5. **Failure isolation:** Policy plugin timeout, crash, or malformed output MUST NOT break kernel lifecycle; deterministic fallback behavior is mandatory.
6. **Fallback taxonomy:** Kernel fallback paths MUST emit stable reason codes and include plugin identity provenance.
7. **Explain evidence:** `/explain` MUST return tenant-aware decision provenance (quota and policy inputs, selected strategy, fallback reasons) without exposing sensitive secrets.
8. **SDK conformance:** Plugin SDK MUST provide policy-plugin scaffold and validation flows covering timeout budgets, schema checks, and deterministic fallback compatibility.
9. **Compatibility matrix:** Release artifacts MUST explicitly mark core-owned vs plugin-owned behavior surfaces.

## Versioning and compatibility

- Contract changes follow RFC-0032 SemVer policy.
- Breaking behavior changes require MAJOR bump and migration notes.
- Backward-compatible additions use MINOR with deterministic defaults.
- Compatibility fixtures for reason-code taxonomy and explain payloads are mandatory.

## Conformance evidence

Phase-9C exit requires:

- deterministic scheduler fixture evidence with plugins disabled;
- plugin failure-isolation drill evidence;
- explain API evidence snapshots for tenant-aware decisions;
- compatibility matrix update with core/plugin ownership map.

## Security and trust constraints

- Policy plugins run with least privilege and sandbox defaults from plugin-trust baseline.
- Plugin outputs are treated as untrusted until validated against policy contract.
- Sensitive tenant metadata is redacted in explain payloads and logs according to security policy.

## Open questions

- Default timeout and budget values for policy plugins may start conservative and be tuned via MINOR updates.
- Future policy categories may require separate conformance profile tiers.
