# Phase-4 RFC/ADR Coverage Check (Intelligent Runtime)

- **Date:** 2026-04-28
- **Scope checked:** `rfcs/`, `docs/adr/`, `docs/rfcs-pointer.md`, `docs/roadmap.md`, `docs/development/`
- **Result:** ✅ **Required Phase-4 RFC package is accepted and indexed; ADR synchronization remains pending implementation.**- **Result:** ✅ **Required Phase-4 RFC package is accepted and indexed; ADR synchronization remains pending implementation.**

## Executive summary

Phase-4 roadmap goals are documented, and the required governance package (RFC 0023/0024/0025) is now accepted and indexed. ADR synchronization remains pending because no Phase-4 RFC has reached `Implemented` status yet.

## What exists today

### RFCs available

- RFC 0023 (Accepted): backend selection scoring contract v1.
- RFC 0024 (Accepted): explainability API contract v1.
- RFC 0025 (Accepted): scheduling policy engine contract v1.

### ADRs available

- ADR coverage currently ends at Phase-3 (`0008`, `0009`, `0010`).
- No Phase-4 ADRs exist yet (expected until at least one Phase-4 RFC reaches `Implemented`).

## Gap matrix

| Area | Needed for Phase-4 | Present now | Gap |
| --- | --- | --- | --- |
| Backend scoring contract | RFC + compatibility policy | RFC 0023 (Accepted) | RFC package done (P4-08); implementation in progress (P4-01) |
| Explainability API contract | RFC + stable envelopes for `/explain/*` | RFC 0024 (Accepted) | RFC package done (P4-08); implementation in progress (P4-03/P4-04) |
| Scheduling policy engine contract | RFC + deterministic resolution guarantees | RFC 0025 (Accepted) | RFC package done (P4-08); implementation in progress (P4-02) |
| Implemented decisions mirrored in ADRs | ADR(s) after implementation | Not started | Open (P4-09) |
| Release closure artifacts | compatibility report + readiness checklist | Not started | Open (P4-09) |
| Index/pointer synchronization | docs links to Phase-4 package | Updated | Closed by P4-08 |

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

## Acceptance baseline locked on 2026-04-28

The following inputs are now locked and reflected across RFC 0023/0024/0025 and the Phase-4 plan:

1. canonical backend scoring feature allowlist + disallowed feature classes;
2. deterministic policy priority ladder and default `user_intent_weights`;
3. fixed explainability depth model (`L1_USER`, `L2_ADMIN`, `L3_FORENSIC`) with required fields;
4. initial decision and explain latency/error targets for compatibility and test planning.

Remaining open work is implementation and ADR synchronization once any RFC transitions to `Implemented`.
