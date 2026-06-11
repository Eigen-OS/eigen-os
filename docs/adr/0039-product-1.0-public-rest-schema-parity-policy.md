# ADR 0039: Product 1.0 public REST schema parity policy

- Status: Accepted
- Date: 2026-06-11
- Deciders: Core maintainers
- RFC: `docs/development/wave-4/product-1.0-wave-4-issue-pack.md (W4-05)`

## Context

Product 1.0 Wave 4 adds concrete REST schema artifacts for the public mirror surfaces. The repository already exposes a canonical gRPC public boundary, and the REST mirror must not diverge from the documented public semantics for requests, canonical errors, idempotency, tracing, or authorization.

## Decision

Adopt an OpenAPI-first publication policy for public REST mirror surfaces:

1. `contracts/product-1.0/public-rest.openapi.json` is the canonical schema bundle for the current public REST mirror.
2. REST mirror endpoints must publish deterministic request/response and error mappings that remain aligned with the reference docs.
3. The REST mirror remains a transport mirror; it must not replace the canonical gRPC public API.
4. Any future REST publication model change requires a new governance record and an explicit compatibility review.
5. The manifest and inventory must reference the schema bundle and the parity evidence together.

## Consequences

### Positive

- REST contract review is schema-first and deterministic.
- Public error parity stays aligned with the canonical error model.
- Trace and idempotency semantics are documented together with the public REST schema.

### Trade-offs

- The current REST mirror remains schema-evidenced rather than fully transport-backed.
- New REST endpoints must carry a schema artifact and parity evidence before implementation.

## Compliance notes

- This ADR is accepted and operational for Wave 4.
- The closure evidence bundle must reference this ADR as the policy governing public REST publication.
- Breaking changes to the REST publication model require MAJOR handling.
