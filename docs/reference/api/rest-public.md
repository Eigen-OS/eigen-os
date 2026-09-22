# Public REST API Contract Envelope

**Document status:** Wave 0 baseline
**Subsystem:** System API public REST gateway
**Contract version:** `1.0.0`
**Applies to:** Product 1.0 alignment stream

---

## 1. Scope

This document freezes the Product 1.0 baseline for public REST surfaces. REST is retained as a selected mirror for targeted HTTP/JSON workflows, not as a replacement for the canonical public gRPC API.

Current Product 1.0 REST surfaces are:

- `POST /benchmarks/run`, defined by `docs/reference/api/benchmark-run.md`.
- `POST /explain/backend-selection`, defined by `docs/reference/api/explain-backend-selection.md`.

Additional REST endpoints require a reference contract, schema mapping, error mapping, and conformance tests before implementation.

---

## 2. Common REST requirements

Every Product 1.0 REST endpoint MUST follow the same cross-cutting policy as public gRPC:

- versioned API path under `/v1`,
- TLS 1.3 at public ingress,
- JWT/OAuth2 authentication when deployed with auth enabled,
- method-level authorization according to `docs/reference/security/authz.md`,
- W3C TraceContext propagation,
- request IDs for correlation,
- deterministic validation before dispatch,
- canonical error semantics from `docs/reference/error-model.md` and `docs/reference/error-mapping.md`,
- documented payload limits,
- observability marker metrics for the owning subsystem.

---

## 3. Wave 1+ schema requirement

Wave 0 accepts REST schema mappings as planned. Before a REST endpoint is implemented or changed in Wave 1+, the implementing PR MUST add one of:

- an OpenAPI document under `contracts/product-1.0/`, or
- a JSON Schema document under `contracts/product-1.0/` plus endpoint-specific request/response examples.

The schema artifact MUST be referenced from `contracts/product-1.0/manifest.json` in the same PR.

The current canonical REST schema bundle is `contracts/product-1.0/public-rest.openapi.json`.
