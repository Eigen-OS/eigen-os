# Phase-4 RFC/ADR Coverage Check (Intelligent Runtime)

- **Date:** 2026-04-28
- **Scope checked:** `rfcs/`, `docs/adr/`, `docs/rfcs-pointer.md`, `docs/roadmap.md`, `docs/development/`
- **Result:** ⚠️ **Phase-4 RFC draft package is prepared; ADR synchronization is pending implementation.**

## Executive summary

Phase-4 roadmap goals are documented, and a draft governance package now exists for scoring, explainability APIs, and policy engine contracts. ADR synchronization is intentionally pending because no Phase-4 RFC is yet in `Implemented` status.

## What exists today

### RFCs available

- RFC 0023 (Draft): backend selection scoring contract v1.
- RFC 0024 (Draft): explainability API contract v1.
- RFC 0025 (Draft): scheduling policy engine contract v1.

### ADRs available

- ADR coverage currently ends at Phase-3 (`0008`, `0009`, `0010`).
- No Phase-4 ADRs exist yet (expected until at least one Phase-4 RFC reaches `Implemented`).

## Gap matrix

| Area | Needed for Phase-4 | Present now | Gap |
| --- | --- | --- | --- |
| Backend scoring contract | RFC + compatibility policy | RFC 0023 (Draft) | In progress (P4-01/P4-08) |
| Explainability API contract | RFC + stable envelopes for `/explain/*` | RFC 0024 (Draft) | In progress (P4-03/P4-04/P4-08) |
| Scheduling policy engine contract | RFC + deterministic resolution guarantees | RFC 0025 (Draft) | In progress (P4-02/P4-08) |
| Implemented decisions mirrored in ADRs | ADR(s) after implementation | Not started | Open (P4-09) |
| Release closure artifacts | compatibility report + readiness checklist | Not started | Open (P4-09) |
| Index/pointer synchronization | docs links to Phase-4 package | Partially updated | In progress |

## Minimum required package to close the gap

1. **Phase-4 RFC set (required):**
   - `backend selection scoring contract` (RFC 0023)
   - `explainability API contract` (RFC 0024)
   - `scheduling policy engine contract` (RFC 0025)

2. **Phase-4 ADR set (required when RFCs become implemented):**
   - One ADR per implemented contract area, or explicit split/merge rationale.

3. **Release closure docs (required before phase closure):**
   - `docs/development/phase-4-release-readiness-checklist.md`
   - `docs/development/phase-4-compatibility-report.md`

4. **Docs synchronization:**
   - Keep `docs/development/README.md` and `docs/rfcs-pointer.md` aligned with RFC/ADR status transitions.

## Recommended issue mapping

- `P4-08` (RFC package)
- `P4-09` (ADR synchronization + release readiness)

## Data still required from maintainers

To move Phase-4 RFCs from `Draft` to `Accepted`, the following inputs are still required:

1. canonical scoring feature list and constraints;
2. policy priority defaults by environment profile;
3. explainability detail level and redaction policy;
4. latency/error SLO targets for explain APIs and decision engine.
