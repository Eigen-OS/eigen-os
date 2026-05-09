# Eigen‑Lang syntax (v0.1)

> **Status snapshot (as of 2026-05-09):** this document is synchronized with `docs/architecture/*` and current Eigen‑Lang reference docs. It explicitly separates **implemented now** syntax rules from **TODO / missing** items required to freeze the system state.

Eigen‑Lang in MVP is a **Python DSL**. A “program” is a Python file with one canonical hybrid entrypoint (`@hybrid_program`) that must pass strict frontend validation.

## 1) File conventions

### Implemented now

- Recommended canonical filename: `program.eigen.py` (tooling defaults rely on this convention).
- Source must be valid **UTF‑8** and valid Python syntax.
- Frontend applies bounded parsing/AST limits (see `allowed-subset.md`) before lowering.
- Entrypoint override via submission metadata (`job.yaml`) is supported by platform contracts.

### TODO / missing

- Freeze and document whether canonical filename is strict or advisory in all compiler paths.
- Publish one normative table for file-level validation fields/reason codes.

## 2) Entrypoint rules

### Implemented now

- Exactly **one** function decorated with `@hybrid_program(...)` is required.
- Entrypoint name must be a valid Python identifier.
- Missing/multiple entrypoints are validation errors (`INVALID_ARGUMENT` contract path).

Minimal example (supported baseline shape):

```python
from eigen_lang import hybrid_program, Param, rx, ry, rz, cx

@hybrid_program(target="sim", shots=1000)
def main():
    theta = Param("theta")
    rx(0, theta)
    ry(1, 0.2)
    cx(0, 1)
    rz(1, theta)
    return {"ok": True}
```

### TODO / missing

- Lock stable error split for recognized-but-unsupported entrypoint patterns (`UNIMPLEMENTED` vs `INVALID_ARGUMENT`).
- Add explicit conformance fixtures for all single-entrypoint edge cases.

## 3) Imports
### Implemented now

- MVP allows only Eigen‑Lang package imports (`eigen_lang` roots and supported symbols).
- Non-allowlisted import roots are rejected by validation policy.

### TODO / missing

- Publish canonical import allowlist matrix (module/symbol level) shared with `standard-library.md` and tests.
- Freeze alias/attribute-chain behavior as one normative rule set.

## 4) Literals, parameters, and expressions

### Implemented now

- Numeric literals (int/float) are accepted within guarded frontend constraints.
- String literals are accepted for declarative identifiers/labels (not dynamic execution).
- Parameter declarations via `Param(...)` are supported in current lowering subset.
- Supported gate-call subset for deterministic AQO lowering includes `rx`, `ry`, `rz`, `cx`.

### TODO / missing

- Document exact numeric bounds and overflow/precision validation behavior in one place.
- Publish full per-symbol support status for stdlib calls (`implemented`, `planned`, `rejected`).

## 5) Control flow (MVP status)

### Implemented now

- Current compiler validation path rejects runtime/dynamic Python control flow patterns (`if`, `for`, `while`, `match`, etc.) outside accepted lowering subset.

### Docs-level intent requiring closure

- Other docs mention potential compile-time-constant control flow as optional MVP behavior; this is not yet frozen as implemented syntax surface.

### TODO / missing

- Decide and freeze whether compile-time-constant control flow belongs to MVP or post‑MVP.
- Add conformance fixtures that prove the final chosen policy.

## 6) Validation and diagnostics surface

### Implemented now

- Syntax/validation failures are reported through structured `INVALID_ARGUMENT` diagnostics (field-violation style).
- Rejections are deterministic for identical source + compiler config.

### TODO / missing

- Freeze machine-readable reason-code taxonomy and field naming for syntax/AST validation.
- Add release drift checks so diagnostics contract remains stable.

## 7) What is still missing to fully freeze system state

To fully “зафиксировать состояние системы” for syntax contracts, mandatory closure items are:

1. **Single syntax compatibility matrix**
   - One table for file rules, entrypoint forms, imports, calls, expressions, control flow with statuses (`Implemented`, `Rejected`, `Planned`) and fixture IDs.
2. **Conformance parity**
   - Positive fixture per documented supported syntax construct + negative fixture per rejection class.
3. **Deterministic diagnostics contract**
   - Stable reason-code taxonomy and field naming across compiler docs/tests.
4. **Cross-doc synchronization gate**
   - CI/doc check preventing contradictions between `syntax.md`, `allowed-subset.md`, `semantics.md`, `standard-library.md`, and `docs/architecture/*`.

Until these are complete, MVP syntax remains operational for the implemented subset, but specification/compliance is still partially under-specified.
