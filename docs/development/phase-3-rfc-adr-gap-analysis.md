# Phase-3 RFC/ADR Coverage Check (Benchmarking Platform)

- **Date:** 2026-04-27
- **Scope checked:** `rfcs/`, `docs/adr/`, `docs/rfcs-pointer.md`, `docs/roadmap.md`
- **Result:** ❌ **Not enough RFC/ADR coverage for Phase-3 yet**.

## Executive summary

Phase-3 goals are documented at roadmap level, but there is no dedicated accepted RFC package for benchmark run/compare/history contracts, and there are no Phase-3 ADRs yet. The current RFC/ADR set is sufficient for MVP-3 runtime execution but not sufficient for Phase-3 benchmarking standardization.

## What exists today

### RFCs available

- MVP-3 RFC set exists (`0016`, `0017`, `0018`) and covers runtime execution, results retrieval, and observability gates.
- No dedicated RFC is currently scoped to Phase-3 benchmark contracts.

### ADRs available

- ADR index currently ends at `0007` (MVP-3 release readiness/runtime contracts).
- No ADR dedicated to Phase-3 benchmark architecture/contracts exists.

## Gap matrix

| Area | Needed for Phase-3 | Present now | Gap |
| --- | --- | --- | --- |
| Benchmark run contract | RFC + compatibility policy | No dedicated RFC | Missing |
| Dataset ingestion schema/provenance contract | RFC + migration policy | No dedicated RFC | Missing |
| Comparison/history semantics | RFC + methodology guarantees | No dedicated RFC | Missing |
| Implemented contract decisions in ADR | ADR(s) synchronized with RFC outcomes | No Phase-3 ADR | Missing |
| Index/pointer documentation | Explicit Phase-3 package links | Not present | Missing |

## Minimum required package to close the gap

1. **Phase-3 RFC set (minimum 3 docs):**
   - `benchmark run contract`
   - `dataset ingestion + manifest contract`
   - `compare/history contract + methodology`
2. **Phase-3 ADR set (minimum 1 umbrella ADR or 2-3 focused ADRs):**
   - Operational decision records for implemented RFC outcomes.
3. **Docs synchronization:**
   - Update `docs/rfcs-pointer.md` and `docs/adr/README.md` when RFC/ADR package lands.

## Recommended issue mapping

- `P3-09` (RFC package)
- `P3-10` (ADR synchronization + release readiness)

## Closure criteria for this gap-check

This document can be marked resolved when all are true:

- Phase-3 RFC package is merged with explicit statuses.
- At least one Phase-3 ADR references implemented RFC outcomes.
- RFC pointer and ADR index include Phase-3 sections.
