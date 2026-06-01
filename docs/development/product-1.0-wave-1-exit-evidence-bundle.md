# Product 1.0 Wave 1 Exit Evidence Bundle

**Status:** Complete for Wave 1 closure evidence
**Scope:** Public API, JobSpec, CLI payloads, canonical errors, public metrics, and migration evidence
**Completed:** 2026-06-01

---

## 1. Evidence index

| Evidence ID | Requirement | Command / artifact | Expected result | Actual result | Owner | Link |
|---|---|---|---|---|---|---|
| W1-E01 | Public proto/reference coverage matrix | `python3 scripts/ci/check-docs-links.py`; `python3 scripts/ci/check-product-1-0-manifest.py` | Matrix has no unexplained gaps | PASS: public API proto/reference sources, inventory, and manifest mappings resolve for Product 1.0 Wave 1 | API Platform | `docs/reference/api/grpc-public.md`; `docs/development/product-1.0-contract-inventory.md`; `contracts/product-1.0/manifest.json` |
| W1-E02 | Public envelope/version negotiation conformance | `PYTHONPATH=src/services/system-api/src pytest src/services/system-api/tests/test_public_envelope_versioning.py` | Compatible accepted; incompatible rejected canonically | PASS: missing versions default to Product 1.0; malformed/future/unsupported versions reject with canonical public reasons | System API | `src/services/system-api/tests/test_public_envelope_versioning.py` |
| W1-E03 | SubmitJob idempotency conformance | `PYTHONPATH=src/services/system-api/src pytest src/services/system-api/tests/test_idempotency.py` | Replay returns same job; conflict fails canonically | PASS: replay, conflict, envelope idempotency key, persistence, TTL, malformed version, and unsupported version paths are covered | System API | `src/services/system-api/tests/test_idempotency.py` |
| W1-E04 | JobSpec schema/parser/normalizer conformance | `PYTHONPATH=src/services/system-api/src pytest src/services/system-api/tests/test_jobspec_parser.py`; `cargo test --manifest-path src/rust/Cargo.toml -p cli` | CLI and API produce equivalent canonical payloads/digests | PASS: System API fixtures cover deterministic canonical JSON/digest, legacy migration, future-compatible sections, and negative validation; CLI tests cover file and inline Product 1.0 submissions | CLI + System API | `docs/reference/schemas/jobspec-1.0.schema.json`; `docs/reference/fixtures/jobspec/1.0/`; `src/services/system-api/tests/test_jobspec_parser.py`; `src/rust/apps/cli/src/jobspec.rs` |
| W1-E05 | Public error mapping conformance | `PYTHONPATH=src/services/system-api/src pytest src/services/system-api/tests/test_public_error_conformance.py` | Status, reason, retryability, and details match reference | PASS: validation, auth, idempotency conflict, version mismatch, payload limit, deadline, cancellation, unavailable, and internal mappings have canonical status/details | System API | `docs/reference/error-model.md`; `docs/reference/error-mapping.md`; `src/services/system-api/tests/test_public_error_conformance.py` |
| W1-E06 | CLI/SDK submission conformance | `cargo test --manifest-path src/rust/Cargo.toml -p cli` | File and inline JobSpec payloads match Product 1.0 contract | PASS: CLI conformance tests normalize minimal inline and full file-backed fixtures with canonical envelopes | Developer Experience | `src/rust/apps/cli/src/jobspec.rs`; `src/rust/apps/cli/README.md`; `docs/architecture/components/client-sdks.md` |
| W1-E07 | Public marker metrics and trace continuity | `PYTHONPATH=src/services/system-api/src pytest src/services/system-api/tests/test_observability_smoke.py` | Bounded metrics and trace/request correlation present | PASS: Prometheus payload exposes bounded public contract markers and traceparent/request IDs correlate through System API request handling | Observability | `src/services/system-api/tests/test_observability_smoke.py`; `src/services/system-api/src/system_api/observability.py` |
| W1-E08 | Compatibility report and migration notes | `python3 scripts/ci/check-product-1-0-wave1-closure.py` | No unresolved completed-issue `TBD` or unknown values | PASS: W1-01 through W1-08 have complete Version Impact, Breaking Marker, migration notes, release notes, and objective evidence links | Governance | `docs/development/product-1.0-wave-1-compatibility-report.md`; `docs/development/product-1.0-wave-1-release-readiness-checklist.md` |

---

## 2. Required evidence record format

Each completed evidence item includes or points to:

- exact command(s) run,
- repository commit SHA: recorded by the closure commit for this bundle,
- generated schema/proto artifact paths when applicable,
- fixture paths and fixture digests when applicable,
- pass/fail output summary,
- known limitations,
- migration-note link for breaking behavior,
- release-note draft link.

Known limitations for Wave 1 closure:

- No Wave 1 breaking change exists, so no MAJOR migration window is required.
- Public REST mirror and non-Wave-1 Product 1.0 contracts remain governed by later waves and are not counted as Wave 1 blockers.
- Operator auth policy beyond public-boundary error normalization remains in the broader Product 1.0 security track.

---

## 3. Wave 1 acceptance mapping

| Acceptance criterion | Evidence IDs | Status |
|---|---|---|
| Public proto and reference semantics are reconciled | W1-E01 | Complete |
| Public envelope/version negotiation is deterministic | W1-E02 | Complete |
| `SubmitJob` idempotency and payload limits are enforced | W1-E03 | Complete |
| JobSpec 1.0 parser/normalizer/digest is deterministic | W1-E04 | Complete |
| Public errors are canonical and retryability is fixture-tested | W1-E05 | Complete |
| CLI/SDK baseline matches public contract | W1-E06 | Complete |
| Public marker metrics and trace continuity are observable | W1-E07 | Complete |
| Compatibility and migration evidence is complete | W1-E08 | Complete |

---

## 4. Closure statement

Wave 1 is complete: every evidence row has an actual result, owner, and reproducible artifact link; W1-01 through W1-07 acceptance criteria map to objective evidence; and no issue has `Breaking Marker=true`. Wave 2 may start with public clients depending on Product 1.0 envelopes, canonical errors, JobSpec 1.0 normalization, and bounded public observability markers instead of MVP-only request semantics.
