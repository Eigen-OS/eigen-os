# Phase-9C Exit Evidence Bundle

## Purpose

This bundle provides objective, reproducible closure evidence for Phase-9C acceptance criteria and Stage-C gates.

## Acceptance criteria → evidence mapping

| Acceptance criterion | Evidence artifact | Verification expectation |
|---|---|---|
| Phase-9C artifacts are linked from `docs/development/README.md`. | `docs/development/README.md` Phase-9C section links. | Links resolve to issue pack, gap analysis, checklist, compatibility report, and exit evidence bundle. |
| RFC/ADR gap status is current and explicit. | `docs/development/phase-9c/phase-9c-rfc-adr-gap-analysis.md`, `docs/adr/0034-phase9c-multitenant-plugin-boundary-contract-v1.md`. | Gap analysis and ADR state is synchronized with RFC 0048 outcomes. |
| Compatibility matrix includes core-vs-plugin ownership and fallback semantics. | `docs/development/fixtures/phase9c/policy_capability_matrix_v1_1_0.json`. | Matrix version and semantics are explicit, stable, and fixture-versioned. |
| Deterministic core behavior is proven with plugins disabled. | Determinism guards in `policy_capability_matrix_v1_1_0.json`; scheduler fixture evidence referenced from P9C-02 package. | Fixed-input ordering and reason-code output are reproducible. |
| Plugin-failure isolation drills are present and auditable. | Isolation drill references from P9C-04 acceptance package + matrix fallback taxonomy fields. | Timeout/crash/malformed-output classes all map to deterministic kernel fallback behavior. |
| P9C issue acceptance criteria are mapped to objective proof. | `docs/development/phase-9c/phase-9c-issue-pack.md` + this bundle. | Every issue (P9C-01..P9C-07) has an evidence pointer and verification expectation. |

## Required evidence sections

### 1) Deterministic-core-with-plugins-disabled proof

Must include:
- fixture workload identifier and fixed seed;
- admission ordering snapshot digest;
- reason-code output snapshot digest;
- replay command used to reproduce output.

### 2) Plugin-failure-isolation drill report

Must include:
- failure class (`timeout`, `crash`, `malformed_output`);
- plugin identity and version under test;
- fallback path selected by kernel;
- resulting lifecycle and scheduler health assertions.

### 3) Compatibility matrix attestation

Must include:
- matrix schema version and matrix version;
- core-owned vs plugin-owned capability inventory;
- fallback semantics taxonomy and expected action per class.

### 4) Migration notes decision log

Must include:
- SemVer decision for the release package;
- breaking-marker declaration;
- explicit statement whether migration notes are required.

## Sign-off criteria

Phase-9C can be marked closed only if:

1. all mapped evidence links are present and resolvable;
2. deterministic-core and isolation drill evidence is complete;
3. SemVer/compatibility decision is published in the compatibility report.
