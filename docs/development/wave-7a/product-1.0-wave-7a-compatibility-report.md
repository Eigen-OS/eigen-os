# Product 1.0 Wave 7a Compatibility Report

**Status:** W7A-05 closure draft; optimizer/intelligent-runtime issue ledger complete for documented implementation slices
**Scope:** Optimizer service wiring, model registry, deterministic fallback, optimization traces, intelligent-runtime observability, and release evidence
**Version policy:** `docs/development/product-1.0-version-policy.md`
**Issue pack:** `docs/development/wave-7a/product-1.0-wave-7a-issue-pack.md`
**Evidence bundle:** `docs/development/wave-7a/product-1.0-wave-7a-exit-evidence-bundle.md`
**Created:** 2026-06-12

---

## 1. Compatibility rules

1. Optimizer service wiring that keeps the contract shape stable is `PATCH` or `MINOR`, depending on whether behavior is additive.
2. Registry/promotion-policy changes are `MINOR` when they remain backward-compatible.
3. Deterministic fallback is `MINOR` when it adds explicit behavior without removing accepted behavior.
4. Metric or label removals/renames are `MAJOR`.
5. Wave 7a does not authorize new public API surfaces.
6. Every breaking change requires migration notes, release notes, conformance updates, and exit evidence.

---

## 2. Issue compatibility ledger

| Issue | Version Impact | Affected Interfaces | Compatibility | Breaking Marker | Migration Notes | Release Notes Draft | Evidence |
|---|---|---|---|---|---|---|---|
| W7A-01 Optimizer service server/client wiring and Kernel/QRTX handoff | MINOR | Internal API; Kernel orchestration; Trace context | Backward-compatible | false | None | Added: real OptimizerService wiring through Kernel/QRTX | W7A-E01 |
| W7A-02 Model registry and version promotion policy | MINOR | Registry policy; Internal API; Compatibility matrix | Backward-compatible | false | None | Added: deterministic promotion, rollback, quarantine policy | W7A-E02 |
| W7A-03 Deterministic fallback and confidence thresholds | MINOR | Internal API; Kernel orchestration; Metrics; Trace context | Backward-compatible | false | None | Added: explicit fallback reason and model-version visibility | W7A-E03 |
| W7A-04 Optimization candidate traces, metrics, and dashboards | TBD | Metrics; Trace context; Dashboard compatibility | TBD | TBD | TBD | TBD | W7A-E04 |
| W7A-05 Quality regression gates and release evidence bundle | PATCH | Compatibility matrix; Migration docs | Backward-compatible | false | None | Added: release evidence bundle and regression gate records | W7A-E05 |
| W7A-06 Inventory/manifest synchronization for Wave 7a surfaces | PATCH | Manifest; Inventory; Governance docs | Backward-compatible | false | None | Added: inventory rows and evidence links for Wave 7a | W7A-E06 |

---

## 3. Compatibility summary

Wave 7a is intended to be implementation-aligned rather than contract-redesign work. The optimizer contract itself stays frozen; the wave promotes it from fixture-backed integration to production path.
