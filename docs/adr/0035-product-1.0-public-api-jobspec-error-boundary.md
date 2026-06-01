# ADR 0035: Product 1.0 Public API, JobSpec, and Error Boundary

- Status: Accepted
- Date: 2026-06-01
- Deciders: Core maintainers
- RFC: `rfcs/0049-product-1.0-public-api-jobspec-error-boundary.md`

## Context

Product 1.0 Wave 1 must stabilize the public boundary before the implementation moves canonical lifecycle authority to Kernel/QRTX. Existing MVP-era RFCs cover early public API and JobSpec behavior, but they do not fully specify Product 1.0 request envelopes, version negotiation, persistent idempotency semantics, canonical public errors, CLI/API parity, and public-boundary observability evidence.

## Decision

Adopt RFC 0049 as the governance baseline for Wave 1 implementation. Wave 1 implementation issues must:

1. reconcile public proto and reference semantics before changing runtime behavior,
2. enforce canonical request envelopes and version negotiation,
3. implement deterministic `SubmitJob` idempotency and payload-limit behavior,
4. implement JobSpec 1.0 parser/normalizer/digest conformance across CLI and System API,
5. normalize public errors through the canonical error model and error mapping matrix,
6. emit public API contract marker metrics with bounded labels and trace/request correlation,
7. record version impact, affected interfaces, compatibility, breaking marker, migration notes, and release-note draft text in every issue.

## Consequences

### Positive

- External client behavior becomes stable before internal ownership changes.
- Breaking public changes are visible, versioned, and migration-documented.
- CLI, System API, JobSpec, and public errors are tested as one Product 1.0 contract surface.

### Trade-offs

- Wave 1 may require MAJOR public contract changes to reconcile frozen Product 1.0 references with MVP payloads.
- Gateway implementation work must include additional compatibility and release evidence before Wave 2 can start.

## Compliance notes

- This ADR is a planning and governance decision; it does not by itself change runtime behavior.
- Any Wave 1 implementation PR that changes public contract behavior must update the Wave 1 compatibility report and Product 1.0 manifest/inventory when schema/proto/conformance mappings change.
