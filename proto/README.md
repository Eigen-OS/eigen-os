# Protobuf contracts (source of truth)

This directory contains the **single source of truth** for all Eigen OS gRPC contracts.

- **Public API**: `proto/eigen_api/v1/*.proto` (client-facing)
- **Internal APIs**: `proto/eigen_internal/v1/*.proto` (service-to-service)

Reference docs:
- Public API: `docs/reference/api/grpc-public.md`
- Internal API: `docs/reference/api/grpc-internal.md`
- Error model: `docs/reference/error-model.md`
- Error mapping: `docs/reference/error-mapping.md`

RFCs:
- `rfcs/0004-public-gRPC-API-v0.1.md`
- `rfcs/0006-qdriver-api-v0.1.md`

## Generating stubs

See: `docs/howto/generate-protos.md`.
