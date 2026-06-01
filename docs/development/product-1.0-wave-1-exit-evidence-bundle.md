# Product 1.0 Wave 1 Exit Evidence Bundle

**Status:** Template for Wave 1 closure evidence  
**Scope:** Public API, JobSpec, CLI payloads, canonical errors, public metrics, and migration evidence  
**Created:** 2026-06-01

---

## 1. Evidence index

| Evidence ID | Requirement | Command / artifact | Expected result | Actual result | Owner | Link |
|---|---|---|---|---|---|---|
| W1-E01 | Public proto/reference coverage matrix | TBD | Matrix has no unexplained gaps | TBD | API Platform | TBD |
| W1-E02 | Public envelope/version negotiation conformance | TBD | Compatible accepted; incompatible rejected canonically | TBD | System API | TBD |
| W1-E03 | SubmitJob idempotency conformance | TBD | Replay returns same job; conflict fails canonically | TBD | System API | TBD |
| W1-E04 | JobSpec schema/parser/normalizer conformance | TBD | CLI and API produce identical canonical digest | TBD | CLI + System API | TBD |
| W1-E05 | Public error mapping conformance | TBD | Status, reason, retryability, and details match reference | TBD | System API | TBD |
| W1-E06 | CLI/SDK submission conformance | TBD | File and inline JobSpec payloads match Product 1.0 contract | TBD | Developer Experience | TBD |
| W1-E07 | Public marker metrics and trace continuity | TBD | Bounded metrics and trace/request correlation present | TBD | Observability | TBD |
| W1-E08 | Compatibility report and migration notes | `docs/development/product-1.0-wave-1-compatibility-report.md` | No unresolved completed-issue `TBD` values | TBD | Governance | TBD |

---

## 2. Required evidence record format

Each completed evidence item must include:

- exact command(s) run,
- repository commit SHA,
- generated schema/proto artifact paths when applicable,
- fixture paths and fixture digests when applicable,
- pass/fail output summary,
- known limitations,
- migration-note link for breaking behavior,
- release-note draft link.

---

## 3. Wave 1 acceptance mapping

| Acceptance criterion | Evidence IDs |
|---|---|
| Public proto and reference semantics are reconciled | W1-E01 |
| Public envelope/version negotiation is deterministic | W1-E02 |
| `SubmitJob` idempotency and payload limits are enforced | W1-E03 |
| JobSpec 1.0 parser/normalizer/digest is deterministic | W1-E04 |
| Public errors are canonical and retryability is fixture-tested | W1-E05 |
| CLI/SDK baseline matches public contract | W1-E06 |
| Public marker metrics and trace continuity are observable | W1-E07 |
| Compatibility and migration evidence is complete | W1-E08 |

---

## 4. Closure statement

Wave 1 may be marked complete only after every evidence row has an actual result, owner sign-off, and link to reproducible artifacts. If any issue has `Breaking Marker=true`, the corresponding migration notes must be included before Wave 2 starts.
