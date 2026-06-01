# Product 1.0 Wave 1 Compatibility Report

**Status:** Template for Wave 1 closure  
**Scope:** Public API, JobSpec, CLI payloads, canonical errors, public metrics, and compatibility evidence  
**Version policy:** `docs/development/product-1.0-version-policy.md`  
**Issue pack:** `docs/development/product-1.0-wave-1-issue-pack.md`  
**Created:** 2026-06-01

---

## 1. Compatibility rules

Wave 1 changes must follow these rules:

1. Public behavior changes that remove or rename documented fields, methods, metrics, reason codes, lifecycle-visible states, or required auth/idempotency semantics are **breaking** and require `Version Impact: MAJOR`.
2. Backward-compatible additions use `MINOR` with deterministic defaults.
3. Non-semantic corrections use `PATCH`.
4. Documentation-only planning updates use `NONE` unless they change normative contract language.
5. Every breaking change requires migration notes and a release-note draft.
6. Every changed public contract surface must update the Product 1.0 manifest/inventory when schema, proto, or conformance mappings change.

---

## 2. Issue compatibility ledger

| Issue | Version Impact | Affected Interfaces | Compatibility | Breaking Marker | Migration Notes | Release Notes Draft | Evidence |
|---|---|---|---|---|---|---|---|
| W1-01 Public proto/reference coverage matrix and envelope decisions | TBD | API; CLI payloads; Compatibility matrix | TBD | TBD | TBD | TBD | TBD |
| W1-02 Public gRPC envelopes, version negotiation, and compatibility rejection | MINOR | API; CLI payloads; Compatibility matrix | Backward-compatible | false | None; MVP metadata clients remain accepted by deterministic envelope derivation while Product 1.0 clients may send `ApiRequestEnvelope` directly. | Added Product 1.0 public request envelope and runtime version-negotiation rejection semantics for `eigen.api.v1`. | `proto/eigen/api/v1/types.proto`; `proto/eigen/api/v1/job_service.proto`; `proto/eigen/api/v1/device_service.proto`; `proto/eigen/api/v1/knowledge_base_service.proto`; `src/services/system-api/src/system_api/grpc_impl.py`; `src/services/system-api/tests/test_public_envelope_versioning.py`; `docs/reference/api/grpc-public.md`; `docs/architecture/components/system-api.md` |
| W1-03 SubmitJob idempotency, payload limits, and request persistence | MINOR | API; JobSpec; Metrics | Backward-compatible for same-key/same-payload retries; canonical conflict status is `FAILED_PRECONDITION`. | false | Clients reusing an idempotency key with a different normalized payload must handle `FAILED_PRECONDITION`; configure persistence path/TTL for restart-safe replay. | Added persisted SubmitJob idempotency records with TTL, expanded payload-limit enforcement, and bounded SubmitJob outcome metrics. | `src/services/system-api/src/system_api/grpc_impl.py`; `src/services/system-api/src/system_api/validation.py`; `src/services/system-api/src/system_api/observability.py`; `src/services/system-api/tests/test_idempotency.py`; `docs/reference/api/grpc-public.md`; `docs/architecture/components/system-api.md` |
| W1-04 JobSpec 1.0 schema, parser/normalizer, canonical digest, and fixtures | MINOR | JobSpec; CLI payloads; System API SubmitJob mapping; AQO packaging | Backward-compatible: native `eigen.os/v1` is added and documented `eigen.os/v0.1` inputs continue to normalize through migration metadata. | false | Prefer `apiVersion: eigen.os/v1` and `spec.program.path`/`spec.program.source`; legacy `spec.program_path` and inline string `spec.program` remain accepted as v0.1 migration inputs. | Added JobSpec 1.0 JSON Schema, fixtures, shared System API normalizer/digest behavior, CLI v1 parser support, and compatibility report. | `docs/reference/jobspec.md`; `docs/reference/schemas/jobspec-1.0.schema.json`; `docs/reference/fixtures/jobspec/1.0/`; `src/services/system-api/src/system_api/jobspec_parser.py`; `src/services/system-api/tests/test_jobspec_parser.py`; `src/rust/apps/cli/src/jobspec.rs` |
| W1-05 Canonical public error model and error mapping conformance | TBD | API; CLI payloads; Metrics | TBD | TBD | TBD | TBD | TBD |
| W1-06 CLI/SDK public submission conformance baseline | MINOR | CLI payloads; JobSpec; API; SDK conformance | Backward-compatible Product 1.0 envelope and JobSpec normalization added for CLI submissions; inline and file-backed JobSpecs are accepted. | false | Prefer Product 1.0 public payloads with canonical envelope fields; legacy bare CLI submit request JSON remains present only as a compatibility shim during migration. | Added CLI public submission payload normalization, deterministic default request/idempotency keys, trace context propagation, and SDK negative-test obligations. | `src/rust/apps/cli/src/jobspec.rs`; `src/rust/apps/cli/src/main.rs`; `src/rust/apps/cli/README.md`; `docs/architecture/components/client-sdks.md`; `docs/reference/api/grpc-public.md` |
| W1-07 Public API observability markers and trace continuity smoke gate | MINOR | Metrics; API; CLI/SDK trace propagation | Backward-compatible additive metrics and correlation behavior; existing metrics are retained. | false | None; Product 1.0 clients should continue sending W3C `traceparent` via metadata or `ApiRequestEnvelope.traceparent`. | Added bounded public API contract marker counters and trace continuity smoke evidence from public envelope/metadata through System API request handling. | `src/services/system-api/src/system_api/observability.py`; `src/services/system-api/src/system_api/grpc_impl.py`; `src/services/system-api/tests/test_observability_smoke.py`; `docs/reference/api/grpc-public.md`; `docs/architecture/components/observability.md`; `docs/architecture/components/system-api.md`; `docs/architecture/components/client-sdks.md` |
| W1-08 Wave 1 compatibility report, migration notes, and release evidence bundle | NONE | Compatibility matrix | Backward-compatible | false | None | TBD | This report and exit evidence bundle |

---

## 3. Required migration-note fields for MAJOR changes

When `Breaking Marker=true`, record:

- old behavior or payload shape,
- new behavior or payload shape,
- detection strategy for affected clients,
- migration steps,
- support/deprecation window if legacy behavior remains temporarily available,
- rollback constraints,
- release-note text.

---

## 4. Public boundary evidence checklist

- [ ] Proto/reference coverage matrix attached or linked.
- [ ] JobSpec schema and fixture set attached or linked.
- [ ] Error mapping fixture set attached or linked.
- [ ] CLI/API parity evidence attached or linked.
- [ ] Idempotency replay/conflict evidence attached or linked.
- [x] Public metrics/trace smoke evidence attached or linked.
- [ ] Manifest/inventory diff reviewed for changed schema/proto/test mappings.
- [ ] Release notes draft copied from every issue and consolidated.

## 5. W1-02 completion evidence

Required issue completion block MUST retain and complete this block before closure:

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
