# Eigen-Lang showcase: broad H2 demo

This example is the broadest **runnable** showcase in the repository for the current Eigen-Lang compiler/runtime path.
It demonstrates the documented surface that is already wired end-to-end, and it names the remaining contract-level surfaces explicitly so the example stays honest.

## What is exercised in `program.eigen.py`

- `@hybrid_program(...)` with `compiler`, `target`, `shots`, `optimization_level`, `seed`, `noise_model`, and `metadata`.
- Symbolic parameters via `Param`.
- `QubitRegister` and `ClassicalRegister` declarations.
- Declarative dataset loading via `load_dataset(...)`.
- Core circuit gates that currently lower deterministically: `rx`, `ry`, `rz`, `cx`.
- `Observable` + `ExpectationValue` for the quantum cost.
- Classical optimization orchestration via `minimize(..., method="COBYLA")`.

## What is documented but not lowered yet

The reference docs also describe auxiliary decorators and extra gate families. They are useful to keep in the design surface, but the current compiler lowering path is intentionally narrower than the docs:

- auxiliary decorators: `@quantum_circuit`, `@ansatz`, `@cost_function`, `@benchmark`
- additional gates: `h`, `x`, `y`, `z`, `cz`, `swap`, `ccx`

## Run

```bash
cd examples/advanced/eigen_lang_showcase
npx eigen submit -f job.yaml
```

Or, if your CLI is already on the PATH:

```bash
eigen submit -f job.yaml
eigen watch <job_id>
eigen results <job_id>
```

## Why there are two program files

- `program.eigen.py` is the editable source file used by the CLI.
- `program.eigen` is the same showcase in the canonical Eigen-Lang source format used by examples and fixtures.
