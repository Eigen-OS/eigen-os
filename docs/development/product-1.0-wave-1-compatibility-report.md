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
| W1-02 Public gRPC envelopes, version negotiation, and compatibility rejection | TBD | API; CLI payloads; Compatibility matrix | TBD | TBD | TBD | TBD | TBD |
| W1-03 SubmitJob idempotency, payload limits, and request persistence | TBD | API; JobSpec; Metrics | TBD | TBD | TBD | TBD | TBD |
| W1-04 JobSpec 1.0 schema, parser/normalizer, canonical digest, and fixtures | TBD | JobSpec; CLI payloads; AQO | TBD | TBD | TBD | TBD | TBD |
| W1-05 Canonical public error model and error mapping conformance | TBD | API; CLI payloads; Metrics | TBD | TBD | TBD | TBD | TBD |
| W1-06 CLI/SDK public submission conformance baseline | TBD | CLI payloads; JobSpec; API | TBD | TBD | TBD | TBD | TBD |
| W1-07 Public API observability markers and trace continuity smoke gate | TBD | Metrics; API | TBD | TBD | TBD | TBD | TBD |
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
- [ ] Public metrics/trace smoke evidence attached or linked.
- [ ] Manifest/inventory diff reviewed for changed schema/proto/test mappings.
- [ ] Release notes draft copied from every issue and consolidated.
