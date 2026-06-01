# Product 1.0 Wave 1 Compatibility Report

**Status:** Complete for Wave 1 closure
**Scope:** Public API, JobSpec, CLI payloads, canonical errors, public metrics, and compatibility evidence
**Version policy:** `docs/development/product-1.0-version-policy.md`
**Issue pack:** `docs/development/product-1.0-wave-1-issue-pack.md`
**Evidence bundle:** `docs/development/product-1.0-wave-1-exit-evidence-bundle.md`
**Completed:** 2026-06-01

---

## 1. Compatibility rules

Wave 1 changes follow these rules:

1. Public behavior changes that remove or rename documented fields, methods, metrics, reason codes, lifecycle-visible states, or required auth/idempotency semantics are **breaking** and require `Version Impact: MAJOR`.
2. Backward-compatible additions use `MINOR` with deterministic defaults.
3. Non-semantic corrections use `PATCH`.
4. Documentation-only planning updates use `NONE` unless they change normative contract language.
5. Every breaking change requires migration notes and a release-note draft.
6. Every changed public contract surface must update the Product 1.0 manifest/inventory when schema, proto, or conformance mappings change.

Wave 1 completed with **no MAJOR changes** and **no `Breaking Marker=true` entries**. Migration notes are still included for behavior-changing MINOR work so SDK, CLI, and operator owners can adopt the Product 1.0 public boundary deliberately.

---

## 2. Issue compatibility ledger

| Issue | Version Impact | Affected Interfaces | Compatibility | Breaking Marker | Migration Notes | Release Notes Draft | Evidence |
|---|---|---|---|---|---|---|---|
| W1-01 Public proto/reference coverage matrix and envelope decisions | MINOR | API; CLI payloads; Compatibility matrix; Reference docs | Backward-compatible additive coverage matrix and envelope decisions; no public method removal. | false | None; clients may keep using existing `eigen.api.v1` calls while adopting the documented Product 1.0 envelope fields. | Added public proto/reference coverage matrix and recorded public envelope ownership/defer decisions. | `docs/reference/api/grpc-public.md`; `proto/eigen/api/v1/types.proto`; `proto/eigen/api/v1/job_service.proto`; `proto/eigen/api/v1/device_service.proto`; `proto/eigen/api/v1/knowledge_base_service.proto`; `docs/architecture/components/system-api.md`; `docs/development/product-1.0-contract-inventory.md`; `contracts/product-1.0/manifest.json` |
| W1-02 Public gRPC envelopes, version negotiation, and compatibility rejection | MINOR | API; CLI payloads; Compatibility matrix | Backward-compatible | false | None; MVP metadata clients remain accepted by deterministic envelope derivation while Product 1.0 clients may send `ApiRequestEnvelope` directly. | Added Product 1.0 public request envelope and runtime version-negotiation rejection semantics for `eigen.api.v1`. | `proto/eigen/api/v1/types.proto`; `proto/eigen/api/v1/job_service.proto`; `proto/eigen/api/v1/device_service.proto`; `proto/eigen/api/v1/knowledge_base_service.proto`; `src/services/system-api/src/system_api/grpc_impl.py`; `src/services/system-api/tests/test_public_envelope_versioning.py`; `docs/reference/api/grpc-public.md`; `docs/architecture/components/system-api.md` |
| W1-03 SubmitJob idempotency, payload limits, and request persistence | MINOR | API; JobSpec; Metrics | Backward-compatible for same-key/same-payload retries; canonical conflict status is `FAILED_PRECONDITION`. | false | Clients reusing an idempotency key with a different normalized payload must handle `FAILED_PRECONDITION`; configure persistence path/TTL for restart-safe replay. | Added persisted SubmitJob idempotency records with TTL, expanded payload-limit enforcement, and bounded SubmitJob outcome metrics. | `src/services/system-api/src/system_api/grpc_impl.py`; `src/services/system-api/src/system_api/validation.py`; `src/services/system-api/src/system_api/observability.py`; `src/services/system-api/tests/test_idempotency.py`; `docs/reference/api/grpc-public.md`; `docs/architecture/components/system-api.md` |
| W1-04 JobSpec 1.0 schema, parser/normalizer, canonical digest, and fixtures | MINOR | JobSpec; CLI payloads; System API SubmitJob mapping; AQO packaging | Backward-compatible: native `eigen.os/v1` is added and documented `eigen.os/v0.1` inputs continue to normalize through migration metadata. | false | Prefer `apiVersion: eigen.os/v1` and `spec.program.path`/`spec.program.source`; legacy `spec.program_path` and inline string `spec.program` remain accepted as v0.1 migration inputs. | Added JobSpec 1.0 JSON Schema, fixtures, shared System API normalizer/digest behavior, CLI v1 parser support, and compatibility report. | `docs/reference/jobspec.md`; `docs/reference/schemas/jobspec-1.0.schema.json`; `docs/reference/fixtures/jobspec/1.0/`; `src/services/system-api/src/system_api/jobspec_parser.py`; `src/services/system-api/tests/test_jobspec_parser.py`; `src/rust/apps/cli/src/jobspec.rs` |
| W1-05 Canonical public error model and error mapping conformance | MINOR | API; CLI payloads; Error model; Metrics | Backward-compatible canonicalization of public negative paths; public errors now include stable reason and retryability metadata. | false | Clients should branch on canonical gRPC status plus `google.rpc.ErrorInfo.reason` instead of raw messages; idempotency conflicts and unsupported versions use `FAILED_PRECONDITION`. | Added canonical public error mapping conformance for validation, auth, idempotency conflict, version mismatch, payload limit, deadline, cancellation, unavailable, and internal failures. | `docs/reference/error-model.md`; `docs/reference/error-mapping.md`; `src/services/system-api/src/system_api/errors.py`; `src/services/system-api/src/system_api/grpc_impl.py`; `src/services/system-api/tests/test_public_error_conformance.py`; `src/services/system-api/tests/test_validation_errors.py` |
| W1-06 CLI/SDK public submission conformance baseline | MINOR | CLI payloads; JobSpec; API; SDK conformance | Backward-compatible Product 1.0 envelope and JobSpec normalization added for CLI submissions; inline and file-backed JobSpecs are accepted. | false | Prefer Product 1.0 public payloads with canonical envelope fields; legacy bare CLI submit request JSON remains present only as a compatibility shim during migration. | Added CLI public submission payload normalization, deterministic default request/idempotency keys, trace context propagation, and SDK negative-test obligations. | `src/rust/apps/cli/src/jobspec.rs`; `src/rust/apps/cli/src/main.rs`; `src/rust/apps/cli/README.md`; `docs/architecture/components/client-sdks.md`; `docs/reference/api/grpc-public.md` |
| W1-07 Public API observability markers and trace continuity smoke gate | MINOR | Metrics; API; CLI/SDK trace propagation | Backward-compatible additive metrics and correlation behavior; existing metrics are retained. | false | None; Product 1.0 clients should continue sending W3C `traceparent` via metadata or `ApiRequestEnvelope.traceparent`. | Added bounded public API contract marker counters and trace continuity smoke evidence from public envelope/metadata through System API request handling. | `src/services/system-api/src/system_api/observability.py`; `src/services/system-api/src/system_api/grpc_impl.py`; `src/services/system-api/tests/test_observability_smoke.py`; `docs/reference/api/grpc-public.md`; `docs/architecture/components/observability.md`; `docs/architecture/components/system-api.md`; `docs/architecture/components/client-sdks.md` |
| W1-08 Wave 1 compatibility report, migration notes, and release evidence bundle | NONE | Compatibility matrix; Release governance; Inventory | Documentation/evidence closure only. | false | None; no new runtime behavior. | Completed Wave 1 compatibility ledger, release readiness checklist, exit evidence bundle, and implemented-slice inventory status. | `docs/development/product-1.0-wave-1-compatibility-report.md`; `docs/development/product-1.0-wave-1-exit-evidence-bundle.md`; `docs/development/product-1.0-wave-1-release-readiness-checklist.md`; `docs/development/product-1.0-contract-inventory.md`; `contracts/product-1.0/manifest.json` |

---

## 3. Migration notes

No Wave 1 issue is marked breaking. The following non-breaking adoption notes apply:

- **Public envelope:** Product 1.0 clients should send `ApiRequestEnvelope.contract_version=1.0.0`, `request_id`, `idempotency_key` for `SubmitJob`, `traceparent`, and tenant/project scope where available. MVP clients without payload envelopes remain supported by deterministic metadata/default derivation.
- **Version negotiation:** malformed versions return `INVALID_ARGUMENT` with `EIGEN_PUBLIC_CONTRACT_VERSION_MALFORMED`; unsupported/future versions return `FAILED_PRECONDITION` with `EIGEN_PUBLIC_CONTRACT_VERSION_UNSUPPORTED` and `supported_contract_version=1.0.0`.
- **Idempotency:** same key and same normalized payload replays the original job; same key and different normalized payload returns `FAILED_PRECONDITION` with `EIGEN_PUBLIC_IDEMPOTENCY_CONFLICT`.
- **Payload limits:** oversized public payloads are rejected before internal forwarding with `RESOURCE_EXHAUSTED` and bounded quota details.
- **JobSpec:** prefer native `eigen.os/v1`; legacy `eigen.os/v0.1` inline/program_path inputs remain accepted through documented migration metadata.
- **Errors:** public clients should consume canonical gRPC status and `google.rpc.ErrorInfo.reason`/`retryable` metadata rather than matching free-form messages.
- **Observability:** clients and SDKs should propagate W3C `traceparent`; operators should monitor bounded `eigen_public_api_contract_requests_total` / `eigen_api_public_contract_requests_total` labels.

---

## 4. Public boundary evidence checklist

- [x] Proto/reference coverage matrix attached or linked.
- [x] JobSpec schema and fixture set attached or linked.
- [x] Error mapping fixture set attached or linked.
- [x] CLI/API parity evidence attached or linked.
- [x] Idempotency replay/conflict evidence attached or linked.
- [x] Public metrics/trace smoke evidence attached or linked.
- [x] Manifest/inventory diff reviewed for changed schema/proto/test mappings.
- [x] Release notes draft copied from every issue and consolidated.

---

## 5. Consolidated release notes draft

### Added
- Added Product 1.0 public proto/reference coverage evidence for `eigen.api.v1` Job, Device, and Knowledge Base request surfaces.
- Added canonical Product 1.0 `ApiRequestEnvelope` fields for contract version, request identity, idempotency identity, trace context, deadline, tenant/project scope, and client version.
- Added persisted `SubmitJob` idempotency records with replay/conflict semantics and payload-limit enforcement before internal forwarding.
- Added JobSpec 1.0 schema, fixtures, parser/normalizer, canonical digest, and CLI file/inline submission support.
- Added canonical public error conformance for validation, auth, idempotency conflict, version mismatch, payload limit, deadline, cancellation, unavailable, and internal failures.
- Added bounded public API contract marker metrics and trace continuity smoke coverage.

### Changed
- Normalized public request metadata and envelopes before audit, metrics, idempotency persistence, and internal forwarding.
- Standardized version negotiation failures and public negative-path retryability metadata.
- Documented SDK/CLI obligations for Product 1.0 public payloads, trace propagation, and negative-test parity.
- Updated Product 1.0 manifest/inventory status for Wave 1 implemented public-boundary slices.

### Fixed
- Removed unknown compatibility and breaking-marker entries from the Wave 1 ledger.
- Closed release-readiness evidence gaps for W1-01 through W1-08.
- Aligned public gRPC, JobSpec, error, and observability documentation with implemented conformance evidence.

---

## 6. Issue completion blocks

### W1-01 — Public proto/reference coverage matrix and envelope decisions

## Summary
- Completed the public proto/reference coverage matrix for `eigen.api.v1` and recorded envelope ownership across Job, Device, and Knowledge Base public request surfaces.
- Reconciled public reference documentation, architecture ownership, inventory, and manifest mappings for Wave 1 public API closure.

## Validation
- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: MINOR
- **Affected Interfaces**: API | CLI payloads | Compatibility matrix | Reference docs
- **Compatibility**: Backward-compatible; no public methods or fields were removed.
- **Breaking Marker**: false
- **Migration Notes**: None; existing `eigen.api.v1` clients remain valid while Product 1.0 clients should adopt the documented envelope fields.

## Release Notes Draft
```markdown
### Added
- Added public proto/reference coverage evidence and envelope ownership decisions for Product 1.0 `eigen.api.v1`.
### Changed
- Clarified public API source-of-truth alignment between protobufs, reference docs, architecture ownership, and Product 1.0 inventory.
### Fixed
- Closed unexplained Wave 1 proto/reference coverage gaps.
```

### W1-02 — Public gRPC envelopes, version negotiation, and compatibility rejection

## Summary
- Added canonical Product 1.0 `ApiRequestEnvelope` for public gRPC requests and attached it to public Job, Device, and Knowledge Base request surfaces.
- Implemented and documented deterministic version negotiation, envelope derivation from metadata/auth context, structured compatibility rejection details, `SubmitJob` idempotency digest semantics, and System API ownership responsibilities.

## Validation
- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: MINOR
- **Affected Interfaces**: API | CLI payloads | Compatibility matrix | Metrics
- **Compatibility**: Backward-compatible
- **Breaking Marker**: false
- **Migration Notes**: None; legacy MVP clients may continue to rely on transport metadata/default derivation while Product 1.0 clients can send the envelope explicitly.

## Release Notes Draft
```markdown
### Added
- Added Product 1.0 public request envelope fields for contract version, request identity, idempotency identity, trace context, deadline, tenant/project scope, and client version, including read-side JobService requests.

### Changed
- Implemented and documented version-negotiation rejection behavior and normalized `SubmitJob` idempotency digest semantics for public gRPC.

### Fixed
- Aligned public gRPC reference documentation with proto and System API runtime behavior for request envelopes, `reservation_id`, `QueryDecisionLogs`, canonical job states, and stream replay errors.
```

### W1-03 — SubmitJob idempotency, payload limits, and request persistence

## Summary
- Implemented persisted `SubmitJob` idempotency records keyed by the Product 1.0 envelope/metadata identity and normalized payload digest.
- Enforced public payload limits before internal forwarding and added bounded outcome metrics for accepted, replayed, conflict, and limit paths.

## Validation
- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: MINOR
- **Affected Interfaces**: API | JobSpec | Metrics
- **Compatibility**: Backward-compatible for same-key/same-payload retries; canonical conflict status is `FAILED_PRECONDITION`.
- **Breaking Marker**: false
- **Migration Notes**: Clients reusing an idempotency key with a different normalized payload must handle `FAILED_PRECONDITION`; operators should configure persistence path/TTL for restart-safe replay.

## Release Notes Draft
```markdown
### Added
- Added persisted `SubmitJob` idempotency records, restart-safe replay evidence, configurable TTL, and bounded submit outcome metrics.
### Changed
- Normalized idempotency comparison over Product 1.0 public envelopes and payload digests before dispatch.
### Fixed
- Rejected same-key/different-payload submissions canonically and enforced public payload limits before internal forwarding.
```

### W1-04 — JobSpec 1.0 schema, parser/normalizer, canonical digest, and fixtures

## Summary
- Added JobSpec 1.0 JSON Schema, positive/negative/future-compatible fixtures, parser/normalizer, canonical JSON, and stable digest evidence.
- Aligned System API and CLI submission mapping for native `eigen.os/v1` and legacy `eigen.os/v0.1` migration inputs.

## Validation
- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: MINOR
- **Affected Interfaces**: JobSpec | CLI payloads | System API SubmitJob mapping | AQO packaging
- **Compatibility**: Backward-compatible; native `eigen.os/v1` is added and documented `eigen.os/v0.1` inputs continue to normalize through migration metadata.
- **Breaking Marker**: false
- **Migration Notes**: Prefer `apiVersion: eigen.os/v1` and `spec.program.path`/`spec.program.source`; legacy `spec.program_path` and inline string `spec.program` remain accepted as v0.1 migration inputs.

## Release Notes Draft
```markdown
### Added
- Added JobSpec 1.0 schema, fixtures, parser/normalizer, canonical digest, and CLI/System API conformance coverage.
### Changed
- Normalized legacy JobSpec inputs into Product 1.0 SubmitJob payload metadata with explicit migration reporting.
### Fixed
- Rejected unsafe or incomplete JobSpec inputs deterministically with field-level violations.
```

### W1-05 — Canonical public error model and error mapping conformance

## Summary
- Implemented canonical public error status construction with stable `ErrorInfo.reason`, retryability metadata, and structured details for public negative paths.
- Added conformance coverage for validation, auth, idempotency conflict, version mismatch, payload limit, deadline, cancellation, unavailable, and internal error mappings.

## Validation
- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: MINOR
- **Affected Interfaces**: API | CLI payloads | Error model | Metrics
- **Compatibility**: Backward-compatible canonicalization; public errors are more deterministic without removing supported requests.
- **Breaking Marker**: false
- **Migration Notes**: Clients should branch on canonical gRPC status plus `google.rpc.ErrorInfo.reason` and `retryable` metadata instead of parsing raw messages.

## Release Notes Draft
```markdown
### Added
- Added canonical public error conformance for validation, auth, idempotency conflict, version mismatch, payload limit, deadline, cancellation, unavailable, and internal failures.
### Changed
- Standardized public retryability metadata and structured detail shapes for negative paths.
### Fixed
- Prevented raw internal exceptions, filesystem paths, provider-private payloads, and stack traces from being exposed at the public boundary.
```

### W1-06 — CLI/SDK public submission conformance baseline

## Summary
- Added CLI Product 1.0 submission payload normalization for file-based and inline JobSpec inputs.
- Documented SDK obligations for public envelopes, deterministic request/idempotency keys, trace context propagation, and negative-test parity.

## Validation
- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: MINOR
- **Affected Interfaces**: CLI payloads | JobSpec | API | SDK conformance
- **Compatibility**: Backward-compatible Product 1.0 envelope and JobSpec normalization added for CLI submissions; inline and file-backed JobSpecs are accepted.
- **Breaking Marker**: false
- **Migration Notes**: Prefer Product 1.0 public payloads with canonical envelope fields; legacy bare CLI submit request JSON remains present only as a compatibility shim during migration.

## Release Notes Draft
```markdown
### Added
- Added CLI public submission payload normalization, deterministic default request/idempotency keys, trace context propagation, and SDK negative-test obligations.
### Changed
- Aligned CLI file and inline submissions with Product 1.0 public envelopes and JobSpec canonicalization.
### Fixed
- Closed CLI/API parity gaps for public submission conformance evidence.
```

### W1-07 — Public API observability markers and trace continuity smoke gate

## Summary
- Added bounded public API contract marker counters and compatibility aliases for Prometheus output.
- Verified trace/request correlation from Product 1.0 envelope or metadata through System API request logging and metrics.

## Validation
- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: MINOR
- **Affected Interfaces**: Metrics | API | CLI/SDK trace propagation
- **Compatibility**: Backward-compatible additive metrics and correlation behavior; existing metrics are retained.
- **Breaking Marker**: false
- **Migration Notes**: None; Product 1.0 clients should continue sending W3C `traceparent` via metadata or `ApiRequestEnvelope.traceparent`.

## Release Notes Draft
```markdown
### Added
- Added bounded public API contract marker counters and trace continuity smoke evidence from public envelope/metadata through System API request handling.
### Changed
- Normalized public contract-version/outcome metric labels to bounded values.
### Fixed
- Preserved request and trace correlation in public API smoke coverage.
```

### W1-08 — Wave 1 compatibility report, migration notes, and release evidence bundle

## Summary
- Completed the Wave 1 compatibility ledger, migration notes, consolidated release notes, release readiness checklist, exit evidence bundle, and implemented-slice manifest/inventory updates.
- Verified that W1-01 through W1-07 acceptance criteria map to objective evidence and that no Wave 1 compatibility row has unknown version impact or breaking-marker values.

## Validation
- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: NONE
- **Affected Interfaces**: Compatibility matrix | Release governance | Inventory
- **Compatibility**: Backward-compatible documentation and release-evidence closure only.
- **Breaking Marker**: false
- **Migration Notes**: None; no new runtime behavior was introduced by the evidence bundle.

## Release Notes Draft
```markdown
### Added
- Added complete Wave 1 compatibility, migration, readiness, release-note, and exit-evidence records.
### Changed
- Updated Product 1.0 manifest/inventory status for Wave 1 implemented public-boundary slices.
### Fixed
- Removed unknown Version Impact, Breaking Marker, and evidence entries from Wave 1 closure documentation.
```
