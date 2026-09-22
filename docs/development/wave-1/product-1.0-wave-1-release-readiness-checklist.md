# Product 1.0 Wave 1 Release Readiness Checklist

**Status:** Complete
**Completed:** 2026-06-01

## Scope

This checklist closes Product 1.0 Wave 1 and must be completed together with:

- `docs/development/wave-1/product-1.0-wave-1-execution-plan.md`
- `docs/development/wave-1/product-1.0-wave-1-issue-pack.md`
- `docs/development/wave-1/product-1.0-wave-1-compatibility-report.md`
- `docs/development/wave-1/product-1.0-wave-1-exit-evidence-bundle.md`
- `docs/development/wave-1/product-1.0-wave-1-rfc-adr-gap-analysis.md`
- `rfcs/0049-product-1.0-public-api-jobspec-error-boundary.md`
- `docs/adr/0035-product-1.0-public-api-jobspec-error-boundary.md`

---

## Contract and governance gates

- [x] RFC 0049 status is accepted or explicitly approved for implementation.
- [x] ADR 0035 is synchronized with RFC 0049.
- [x] Every Wave 1 issue includes the required Summary, Validation, Versioning & Compatibility, and Release Notes Draft blocks.
- [x] Product 1.0 manifest/inventory are updated for any concrete schema/proto/conformance path changes.
- [x] Every MAJOR or breaking change has migration notes. Wave 1 has no MAJOR or `Breaking Marker=true` entries.
- [x] Compatibility report has no unresolved `TBD` values for completed issues.


## Public API gates

- [x] Public proto/reference coverage matrix is complete.
- [x] Required public envelope fields are implemented or explicitly deferred with compatibility rationale.
- [x] Version negotiation accepts supported versions and rejects incompatible versions deterministically.
- [x] Payload limits are enforced before internal forwarding.
- [x] Public auth context normalization hooks are present, with fail-closed error behavior for missing/invalid public credentials where Wave 1 covers them.

## JobSpec and client gates

- [x] JobSpec 1.0 schema is versioned and fixture-tested.
- [x] Parser/normalizer behavior is shared or proven equivalent between CLI and System API.
- [x] Canonical digest generation is deterministic.
- [x] CLI supports file-based and inline JobSpec submissions using Product 1.0 public envelopes.
- [x] Accepted previous JobSpec/API versions and migration behavior are documented.

## Error and compatibility gates

- [x] Public validation failures map to canonical error status/details.
- [x] Public auth failures map to canonical error status/details.
- [x] Public idempotency conflicts map to canonical error status/details.
- [x] Public version mismatches map to canonical error status/details.
- [x] Public payload-limit failures map to canonical error status/details.
- [x] Retryability metadata is fixture-tested for all public negative paths.

## Observability and evidence gates

- [x] Public API contract marker metrics are emitted.
- [x] Metric labels are bounded and tested.
- [x] Trace/request correlation works from CLI/SDK to System API.
- [x] Exit evidence bundle links all commands, fixtures, generated artifacts, and known limitations.
- [x] Wave 2 handoff explicitly states that public clients no longer depend on MVP-only request semantics.

---

## Wave 2 handoff

Wave 2 may start after the Wave 1 closure commit. Public clients can rely on Product 1.0 envelope normalization, deterministic version negotiation, JobSpec 1.0 parsing/normalization, canonical public errors, `SubmitJob` idempotency/payload-limit behavior, and bounded public observability markers. Remaining Product 1.0 contracts outside the Wave 1 public boundary keep their existing Product 1.0 manifest statuses and are not Wave 1 blockers.
