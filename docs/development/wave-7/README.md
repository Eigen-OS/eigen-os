# Product 1.0 Wave 7 Documentation Index

**Wave:** Product 1.0 Wave 7 — Neuro-Symbolic Compiler and GNN Optimizer
**Status:** Planning baseline
**Parent execution plan:** `docs/development/product-1.0-contract-alignment-plan.md`

---

## Core planning documents

- `product-1.0-wave-7-execution-plan.md`
- `product-1.0-wave-7-issue-pack.md`
- `product-1.0-wave-7-rfc-adr-gap-analysis.md`

---

## Closure-target documents

These documents should be completed when Wave 7 is ready to close:

- `product-1.0-wave-7-compatibility-report.md`
- `product-1.0-wave-7-release-readiness-checklist.md`
- `product-1.0-wave-7-exit-evidence-bundle.md`

---

## Scope

Wave 7 closes the compiler and optimization boundary for Product 1.0. It aligns the neuro-symbolic compiler pipeline, Eigen-Lang lowering, AQO/IR normalization, GNN optimizer scoring and policy selection, artifact handoff, and the deterministic validation gates required for release.

---

## Primary source-of-truth references

- `docs/architecture/components/compiler.md`
- `docs/architecture/components/gnn-optimizer.md`
- `docs/architecture/components/neuro-symbolic-core.md`
- `docs/reference/eigen-lang.md`
- `docs/reference/formats/aqo.md`
- `docs/reference/api/grpc-internal.md`
- `docs/reference/compiler-observability-contract.md`
- `docs/reference/error-model.md`
- `docs/architecture/components/observability.md`
- `docs/architecture/components/qfs.md`

---

## Dependencies carried into Wave 7

- Wave 1 public API, JobSpec, and error model closure
- Wave 2 Kernel/QRTX lifecycle authority closure
- Wave 4 QFS lineage / checkpoint / reservation closure
- Wave 5 Resource Manager and multi-device execution closure
- Wave 6 Driver Manager and QDriver final contract closure
- Product 1.0 inventory / manifest synchronization