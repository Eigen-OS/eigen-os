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

- [ ] RFC 0051 status is accepted or explicitly approved for implementation.
- [ ] ADR 0037 is synchronized with RFC 0051.
- [ ] Every Wave 7a issue includes the required Summary, Validation, Versioning & Compatibility, and Release Notes Draft blocks.
- [ ] Product 1.0 manifest/inventory are updated for any concrete optimizer or observability mapping changes.
- [ ] Every MAJOR or breaking change has migration notes and release evidence.
- [ ] Compatibility report has no unresolved `TBD` values for completed issues.

## Runtime and integration gates

- [ ] Optimizer service is reachable through Kernel/QRTX handoff.
- [ ] Deterministic fallback is tested for unavailable/low-confidence paths.
- [ ] Optimization candidate traces include objective, score breakdown, topology context, model version, confidence, and fallback reason.
- [ ] Observability metrics are bounded and stable.
- [ ] Quality regression gates fail the wave when fixtures regress.

## Evidence gates

- [ ] Evidence bundle links commands, fixtures, generated artifacts, and known limitations.
- [ ] Wave 8 handoff states that knowledge/learning can consume optimizer output without contract redesign.
