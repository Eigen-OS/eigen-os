# Product 1.0 Wave 7a Release Readiness Checklist

**Status:** Wave 7a closure checklist
**Created:** 2026-06-12

## Scope

This checklist closes Product 1.0 Wave 7a and must be completed together with:
- `docs/development/wave-7a/product-1.0-wave-7a-execution-plan.md`
- `docs/development/wave-7a/product-1.0-wave-7a-issue-pack.md`
- `docs/development/wave-7a/product-1.0-wave-7a-compatibility-report.md`
- `docs/development/wave-7a/product-1.0-wave-7a-exit-evidence-bundle.md`
- `docs/development/wave-7a/product-1.0-wave-7a-rfc-adr-gap-analysis.md`
- `rfcs/0051-product-1.0-optimizer-production-path.md`
- `docs/adr/0037-product-1.0-optimizer-production-path.md`

---

## Contract and governance gates

- [x] RFC 0051 status is accepted or explicitly approved for implementation.
- [x] ADR 0037 is synchronized with RFC 0051.
- [x] Every Wave 7a issue includes the required Summary, Validation, Versioning & Compatibility, and Release Notes Draft blocks.
- [x] Product 1.0 manifest/inventory are updated for the documented optimizer and observability mapping changes.
- [x] Every MAJOR or breaking change has migration notes and release evidence.
- [x] Compatibility report has no unresolved `TBD` values for completed issues.

## Runtime and integration gates

- [x] Optimizer service is reachable through Kernel/QRTX handoff.
- [x] Deterministic fallback is tested for unavailable/low-confidence paths.
- [x] Optimization candidate traces include objective, score breakdown, topology context, model version, confidence, and fallback reason.
- [x] Observability metrics are bounded and stable.
- [x] Quality regression gates fail the wave when fixtures regress.

## Evidence gates

- [x] Evidence bundle links commands, fixtures, generated artifacts, and known limitations.
- [x] Wave 8 handoff states that knowledge/learning can consume optimizer output without contract redesign.

## Verification

- CI-equivalent gate: `cd src/services/benchmark-service && PYTHONPATH=src pytest -q tests/test_optimizer_evaluation_harness.py`
- The fixed offline/online fixture remains the regression gate input for W7A-05.
