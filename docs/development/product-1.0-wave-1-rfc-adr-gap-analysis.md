# Product 1.0 Wave 1 RFC/ADR Gap Analysis

## Goal

Identify whether the current RFC/ADR set is sufficient for **Wave 1 — Public API, JobSpec, and error model closure** in the Product 1.0 contract-alignment program.

## Inputs

- `docs/development/product-1.0-contract-alignment-plan.md`
- `docs/development/product-1.0-contract-inventory.md`
- `docs/development/product-1.0-version-policy.md`
- `docs/reference/api/grpc-public.md`
- `docs/reference/jobspec.md`
- `docs/reference/error-model.md`
- `docs/reference/error-mapping.md`
- `rfcs/0003-JobSpec-eigen-cli-v0.1.md`
- `rfcs/0004-public-gRPC-API-v0.1.md`
- `rfcs/0013-mvp2-jobspec-parser-submit-contract.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`

---

## Coverage matrix

| Wave 1 requirement | Existing spec coverage | Gap decision |
|---|---|---|
| Public envelope fields (`contract_version`, `request_id`, `idempotency_key`, `trace_context`, `deadline`, tenant/project context when in scope) | Early public gRPC RFCs cover MVP request behavior but not the complete Product 1.0 envelope. | **Gap: formalize in Product 1.0 RFC.** |
| Version negotiation and compatibility rejection | RFC 0032 defines SemVer discipline, but not public gateway negotiation behavior. | **Gap: formalize gateway behavior and errors.** |
| `SubmitJob` idempotency and payload limits | MVP JobSpec/submit RFCs cover parser and submission basics, but not persistent idempotency conflict semantics. | **Gap: formalize idempotency and limit behavior.** |
| JobSpec 1.0 parser/normalizer, schema fixtures, canonical digest, CLI/API parity | MVP parser RFCs exist, but Product 1.0 requires a stable schema and shared canonicalization across client and gateway. | **Gap: formalize Product 1.0 JobSpec canonicalization.** |
| Canonical public error mapping with structured details | Reference docs exist; existing RFCs do not bind all public negative paths to `google.rpc.Status` details and retryability. | **Gap: formalize error normalization obligations.** |
| Public contract marker metrics and trace continuity at ingress | Observability contracts exist, but Wave 1 needs public-boundary marker obligations and bounded-label evidence. | **Gap: formalize additive Wave 1 marker obligations.** |
| Compatibility/migration discipline | RFC 0032 and Product 1.0 version policy are sufficient. | **No new gap; apply strictly.** |

---

## Decision

A dedicated Product 1.0 Wave 1 RFC and ADR are required because the existing MVP RFCs do not encode the mature public boundary semantics that implementation must enforce before Wave 2.

- **Action:** introduce `rfcs/0049-product-1.0-public-api-jobspec-error-boundary.md`.
- **ADR impact:** publish `docs/adr/0035-product-1.0-public-api-jobspec-error-boundary.md` and index it in `docs/adr/README.md`.
- **Versioning impact:** RFC 0049 allows MAJOR public contract changes when required to reconcile the frozen Product 1.0 reference docs with current implementation. Every MAJOR change still requires migration notes and release evidence.

---

## Follow-up checklist

- [ ] Review RFC 0049 with API Platform, CLI/SDK, System API, and Architecture/Governance owners.
- [ ] Keep ADR 0035 synchronized with accepted RFC 0049 decisions.
- [ ] Update the Wave 1 compatibility report when public fields, errors, metrics, or JobSpec semantics change.
- [ ] Ensure every Wave 1 GitHub issue contains the required Versioning & Compatibility and Release Notes Draft blocks.
- [ ] Update Product 1.0 manifest/inventory when planned schema or conformance mappings become concrete.
