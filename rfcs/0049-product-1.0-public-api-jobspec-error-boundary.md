# RFC-0049: Product 1.0 Public API, JobSpec, and Error Boundary

- Status: Proposed
- Created: 2026-06-01
- Target milestone: Product 1.0 Wave 1 Public Boundary Closure
- Depends on: RFC-0003, RFC-0004, RFC-0013, RFC-0032

## Summary

This RFC defines the normative Product 1.0 public boundary for `eigen.api.v1`, JobSpec 1.0 ingestion, public request envelopes, version negotiation, `SubmitJob` idempotency, canonical public errors, and public-boundary observability markers.

## Motivation

Wave 0 froze the Product 1.0 contract inventory and showed that public reference docs, proto contracts, CLI payload behavior, and error semantics need explicit alignment before internal lifecycle authority moves to Kernel/QRTX. The public boundary must become stable first so later waves can change internals without changing external client behavior.

## Normative requirements

1. **Public envelope:** Public API requests MUST expose or derive a canonical envelope containing contract version, request identity, idempotency identity where applicable, trace context, deadline, and normalized tenant/project context when multi-tenancy is in scope.
2. **Version negotiation:** System API MUST accept documented compatible contract versions and reject unsupported, malformed, or incompatible versions with canonical errors.
3. **Idempotent submission:** `SubmitJob` MUST treat the tuple of idempotency key and normalized request as the retry identity. Same key plus same normalized request returns the same job identity; same key plus different normalized request returns a canonical conflict/precondition error.
4. **Payload limits:** Public payload limits MUST be enforced before forwarding to internal services.
5. **JobSpec canonicalization:** JobSpec 1.0 parsing, normalization, schema validation, and digest generation MUST be deterministic and shared or proven equivalent across CLI and System API.
6. **Public error normalization:** Validation, auth, idempotency, version, payload-limit, deadline, cancellation, unavailable, and internal failure paths MUST map to the canonical error model and error mapping matrix with retryability metadata.
7. **Structured details:** Public gRPC errors SHOULD use `google.rpc.Status` details where supported by the language/runtime stack.
8. **Client conformance:** CLI and SDK submissions MUST emit or derive Product 1.0-compliant envelopes and JobSpec payloads.
9. **Observability marker:** System API MUST emit public API contract marker metrics with bounded labels and request/trace correlation.
10. **Compatibility evidence:** Every changed public field, method, reason code, JobSpec semantic, CLI payload, or metric MUST be recorded in the Wave 1 compatibility report.

## Versioning and compatibility

- Contract changes follow the Product 1.0 version policy and RFC 0032.
- Breaking public behavior changes require `Version Impact: MAJOR`, `Breaking Marker=true`, migration notes, conformance fixture updates, and release-note draft text.
- Additive fields, metrics, or accepted-version behavior use `MINOR` with deterministic defaults.
- Non-semantic corrections use `PATCH`.
- Documentation-only planning changes use `NONE` unless they alter normative behavior.

## Conformance evidence

Wave 1 exit requires evidence for:

- public proto/reference coverage,
- version negotiation acceptance and rejection,
- idempotency replay and conflict behavior,
- payload-limit rejection before forwarding,
- JobSpec schema/parser/normalizer/digest determinism,
- CLI/API parity,
- canonical public error mapping and retryability,
- public API marker metric and trace/request correlation.

## Security and privacy constraints

- Public auth context may be normalized in Wave 1, but full policy-engine enforcement remains a later security wave unless explicitly pulled forward.
- Public errors, logs, and metrics MUST NOT expose secrets, tokens, provider credentials, or raw internal exception text.
- Trace and request identifiers MUST be safe for logs and bounded-cardinality metrics.

## Open questions

- Whether the public REST mirror is implemented in Wave 1 or explicitly deferred from Product 1.0 public-boundary closure.
- Whether legacy JobSpec/API versions remain accepted after Product 1.0 GA, and for how long.
- Whether tenant/project context is mandatory in Wave 1 or derived from auth context until the security wave completes.
