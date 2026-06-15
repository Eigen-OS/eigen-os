# H2 VQE demo (simulator)

A polished VQE example for the local simulator. This variant keeps the source fully Eigen-Lang-native and avoids external optimizer imports so it stays aligned with the current language contract.

## What it shows

- a small two-qubit ansatz with entanglement,
- a simulator-targeted hybrid program,
- a declarative energy objective tied to the H2 / STO-3G demo label,
- a classical optimization loop using the Eigen-Lang `minimize()` surface.

## Files

- `program.eigen` / `program.eigen.py` — simulator-targeted H2 demo program.
- `job.yaml` — JobSpec for `eigen submit`.

## Run

From this folder:

```bash
eigen submit -f job.yaml
eigen watch <job_id>
eigen results <job_id>
```

## Expected behavior

A healthy simulator run should produce:

- non-empty counts,
- several optimization iterations,
- a decreasing objective trend in the early steps,
- stable terminal results once the optimizer converges.

## Notes

- The Hamiltonian label (`H2_sto-3g`) is intentionally declarative.
- The example stays within the Eigen-Lang surface documented in `docs/reference/eigen-lang.md`.
