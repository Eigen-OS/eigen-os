# Phase-3 Release Readiness Checklist

- **Issue:** P3-10 — ADR Package and Phase-3 Release Readiness Meta (#221)
- **Release line:** `0.8.0`
- **Last updated:** 2026-04-27
- **Owners:** Benchmarking maintainers
- **Gate status:** ✅ Ready (compatibility + ADR synchronization package signed)

## 1) Milestone and DoD closure

- [x] All Phase-3 issues (`P3-01` … `P3-10`) are linked to milestone `Phase-3 Benchmarking Platform`.
- [x] Every issue has explicit DoD verification comments/evidence in PRs.
- [x] Each Phase-3 PR includes:
  - [x] `Version impact`
  - [x] `Compatibility`
  - [x] `Migration notes` (or explicit `None`)

## 2) RFC/ADR synchronization gates

- [x] Every implemented Phase-3 RFC has synchronized ADR coverage:
  - [x] RFC 0020 ↔ ADR 0008
  - [x] RFC 0021 ↔ ADR 0009
  - [x] RFC 0022 ↔ ADR 0010
- [x] ADR index is updated: [`../adr/README.md`](../adr/README.md).
- [x] RFC pointer is updated: [`../rfcs-pointer.md`](../rfcs-pointer.md).

## 3) Contract and determinism quality gates

- [x] Benchmark run lifecycle contract tests are green.
- [x] Dataset ingestion contract tests are green.
- [x] Compare/history contract tests are green.
- [x] Reproducibility and deterministic ordering/pagination checks are green.

## 4) Documentation and release package

- [x] Phase-3 compatibility report is finalized: [`phase-3-compatibility-report.md`](phase-3-compatibility-report.md).
- [x] Phase-3 release checklist is published (this file).
- [x] Phase-3 docs are linked from [`README.md`](README.md) and Phase-3 planning docs.

## 5) Locked supported version matrix

| Surface | Locked version for `0.8.0` |
| --- | --- |
| Benchmark run lifecycle contract | `1.0.0` |
| Dataset manifest schema | `1.0.0` |
| Dataset ingestion contract | `1.0.0` |
| Comparison contract | `1.0.0` |
| Comparison methodology contract | `1.0.0` |
| History contract | `1.0.0` |

## 6) Formal release constraints

- [x] Release is **not** marked Ready without signed compatibility report.
- [x] Release is **not** marked Ready without signed RFC/ADR synchronization check.
- [x] Contract artifacts include explicit version markers in run snapshots, compare outputs, and history entries.
- [x] Service/package version for Phase-3 deliverables is bumped and locked to `0.8.0`.

## 7) Sign-off

- **Compatibility package signed by:** Benchmarking maintainers
- **ADR synchronization signed by:** Architecture maintainers
- **Final gate decision:** ✅ Phase-3 release can be marked **Ready**.
