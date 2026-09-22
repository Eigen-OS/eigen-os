# Product 1.0 Wave 3 RFC/ADR Gap Analysis

**Status:** Wave 3 governance review template  
**Created:** 2026-06-05  
**Source of truth:** `docs/architecture/components/compiler.md`; `docs/reference/eigen-lang.md`; `docs/reference/formats/aqo.md`; `docs/reference/formats/qfs-layout.md`

---

## 1. Purpose

This document checks whether Wave 3 can be implemented using the existing normative documentation, or whether a new RFC/ADR is required before coding begins.

The default assumption for Wave 3 is:

- the architecture and reference docs are already normative enough to implement the compiler closure work;
- no new RFC/ADR is required unless the implementation needs to **change** the current contract, not merely implement it.

---

## 2. Gap ledger

| Gap | Current source of truth | Is a new RFC/ADR required? | Action |
|---|---|---|---|
| Eigen-Lang accepted subset and forbidden constructs | `docs/architecture/components/compiler.md`; `docs/reference/eigen-lang.md` | No, if the implementation stays within the documented subset | Implement parser/allowlist tests; update reference text only if clarification is needed |
| Compiler request shape and JobSpec mapping | `docs/architecture/components/compiler.md`; `docs/reference/jobspec.md`; `docs/reference/api/grpc-internal.md` | No, if the mapping is additive and conforms to the current contract | Align proto/messages and keep migration notes for any breaking internal caller assumptions |
| AQO canonical schema and deterministic serialization | `docs/reference/formats/aqo.md` | No, if the implementation emits the documented canonical form | Add schema/test artifacts if the machine-readable form is missing |
| Compiler artifact persistence through QFS | `docs/reference/formats/qfs-layout.md`; `docs/architecture/components/qfs.md` | No, if the path contract is an implementation of the documented layout | Add path/metadata fixtures and update docs if path wording is ambiguous |
| Compiler observability and bounded telemetry | `docs/reference/orchestration-observability-contract.md`; `docs/reference/cluster-runtime-observability-contract.md` | No, if metrics and traces stay within the documented bounded-label model | Implement metrics/tests; update docs only for missing examples |
| Any request to broaden the accepted language, relax safety, or change AQO semantics | Current normative docs | **Yes** | Create or update an RFC and an ADR before changing the contract |

---

## 3. Decision

Wave 3 can proceed without a new RFC/ADR if the implementation work stays within the current source-of-truth documents and only adds missing fixtures, tests, and code paths.

A new RFC/ADR becomes necessary only when one of the following is true:

1. the accepted Eigen-Lang subset must expand beyond the documented v1.0 contract,
2. the AQO contract must change in a way that alters canonical bytes or semantic invariants,
3. the QFS artifact layout must be redefined rather than implemented,
4. the compiler safety model must be relaxed or otherwise changed,
5. the internal compiler request contract must break compatibility in a way that needs governance approval beyond ordinary migration notes.

---

## 4. Implementation recommendation

Proceed with the Wave 3 issue pack first. Create or revise an RFC/ADR only if one of the issues uncovers a true contract mismatch that cannot be resolved by implementation, tests, or documentation updates alone.
