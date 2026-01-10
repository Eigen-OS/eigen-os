# Eigen‑Lang syntax (v0.1)

Eigen‑Lang in MVP is a **Python DSL**. A “program” is a Python file containing exactly one entrypoint function marked with `@hybrid_program`.

## 1) File conventions
- Canonical filename: `program.eigen.py` (recommended; tooling assumes this by default).
- The file must be **UTF‑8** encoded.
- The program must be **self‑contained** (no network, no file I/O; see allowed subset).

## 2) Entrypoint rules
- Exactly **one** function decorated with `@hybrid_program(...)`.
- Entrypoint name must be a valid Python identifier.
- Tooling must accept explicit entrypoint override in `job.yaml`.

Example (minimal):

```python
from eigen_lang import hybrid_program, QubitRegister, ClassicalRegister

@hybrid_program(target="sim", shots=1000)
def main():
    q = QubitRegister(2)
    c = ClassicalRegister(2)
    # TODO: build circuit (MVP subset)
    return {"ok": True}
```

## 3) Imports
Only imports from the Eigen‑Lang standard library are allowed in MVP:
- `eigen_lang` (and its submodules)

All other imports are prohibited by default (see allowlist).

## 4) Literals and parameters
- Numeric literals: int/float (bounded; implementation must enforce limits).
- Strings: for labels only (not for dynamic execution).
- Parameters: represented by `Param(...)` objects.

## 5) Control flow (MVP)
MVP supports **static** Python control flow that can be resolved at compile time:
- simple `for` loops with constant bounds (optional; can be postponed to Post‑MVP)
- `if` statements with compile‑time constants (optional)

Any runtime‑dependent Python control flow is rejected in MVP.
