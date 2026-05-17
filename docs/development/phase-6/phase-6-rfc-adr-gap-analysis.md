# Phase-6 RFC/ADR Coverage Check (Plugin Ecosystem)

- **Date:** 2026-04-29
- **Scope checked:** `rfcs/`, `docs/adr/`, `docs/rfcs-pointer.md`, `docs/roadmap.md`, `docs/development/`
- **Result:** ✅ **Required Phase-6 RFC package is accepted and indexed; ADR synchronization remains the next governance checkpoint.**

## Executive summary

Phase-6 planning is prepared with implementation backlog and contract-oriented RFC package for plugin ecosystem work. Required RFC documents are now accepted (RFC 0029/0030/0031) and indexed in roadmap/development docs; matching ADRs should now be created during implementation stabilization.

## What exists today

### RFCs available

- RFC 0029 (Accepted): plugin SDK and manifest contract v1.
- RFC 0030 (Accepted): plugin lifecycle and runtime isolation contract v1.
- RFC 0031 (Accepted): plugin compatibility and trust policy contract v1.

### ADRs available

- No Phase-6 plugin ADRs yet (expected at acceptance/implementation checkpoint).

## Gap matrix

| Area | Needed for Phase-6 | Present now | Gap |
| --- | --- | --- | --- |
| Plugin SDK + manifest contract | RFC + compatibility policy | RFC 0029 (Accepted) | Closed for RFC package; implementation pending |
| Plugin lifecycle + isolation contract | RFC + security constraints + deterministic loading semantics | RFC 0030 (Accepted) | Closed for RFC package; implementation pending |
| Plugin compatibility + trust policy | RFC + version/trust governance | RFC 0031 (Accepted) | Closed for RFC package; implementation pending |
| Implemented decisions mirrored in ADRs | ADR(s) after implementation | No Phase-6 ADRs yet | Open |
| Release closure artifacts | compatibility report + readiness checklist | Not started | Open |
| Index/pointer synchronization | docs links to Phase-6 package | Updated in planning docs | Closed for planning stage |

## Minimum package required for Phase-6 closure

1. **Phase-6 RFC set (accepted/implemented):**
   - plugin SDK and manifest contract (RFC 0029)
   - plugin lifecycle and runtime isolation contract (RFC 0030)
   - plugin compatibility and trust policy contract (RFC 0031)

2. **Phase-6 ADR set (to be created post-acceptance):**
   - ADR for SDK/manifest contract
   - ADR for lifecycle/isolation contract
   - ADR for compatibility/trust contract

3. **Release closure docs (to publish during execution):**
   - `docs/development/phase-6-release-readiness-checklist.md`
   - `docs/development/phase-6-compatibility-report.md`

4. **Docs synchronization:**
   - ensure `docs/development/README.md`, `docs/rfcs-pointer.md`, and `docs/adr/README.md` reflect status transitions.

## Recommended issue mapping

- `P6-08` (RFC package)
- `P6-09` (ADR synchronization + release readiness package, to open after RFC acceptance)

## Planning baseline on 2026-04-28

The following defaults are fixed for initial Phase-6 planning:

1. plugin artifact compatibility and manifest fields are SemVer-governed;
2. Sigstore/Cosign is fixed as default trust stack (Fulcio/Rekor for public/community plugins);
3. plugin lifecycle semantics require deterministic load ordering and fail-closed conflict behavior;
4. gVisor `runsc` OCI sandbox is fixed as mandatory runtime boundary for GA;
5. Phase-6 GA plugin type set is fixed to `driver`, `compiler_backend`, `optimizer`;
6. Phase-6 work is blocked from closure until RFC acceptance and ADR synchronization are complete.
