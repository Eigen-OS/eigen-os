# Product 1.0 Wave 4 Compatibility Report — W4-05

**Status:** Closure record for Public REST schema and error parity  
**Scope:** Public REST schema bundle, canonical error parity, deterministic request hashing, authn/authz parity, observability markers

This report closes the W4-05 slice at the contract layer. The runtime transport is still mirrored through the canonical gRPC surface; the REST surface is now specified by a concrete OpenAPI bundle and associated parity fixtures.

| Issue | Version Impact | Affected Interfaces | Compatibility | Breaking Marker | Migration Notes | Release Notes Draft | Evidence |
|---|---|---|---|---|---|---|---|
| W4-05 Public REST schema and error parity | MINOR | Public API facade; Compatibility matrix; Trace context; Metrics | Backward-compatible | false | None | Added: OpenAPI bundle for `/v1/benchmarks/run` and `/v1/explain/backend-selection`, canonical REST error envelopes, deterministic request hashing markers, and REST parity fixtures; Changed: benchmark REST idempotency conflict now follows canonical `FAILED_PRECONDITION` / `EIGEN_PUBLIC_IDEMPOTENCY_CONFLICT` mapping; Fixed: missing schema artifact and public parity matrix gaps | W4-05-E01 |

## Notes

- The source-of-truth contract now points to `contracts/product-1.0/public-rest.openapi.json`.
- Canonical error mapping remains aligned with `docs/reference/error-model.md` and `docs/reference/error-mapping.md`.
- Authn/authz and trace propagation requirements are captured in the schema bundle and parity fixture.
