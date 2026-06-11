# Product 1.0 Wave 6 Documentation Index

**Wave:** Product 1.0 Wave 6 — Driver Manager and QDriver final contract
**Status:** Planning baseline
**Parent execution plan:** `docs/development/product-1.0-contract-alignment-plan.md`

---

## Core planning documents

- `product-1.0-wave-6-execution-plan.md`
- `product-1.0-wave-6-issue-pack.md`
- `product-1.0-wave-6-rfc-adr-gap-analysis.md`

---

## Closure-target documents

These documents should be completed when Wave 6 is ready to close:

- `product-1.0-wave-6-compatibility-report.md`
- `product-1.0-wave-6-release-readiness-checklist.md`
- `product-1.0-wave-6-exit-evidence-bundle.md`

---

## Scope

Wave 6 closes the Driver Manager / QDriver boundary so that provider execution is normalized, replaceable, and safe. The wave aligns the current Driver Manager skeleton with the final QDriver contract, provider matrix governance, sandboxing, secrets handling, and reference simulator behavior.

---

## Primary source-of-truth references

- `docs/architecture/components/driver-manager.md`
- `docs/reference/api/qdriver.md`
- `docs/reference/api/grpc-internal.md`
- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/intelligent-runtime-observability-contract.md`
- `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`
- `rfcs/0045-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`
- `docs/adr/0030-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`
- `docs/adr/0031-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`

---

## Dependencies carried into Wave 6

- Wave 2 Kernel/QRTX lifecycle authority closure
- Wave 4 QFS lineage / checkpoint / reservation closure
- Wave 5 Resource Manager and multi-device execution closure
- Product 1.0 inventory / manifest synchronization
