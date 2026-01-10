# Eigen‑Lang standard library (MVP v0.1)

This page defines what functions/classes are part of Eigen‑Lang in MVP.

## Core decorator
- `@hybrid_program(...)` — defines the program entrypoint

## Core types
- `QubitRegister(n)`
- `ClassicalRegister(n)`
- `Param(name, init=None)`
- `Observable(...)`
- `Ansatz(...)`

## Core operations (DSL)
- `ExpectationValue(circuit, observable)`
- `minimize(cost_fn, init_params, max_iters=..., tol=..., optimizer=...)`

Anything not listed here is not part of the stable language contract in v0.1.
