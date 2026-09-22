# RFC-0057: Product 1.0 Optimizer Production Path

- Status: Proposed
- Created: 2026-06-12
- Target milestone: Product 1.0 Wave 7a GNN Optimizer and Intelligent Runtime
- Depends on: RFC-0050, RFC-0049, RFC-0048, RFC-0040

## Summary

This RFC defines the Product 1.0 Wave 7a cutover that promotes the GNN Optimizer and intelligent-runtime surfaces from fixture-backed integration to the production execution path.

## Normative requirements

1. Kernel/QRTX MUST be able to invoke the optimizer through the production handoff path.
2. The optimizer contract shape MUST remain frozen for Wave 7a.
3. The model registry MUST have explicit version-promotion policy.
4. Fallback when unavailable or low-confidence MUST be deterministic and observable.
5. Optimization traces MUST include objective, score breakdown, topology context, model version, confidence, and fallback reason.
6. Intelligent-runtime observability markers MUST be emitted with bounded labels.
7. Quality regressions MUST block release when fixtures fail.

+## Rollout plan

1. Add Kernel/QRTX → optimizer service wiring.
2. Add registry/promotion policy.
3. Add deterministic fallback.
4. Add telemetry and dashboards.
5. Close compatibility and evidence docs.
