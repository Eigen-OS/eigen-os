# Eigen‑Lang semantics (v0.1)

Eigen‑Lang programs describe a **hybrid workflow**: classical orchestration + quantum circuit evaluations.

## 1) Program model
The entrypoint defines a description that is compiled into a DAG:
- **Quantum nodes**: prepare/transform/measure circuits
- **Classical nodes**: parameter updates, reduction, objective evaluation
- **Edges**: data dependencies (params/results)

In MVP the DAG can be implicit: `minimize(cost_fn, init_params, ...)` expands into a loop:
1) build circuit with parameters
2) execute on target backend
3) compute objective from measurement counts
4) update parameters
5) repeat until convergence or max_iters

## 2) Determinism rules (MVP)
Given the same:
- `program.eigen.py` source,
- `job.yaml` (including seeds/options),
- referenced inputs (by hash),
the compiler must produce the same IR (AQO JSON).

Non‑determinism is allowed only via explicit `seed` in runtime options and only affects sampling/optimization, not compilation output.

## 3) Quantum/classical boundary
- Quantum nodes consume: circuit IR + shots + backend options.
- Quantum nodes produce: measurement results (counts) + metadata.
- Classical nodes consume: results + params, produce: new params or final metrics

## 4) Measurement semantics
- The canonical measurement output is `counts: map<bitstring, int>`.
- Bitstring ordering must be defined by the target mapping policy and exposed in metadata.

## 5) Errors
- Syntax/validation errors are **compile‑time** errors (INVALID_ARGUMENT).
- Backend errors are **runtime** errors (UNAVAILABLE/RESOURCE_EXHAUSTED/FAILED_PRECONDITION as per error mapping).
