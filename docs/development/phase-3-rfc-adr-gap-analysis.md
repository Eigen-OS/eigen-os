# Phase-3 RFC/ADR Coverage Check (Benchmarking Platform)

- **Date:** 2026-04-27
- **Scope checked:** `rfcs/`, `docs/adr/`, `docs/rfcs-pointer.md`, `docs/roadmap.md`
- **Result:** ❌ **Not enough RFC/ADR coverage for Phase-3 yet**.

## Executive summary

Phase-3 goals are documented at roadmap level. Initial governance coverage now exists for benchmark run lifecycle via RFC 0020 + ADR 0008, but the full benchmark contract package (dataset + compare/history) is still missing. The current RFC/ADR set is sufficient for MVP-3 runtime execution and P3-01 core lifecycle only.

## What exists today

### RFCs available

- MVP-3 RFC set exists (`0016`, `0017`, `0018`) and covers runtime execution, results retrieval, and observability gates.
- RFC 0020 now covers benchmark run lifecycle core v1.

### ADRs available

- ADR index currently ends at `0007` (MVP-3 release readiness/runtime contracts).
- ADR 0008 now records implemented benchmark run lifecycle core v1.

## Gap matrix

| Area | Needed for Phase-3 | Present now | Gap |
| --- | --- | --- | --- |
| Benchmark run contract | RFC + compatibility policy | RFC 0020 + ADR 0008 | Closed (P3-01) |
| Dataset ingestion schema/provenance contract | RFC + migration policy | No dedicated RFC | Missing |
| Comparison/history semantics | RFC + methodology guarantees | No dedicated RFC | Missing |
| Implemented contract decisions in ADR | ADR(s) synchronized with RFC outcomes | ADR 0008 for P3-01 | Partial |
| Index/pointer documentation | Explicit Phase-3 package links | Updated for RFC 0020/ADR 0008 | Partial |

## Minimum required package to close the gap

1. **Phase-3 RFC set (remaining):**
   - `dataset ingestion + manifest contract`
   - `compare/history contract + methodology`
2. **Phase-3 ADR set (remaining):**
   - Operational decision records for dataset/compare/history outcomes when implemented.
3. **Docs synchronization:**
   - Update `docs/rfcs-pointer.md` and `docs/adr/README.md` as remaining RFC/ADR package lands.

## Recommended issue mapping

- `P3-09` (RFC package)
- `P3-10` (ADR synchronization + release readiness)

## Closure criteria for this gap-check

This document can be marked resolved when all are true:

- Phase-3 RFC package is merged with explicit statuses.
- At least one Phase-3 ADR references implemented RFC outcomes.
- RFC pointer and ADR index include Phase-3 sections.
