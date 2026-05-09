# Eigen‑Lang standard library (MVP v0.1)

> **Status snapshot (as of 2026-05-09):** this page is synchronized with the current compiler implementation and architecture docs. It distinguishes what is **implemented now** from what is **documented as intent / missing** so the current system state is explicit.
## 1) Stable contract baseline (implemented now)

These symbols are part of the practical MVP contract used by the compiler/runtime path today.

### Decorators
- `@hybrid_program(...)` — required entrypoint marker (exactly one per source file).

### Types / constructors detected by compiler path
- `Param(name, init=None)`
- `ExpectationValue(circuit, observable)` *(currently used as hybrid/observable marker in AQO metadata path, not full semantic lowering)*
- `minimize(cost_fn, init_params, max_iters=..., tol=..., optimizer=...)` *(currently used as hybrid-plan marker; loop semantics are expanded by runtime/kernel path)*

### Gate-level callable subset currently lowered deterministically to AQO
- `rx(..., theta=...)`
- `ry(..., theta=...)`
- `rz(..., theta=...)`
- `cx(...)`

## 2) Documented but not compiler-frozen in MVP implementation

The following symbols appear in architecture-level language vision/examples, but are **not part of the compiler-frozen MVP lowering contract** today:

- `QubitRegister(n)`
- `ClassicalRegister(n)`
- `Observable(...)`
- `Ansatz(...)`
- `@quantum_circuit`
- `@ansatz`
- `@cost_function`
- `QuantumModel(...)`
- `SupervisedTask(...)`

Use these only as forward-looking/design-level constructs until conformance-backed implementation and reference freezing are completed.

## 3) Current behavioral notes (important)

- Compiler frontend is AST-only and non-executing.
- Exactly one `@hybrid_program` is mandatory.
- Dynamic runtime control flow (`if`/`for`/`while`/`match`/etc.) is currently rejected in MVP compiler validation.
- `ExpectationValue(...)` and `minimize(...)` are recognized for intent/metadata, but full optimizer + observable IR semantics are still partial.

## 4) What is missing to fully freeze this stdlib contract

To “fix the system state” and avoid drift, we still need:

1. **Normative stdlib matrix (single source of truth)**
   - Per symbol: `Implemented`, `Rejected`, or `Planned`, with fixture/test references.
2. **Conformance parity**
   - Positive fixture for every symbol marked implemented, negative fixture for every rejected category.
3. **Reason-code determinism**
   - Stable machine-readable diagnostics for unsupported vs invalid symbol usage.
4. **Docs sync gate in CI**
   - Automatic check preventing contradictions between architecture pages, this reference page, and compiler behavior.

Until those items are complete, MVP is operational but language-surface contract remains partially under-specified for some documented symbols.
