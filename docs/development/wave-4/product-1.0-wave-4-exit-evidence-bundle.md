# Product 1.0 Wave 4 Exit Evidence Bundle — W4-05

**Status:** W4-05 evidence complete  
**Scope:** Public REST schema bundle, canonical error parity, deterministic request hashing, authn/authz parity, observability markers  
**Created:** 2026-06-11

| Evidence ID | Requirement | Artifact | Expected result | Actual result | Owner | Link |
|---|---|---|---|---|---|---|
| W4-05-E01 | Schema bundle | `contracts/product-1.0/public-rest.openapi.json` | OpenAPI 3.1 bundle exists for the public REST mirror | Present | System API | [OpenAPI bundle](../../../contracts/product-1.0/public-rest.openapi.json) |
| W4-05-E02 | Public parity matrix | `docs/development/wave-4/product-1.0-wave-4-public-parity-matrix.md` | REST parity, trace propagation, authn/authz, and error mapping are recorded | Present | System API | [Parity matrix](./product-1.0-wave-4-public-parity-matrix.md) |
| W4-05-E03 | Compatibility report | `docs/development/wave-4/product-1.0-wave-4-compatibility-report.md` | Closure status and release-note draft are recorded | Present | System API | [Compatibility report](./product-1.0-wave-4-compatibility-report.md) |
| W4-05-E04 | Canonical error mapping | `src/services/system-api/tests/test_rest_parity_and_compatibility_matrix.py` | Schema and fixture assert canonical REST error codes and reasons | Present | System API tests | [Test](../../../src/services/system-api/tests/test_rest_parity_and_compatibility_matrix.py) |
| W4-05-E05 | Invalid payload validation | `src/services/system-api/tests/test_rest_parity_and_compatibility_matrix.py` | Required request fields and non-empty config are enforced in the schema | Present | System API tests | [Test](../../../src/services/system-api/tests/test_rest_parity_and_compatibility_matrix.py) |
| W4-05-E06 | Trace propagation and observability markers | `contracts/product-1.0/public-rest.openapi.json` | `traceparent`, `x-request-id`, and public contract marker fields are documented | Present | System API | [OpenAPI bundle](../../../contracts/product-1.0/public-rest.openapi.json) |
| W4-05-E07 | Authn/authz parity | `contracts/product-1.0/public-rest.openapi.json`; `docs/reference/security/authz.md` | Bearer auth requirement and operation-specific permissions are documented | Present | Security + System API | [OpenAPI bundle](../../../contracts/product-1.0/public-rest.openapi.json) |

## Validation

- Schema artifact added and referenced from the Product 1.0 manifest.
- Canonical error mapping aligned to the public error model.
- REST parity fixture updated with release artifacts, observability markers, and ashing policy.
- Contract docs updated to reference the concrete bundle.

## Release note draft

### Added

- Public REST OpenAPI bundle for benchmark and explainability mirror contracts.
- Public parity matrix and exit evidence for W4-05.

### Changed

- Benchmark REST idempotency conflict now follows canonical `FAILED_PRECONDITION` / EIGEN_PUBLIC_IDEMPOTENCY_CONFLICT` semantics.
- Public REST contract docs now reference the concrete schema bundle.

### Fixed

- Missing schema bundle artifact under `contracts/product-1.0/`.
- Missing public parity evidence for REST schema and error parity.
