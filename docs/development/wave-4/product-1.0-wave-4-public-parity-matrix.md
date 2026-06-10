# Product 1.0 Wave 4 Public Parity Matrix — W4-05

| Area | REST contract surface | Canonical source | Parity rule | Evidence |
|---|---|---|---|---|
| Benchmark submission | `POST /v1/benchmarks/run` | `docs/reference/api/benchmark-run.md` | Request body must be canonicalizable, idempotency-aware, and validated before dispatch | `contracts/product-1.0/public-rest.openapi.json` |
| Benchmark errors | `POST /v1/benchmarks/run` | `docs/reference/error-model.md`; `docs/reference/error-mapping.md` | Validation, auth, payload-limit, and idempotency conflicts map to canonical public error codes | `contracts/product-1.0/public-rest.openapi.json` |
| Backend explanation | `POST /v1/explain/backend-selection` | `docs/reference/api/explain-backend-selection.md` | Read-only responses remain deterministic and idempotent | `contracts/product-1.0/public-rest.openapi.json` |
| Trace propagation | All public REST operations | `docs/reference/api/rest-public.md` | `traceparent` and `x-request-id` are accepted and echoed for correlation | `contracts/product-1.0/public-rest.openapi.json` |
| Authn/authz | All public REST operations | `docs/reference/security/authz.md` | Bearer auth is required, with operation-specific permission parity | `contracts/product-1.0/public-rest.openapi.json` |
| Observability | All public REST operations | `docs/reference/api/rest-public.md` | Public contract marker metrics use bounded labels and stable outcomes | `contracts/product-1.0/public-rest.openapi.json` |
| Request hashing | Benchmark submission | `docs/reference/api/benchmark-run.md` | Canonical JSON hash is deterministic across platforms | `contracts/product-1.0/public-rest.openapi.json` |

## Canonical error parity summary

- `INVALID_ARGUMENT` → `EIGEN_PUBLIC_VALIDATION_FAILED`
- `UNAUTHENTICATED` → `EIGEN_PUBLIC_UNAUTHENTICATED`
- `PERMISSION_DENIED` → `EIGEN_PUBLIC_PERMISSION_DENIED`
- `FAILED_PRECONDITION` → `EIGEN_PUBLIC_IDEMPOTENCY_CONFLICT`
- `RESOURCE_EXHAUSTED` → `EIGEN_PUBLIC_PAYLOAD_LIMIT_EXCEEDED`
- `NOT_FOUND` → `EIGEN_PUBLIC_BACKEND_SELECTION_NOT_FOUND`
- `INTERNAL` → `EIGEN_PUBLIC_INTERNAL`
- `UNAVAILABLE` → `EIGEN_PUBLIC_UNAVAILABLE`
