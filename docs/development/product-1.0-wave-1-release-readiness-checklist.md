# Product 1.0 Wave 1 Release Readiness Checklist

## Scope

This checklist closes Product 1.0 Wave 1 and must be completed together with:

- `docs/development/product-1.0-wave-1-execution-plan.md`
- `docs/development/product-1.0-wave-1-issue-pack.md`
- `docs/development/product-1.0-wave-1-compatibility-report.md`
- `docs/development/product-1.0-wave-1-exit-evidence-bundle.md`
- `docs/development/product-1.0-wave-1-rfc-adr-gap-analysis.md`
- `rfcs/0049-product-1.0-public-api-jobspec-error-boundary.md`
- `docs/adr/0035-product-1.0-public-api-jobspec-error-boundary.md`

---

## Contract and governance gates

- [ ] RFC 0049 status is accepted or explicitly approved for implementation.
- [ ] ADR 0035 is synchronized with RFC 0049.
- [ ] Every Wave 1 issue includes the required Summary, Validation, Versioning & Compatibility, and Release Notes Draft blocks.
- [ ] Product 1.0 manifest/inventory are updated for any concrete schema/proto/conformance path changes.
- [ ] Every MAJOR or breaking change has migration notes.
- [ ] Compatibility report has no unresolved `TBD` values for completed issues.

## Public API gates

- [ ] Public proto/reference coverage matrix is complete.
- [ ] Required public envelope fields are implemented or explicitly deferred with compatibility rationale.
- [ ] Version negotiation accepts supported versions and rejects incompatible versions deterministically.
- [ ] Payload limits are enforced before internal forwarding.
- [ ] Public auth context normalization hooks are present, with fail-closed error behavior for missing/invalid public credentials where Wave 1 covers them.

## JobSpec and client gates

- [ ] JobSpec 1.0 schema is versioned and fixture-tested.
- [ ] Parser/normalizer behavior is shared or proven equivalent between CLI and System API.
- [ ] Canonical digest generation is deterministic.
- [x] CLI supports file-based and inline JobSpec submissions using Product 1.0 public envelopes.
- [ ] Accepted previous JobSpec/API versions and migration behavior are documented.

## Error and compatibility gates

- [ ] Public validation failures map to canonical error status/details.
- [ ] Public auth failures map to canonical error status/details.
- [ ] Public idempotency conflicts map to canonical error status/details.
- [ ] Public version mismatches map to canonical error status/details.
- [ ] Public payload-limit failures map to canonical error status/details.
- [ ] Retryability metadata is fixture-tested for all public negative paths.

## Observability and evidence gates

- [ ] Public API contract marker metrics are emitted.
- [ ] Metric labels are bounded and tested.
- [ ] Trace/request correlation works from CLI/SDK to System API.
- [ ] Exit evidence bundle links all commands, fixtures, generated artifacts, and known limitations.
- [ ] Wave 2 handoff explicitly states that public clients no longer depend on System API-internal lifecycle state.
