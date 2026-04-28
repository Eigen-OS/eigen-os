# Phase-4 Release Readiness Checklist

- **Issue:** P4-09 — ADR Synchronization and Phase-4 Release Meta (#244)
- **Release line:** `0.9.0`
- **Last updated:** 2026-04-28
- **Owners:** Intelligent runtime maintainers
- **Gate status:** ✅ Ready (compatibility + ADR synchronization package signed)

## 1) Milestone and DoD closure

- [x] All Phase-4 issues (`P4-01` … `P4-09`) are linked to milestone `Phase-4 Intelligent Runtime`.
- [x] Every issue has explicit DoD verification comments/evidence in PRs.
- [x] Each Phase-4 PR includes:
  - [x] `Version impact`
  - [x] `Compatibility`
  - [x] `Migration notes` (or explicit `None`)

## 2) RFC/ADR synchronization gates

- [x] Every implemented Phase-4 RFC has synchronized ADR coverage:
  - [x] RFC 0023 ↔ ADR 0011
  - [x] RFC 0024 ↔ ADR 0012
  - [x] RFC 0025 ↔ ADR 0013
- [x] ADR index is updated: [`../adr/README.md`](../adr/README.md).
- [x] RFC pointer is updated: [`../rfcs-pointer.md`](../rfcs-pointer.md).

## 3) Contract and determinism quality gates

- [x] Backend scoring contract tests are green.
- [x] Scheduling policy contract tests are green.
- [x] Explainability API contract tests are green.
- [x] Deterministic replay checks for runtime decisions are green.

## 4) Documentation and release package

- [x] Phase-4 compatibility report is finalized: [`phase-4-compatibility-report.md`](phase-4-compatibility-report.md).
- [x] Phase-4 release checklist is published (this file).
- [x] Phase-4 docs are linked from [`README.md`](README.md), RFC pointer docs, and ADR index.

## 5) Locked supported version matrix

| Surface | Locked version for `0.9.0` |
| --- | --- |
| Backend scoring contract | `1.0.0` |
| Scoring profile schema | `1.0.0` |
| Scheduling policy contract | `1.0.0` |
| Policy bundle schema | `1.0.0` |
| Explainability API contract | `1.0.0` |

## 6) Formal release constraints

- [x] Release is **not** marked Ready without signed compatibility report.
- [x] Release is **not** marked Ready without signed RFC/ADR synchronization check.
- [x] Decision artifacts and explain responses include explicit version markers.
- [x] Governance docs release package version is bumped and locked to `0.9.0`.

## 7) Sign-off

- **Compatibility package signed by:** Intelligent runtime maintainers
- **ADR synchronization signed by:** Architecture maintainers
- **Final gate decision:** ✅ Phase-4 release can be marked **Ready**.
