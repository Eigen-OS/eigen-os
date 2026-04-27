# Phase-3 RFC/ADR Coverage Check (Benchmarking Platform)

- **Date:** 2026-04-27
- **Scope checked:** `rfcs/`, `docs/adr/`, `docs/rfcs-pointer.md`, `docs/roadmap.md`
- **Result:** ✅ **Required Phase-3 RFC package for stable contracts is complete.**

## Executive summary

Phase-3 goals are documented at roadmap level. Governance coverage now includes benchmark run lifecycle, dataset ingestion, and comparison/history contracts. The required RFC package for stable Phase-3 benchmark contracts is now complete.

## What exists today

### RFCs available

- MVP-3 RFC set exists (`0016`, `0017`, `0018`) and covers runtime execution, results retrieval, and observability gates.
- RFC 0020 covers benchmark run lifecycle core v1.
- RFC 0021 covers dataset ingestion and manifest/provenance contract v1.
- RFC 0022 covers comparison methodology and history contract v1.

### ADRs available

- ADR index currently ends at `0007` (MVP-3 release readiness/runtime contracts).
- ADR 0008 now records implemented benchmark run lifecycle core v1.

## Gap matrix

| Area | Needed for Phase-3 | Present now | Gap |
| --- | --- | --- | --- |
| Benchmark run contract | RFC + compatibility policy | RFC 0020 + ADR 0008 | Closed (P3-01) |
| Dataset ingestion schema/provenance contract | RFC + migration policy | RFC 0021 | Closed (P3-02/P3-09) |
| Comparison/history semantics | RFC + methodology guarantees | RFC 0022 | Closed (P3-04/P3-05/P3-09) |
| Implemented contract decisions in ADR | ADR(s) synchronized with RFC outcomes | ADR 0008 for P3-01 | Partial (dataset/compare/history ADR sync tracked by P3-10) |
| Index/pointer documentation | Explicit Phase-3 package links | Updated for RFC 0020/0021/0022 | Closed for RFC package |

## Minimum required package to close the gap

✅ **Completed for RFC package**

1. **Phase-3 RFC set:**
   - `benchmark run lifecycle contract` (RFC 0020)
   - `dataset ingestion + manifest contract` (RFC 0021)
   - `compare/history contract + methodology` (RFC 0022)

⏳ **Remaining for full RFC+ADR closure (P3-10):**

2. **Phase-3 ADR set (remaining):**
   - Operational decision records for dataset/compare/history outcomes when implementation ADR sync lands.
3. **Docs synchronization (ADR index):**
   - Ensure `docs/adr/README.md` is updated when new ADRs are accepted.

## Recommended issue mapping

- `P3-09` (RFC package)
- `P3-10` (ADR synchronization + release readiness)

## Closure criteria for this gap-check

RFC-package closure status on 2026-04-27:

- ✅ Phase-3 RFC package is merged with explicit statuses (RFC 0020/0021/0022).
- ✅ RFC pointer includes the full Phase-3 RFC package.
- ⏳ Additional ADR synchronization for dataset/compare/history remains tracked by P3-10.
