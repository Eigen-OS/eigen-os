# Mapping Eigen‑Lang → AQO (MVP v0.1)

Eigen‑Lang compiles to **AQO** (Abstract Quantum Operations). This page defines the mapping rules.

## High-level mapping
- `QubitRegister(n)` → AQO logical allocation: `alloc_qubits(n)`
- Measurement → `measure(qubits, c_register)`
- `ExpectationValue(...)` → `expectation(observable, measurement)` (or a macro expanded by Kernel)
- `minimize(...)` → expands into a hybrid loop in Kernel (compiler emits a “hybrid plan” marker + circuit template)

## Canonical IR
AQO JSON is the canonical interchange format in MVP (see `docs/reference/formats/aqo.md`).
