# Product 1.0 Wave 1 Execution Plan

**Status:** Wave 1 implementation guide  
**Parent plan:** `docs/development/product-1.0-contract-alignment-plan.md`  
**Wave 0 baseline:** `docs/development/product-1.0-wave-0-execution-plan.md`  
**Inventory:** `docs/development/product-1.0-contract-inventory.md`  
**Version policy:** `docs/development/product-1.0-version-policy.md`  
**Issue pack:** `docs/development/wave-1/product-1.0-wave-1-issue-pack.md`  
**Created:** 2026-06-01

---

## 1. Goal

Wave 1 closes the **public Product 1.0 boundary** before lifecycle ownership moves deeper into Kernel/QRTX. The wave is complete only when public gRPC, JobSpec ingestion, client/CLI submission behavior, canonical errors, version negotiation, idempotency, and public observability markers are contract-tested as one externally stable surface.

Wave 1 intentionally permits MAJOR contract updates when the Wave 0 inventory proves that the documented Product 1.0 behavior and current proto/service behavior cannot be reconciled in a backward-compatible way. Every MAJOR update must follow `docs/development/product-1.0-version-policy.md` and include migration notes, compatibility evidence, and release-note draft text.

---

## 2. In-scope contract surfaces

| Surface | Inventory row | Primary owner | Wave 1 target |
|---|---|---|---|
| Public gRPC API (`eigen.api.v1`) | Public gRPC API | System API; client SDKs/CLI | Proto/reference coverage, public envelopes, version negotiation, idempotency, pagination/result handles, and public conformance tests. |
| JobSpec | JobSpec | System API; CLI; Kernel/QRTX packaging boundary | Versioned schema, parser/normalizer, deterministic digest, fixtures, and CLI/API parity. |
| Canonical error model | Canonical error model | All public services, led by System API | Public validation/auth/idempotency/version/payload errors map to canonical status and structured details. |
| Error mapping matrix | Error mapping matrix | All public services, led by System API | Machine-readable public mapping coverage and retryability/reason-code conformance. |
| Public REST API envelope | Public REST API envelope | System API; API gateway | Scope decision only: implement as mirror if accepted, or explicitly defer/remove from Product 1.0 Wave 1 scope. |
| Authorization and security policy | Authorization and security policy | Security & Isolation; System API | Public auth context normalization hooks and fail-closed error semantics; full authz engine remains Wave 9. |
| Orchestration observability | Orchestration observability | System API; Observability; Kernel/QRTX | Public contract marker metric, bounded labels, request/trace correlation, and smoke conformance. |

---

## 3. Required deliverables

| Deliverable | Path | Acceptance criteria |
|---|---|---|
| Wave 1 issue pack | `docs/development/wave-1/product-1.0-wave-1-issue-pack.md` | Every implementation issue contains Summary, Validation, required Versioning & Compatibility block, and Release Notes Draft. |
| Wave 1 RFC/ADR gap analysis | `docs/development/wave-1/product-1.0-wave-1-rfc-adr-gap-analysis.md` | Declares whether existing RFCs/ADRs are sufficient and links required Product 1.0 public-boundary RFC/ADR updates. |
| Public boundary RFC | `rfcs/0049-product-1.0-public-api-jobspec-error-boundary.md` | Normative requirements for public envelopes, JobSpec canonicalization, idempotency, errors, and compatibility. |
| Public boundary ADR | `docs/adr/0035-product-1.0-public-api-jobspec-error-boundary.md` | Accepted governance decision for Wave 1 implementation. |
| Compatibility report template | `docs/development/wave-1/product-1.0-wave-1-compatibility-report.md` | Captures version impact, affected interfaces, breaking markers, migrations, fixture evidence, and release notes for every issue. |
| Release readiness checklist | `docs/development/wave-1/product-1.0-wave-1-release-readiness-checklist.md` | Checklist maps Wave 1 exit criteria to objective gates. |
| Exit evidence bundle template | `docs/development/wave-1/product-1.0-wave-1-exit-evidence-bundle.md` | Defines evidence records for tests, schema/proto diffs, conformance fixtures, release notes, and migration notes. |
| Development index updates | `docs/development/README.md`; `docs/adr/README.md` | Product 1.0 Wave 1 planning package and ADR are discoverable. |

---

## 4. Execution order

1. **Governance lock:** accept/update RFC 0049 and ADR 0035 before implementation commits that change public behavior.
2. **Coverage matrix:** compare `docs/reference/api/grpc-public.md`, `docs/reference/jobspec.md`, `docs/reference/error-model.md`, and `docs/reference/error-mapping.md` against current public proto and System API behavior.
3. **Proto/schema slice:** update public proto and JobSpec schema artifacts together, including generated bindings if the repository owns them.
4. **Gateway behavior slice:** implement version negotiation, payload limits, auth-context normalization hooks, idempotency semantics, and canonical error normalization in System API.
5. **Client slice:** update CLI/SDK submission path to send canonical envelopes, trace context, idempotency metadata, and normalized JobSpec payloads.
6. **Conformance slice:** add positive, negative, replay, idempotency-conflict, version-mismatch, payload-limit, and retryability mapping tests.
7. **Observability slice:** add public API contract marker metrics, bounded labels, and trace/request correlation evidence.
8. **Compatibility closure:** update the manifest/inventory when mappings move from planned to concrete, complete the compatibility report, and attach exit evidence.

---

## 5. Wave 1 issue map

| Issue | Priority | Contract surfaces | Expected version impact |
|---|---|---|---|
| W1-01 Public proto/reference coverage matrix and envelope decisions | P0 | API; CLI payloads; Plugin envelopes only if public gateway forwards plugin metadata | MAJOR or MINOR, depending on removals/renames vs additive fields. |
| W1-02 Public gRPC envelopes, version negotiation, and compatibility rejection | P0 | API; CLI payloads; Compatibility matrix | MAJOR if existing clients must add required fields; otherwise MINOR. |
| W1-03 SubmitJob idempotency, payload limits, and request persistence | P0 | API; JobSpec; Metrics | MINOR for additive idempotency; MAJOR if conflicting legacy behavior changes. |
| W1-04 JobSpec 1.0 schema, parser/normalizer, canonical digest, and fixtures | P0 | JobSpec; CLI payloads; AQO handoff metadata | MAJOR if accepted JobSpec semantics narrow; otherwise MINOR. |
| W1-05 Canonical public error model and error mapping conformance | P0 | API; CLI payloads; Metrics | MAJOR if status/reason behavior changes; otherwise MINOR/PATCH. |
| W1-06 CLI/SDK public submission conformance baseline | P1 | CLI payloads; JobSpec; API | MINOR unless legacy CLI payloads are removed. |
| W1-07 Public API observability markers and trace continuity smoke gate | P1 | Metrics; API | MINOR for additive metrics; MAJOR only if metric names in frozen contract change. |
| W1-08 Wave 1 compatibility report, migration notes, and release evidence bundle | P1 | Compatibility matrix; API; CLI payloads; JobSpec; Metrics | NONE/PATCH unless closure discovers unresolved drift. |

---

## 6. Definition of done

Wave 1 is 100% complete when:

- public proto methods/messages and documented public API semantics are reconciled or deviations are documented with an accepted migration decision,
- every public request has a canonical envelope or a documented exception,
- version negotiation rejects incompatible requests deterministically,
- `SubmitJob` idempotency semantics are persistent, configurable, and fixture-tested,
- JobSpec 1.0 parsing, normalization, canonical digest, and CLI/API parity are fixture-tested,
- public validation/auth/version/idempotency/payload errors use canonical status details and retryability mapping,
- public contract marker metrics and trace/request correlation are emitted with bounded labels,
- the Product 1.0 manifest/inventory are updated for new concrete proto/schema/conformance paths,
- the Wave 1 compatibility report and exit evidence bundle are complete,
- all Wave 1 issues include the required Versioning & Compatibility and Release Notes Draft blocks.

---

## 7. Handoff to Wave 2

Wave 2 must not start moving lifecycle authority from System API to Kernel/QRTX until Wave 1 evidence proves that external clients can submit, watch, cancel, and retrieve public result references without relying on System API-internal state details. Any Wave 2 API shape discovered during implementation must be expressed as an internal contract update rather than leaking new lifecycle semantics into public Wave 1 payloads without RFC/ADR review.
