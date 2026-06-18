# H2 VQE demo (simulator)

A reproducible VQE example for the local simulator. This variant is designed to be useful beyond a smoke test: it exposes optimizer state, explicit observables, and metadata that make runs comparable across versions.

## What it shows

- a small two-qubit ansatz with entanglement,
- a simulator-targeted hybrid program,
- a declarative energy objective tied to the H2 / STO-3G demo label,
- a classical optimization loop using the Eigen-Lang `minimize()` surface.

## Files

- `program.eigen` / `program.eigen.py` — simulator-targeted H2 benchmark program.
- `job.yaml` — JobSpec for `eigen submit`.

## Run

From this folder:

```bash
eigen submit -f job.yaml
eigen watch <job_id>
eigen results <job_id>
```

## What to expect

A healthy simulator run should produce:

- non-empty counts,
- reproducible results for the same seed and backend configuration,
- a final report with `energy`, `parameters`, `method`, and `optimizer_metadata`,
- stable terminal results that are easy to compare in CI or benchmark runs.

## Notes

- The Hamiltonian is represented as an explicit observable so the example is
  easier to reason about and extend.
- The program returns structured data rather than a bare scalar, which makes it
  more convenient for downstream analysis and regression tracking.
- The example stays within the Eigen-Lang surface documented ineigen-lang.md`.
