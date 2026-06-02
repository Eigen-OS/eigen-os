# Product 1.0 Wave 2 Compatibility Report

**Status:** Draft template for Wave 2 closure
**Scope:** Kernel/QRTX lifecycle authority, internal API alignment, System API delegation, orchestration DAG, cancellation/deadline/retry semantics, and observability evidence
**Version policy:** `docs/development/product-1.0-version-policy.md`
**Issue pack:** `docs/development/product-1.0-wave-2-issue-pack.md`
**Evidence bundle:** `docs/development/product-1.0-wave-2-exit-evidence-bundle.md`
**Created:** 2026-06-02

---

## 1. Compatibility rules

Wave 2 changes follow these rules:

1. Internal API changes that remove, rename, or change documented KernelGateway methods, fields, metadata requirements, lifecycle states, event semantics, retry/deadline behavior, or result-reference behavior are **breaking** and require `Version Impact: MAJOR`.
2. Kernel state-machine changes that alter accepted transitions, terminal-state precedence, replay semantics, or invalid-transition errors are **breaking** unless only additive and backward-compatible.
3. Public `eigen.api.v1` behavior from Wave 1 must remain compatible. Any public breaking change requires a separate public RFC/ADR and must not be hidden in Wave 2.
4. Additive internal fields, metrics, event types, or trace attributes use `MINOR` when old consumers continue to function.
5. Documentation-only or non-semantic fixes use `PATCH` or `NONE` according to the Product 1.0 version policy.
6. Every breaking change requires migration notes, release notes, conformance fixture updates, and exit evidence.
7. Every changed Product 1.0 contract mapping must update `contracts/product-1.0/manifest.json` and `docs/development/product-1.0-contract-inventory.md` in the same implementation PR.

---

## 2. Issue compatibility ledger

| Issue | Version Impact | Affected Interfaces | Compatibility | Breaking Marker | Migration Notes | Release Notes Draft | Evidence |
|---|---|---|---|---|---|---|---|
| W2-01 Internal KernelGateway contract matrix and canonical state machine | TBD | Internal API; Kernel state; Compatibility matrix | TBD | TBD | TBD | TBD | W2-E01 |
| W2-02 Durable/replayable kernel job state store and transition validator | TBD | Kernel state; Migration docs | TBD | TBD | TBD | TBD | W2-E02 |
| W2-03 System API lifecycle delegation cutover to Kernel/QRTX | TBD | Public API facade; Internal API; Kernel state | TBD | TBD | TBD | TBD | W2-E03 |
| W2-04 Product 1.0 orchestration DAG control-plane skeleton | TBD | Kernel state; Internal API; Trace context | TBD | TBD | TBD | TBD | W2-E04 |
| W2-05 Deadline propagation and cancellation fan-out | TBD | Internal API; Kernel state; Metrics; Trace context | TBD | TBD | TBD | TBD | W2-E05 |
| W2-06 Retry governance tied to canonical retryability | TBD | Kernel state; Internal API; Metrics; Error mapping | TBD | TBD | TBD | TBD | W2-E06 |
| W2-07 Orchestration observability and trace continuity gate | TBD | Metrics; Trace context; Compatibility matrix | TBD | TBD | TBD | TBD | W2-E07 |
| W2-08 Wave 2 compatibility report, migration notes, and exit evidence bundle | TBD | Compatibility matrix; Migration docs | TBD | TBD | TBD | TBD | W2-E08 |

---

## 3. Required migration-note content for MAJOR internal changes

Any `Version Impact: MAJOR` Wave 2 issue must include:

- old internal method/field/state/behavior,
- new Product 1.0 method/field/state/behavior,
- affected service owners,
- migration sequence,
- compatibility/deprecation window if any,
- conformance fixtures that prove old behavior is rejected, translated, or legacy-gated,
- operational rollback or replay implications,
- public API impact statement proving Wave 1 clients remain compatible or linking the separate public breaking-change approval.

---

## 4. Closure requirements

Before Wave 2 can close:

- no completed issue row may contain `TBD`, empty compatibility text, or missing evidence links;
- every `Breaking Marker=true` row must have migration notes;
- every MAJOR row must have release-note text under `### Changed` or `### Removed`;
- public Wave 1 regression evidence must be linked in W2-E03 or W2-E08;
- manifest and inventory updates must be linked for all concrete proto/schema/conformance path changes.
