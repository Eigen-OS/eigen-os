# First job in Eigen‑Lang

## Goal

Run a minimal VQE-style hybrid job on the local simulator using the canonical package:

- `program.eigen.py`
- `job.yaml`

This tutorial uses `examples/basic/vqe_cycle/`.

## Steps

1. Go to the example directory.

```bash
cd examples/basic/vqe_cycle
```

2. Inspect the files:

- `program.eigen.py` defines a 2-qubit ansatz with one parameter `theta`.
- `job.yaml` points to `program.eigen.py` via `spec.program_path`.

3. Submit the job.

```bash
eigen submit -f job.yaml
```

Save the returned `job_id`.

4. Stream job progress.

```bash
eigen watch <job_id>
```

5. Fetch final results.

```bash
eigen results <job_id>
```

## Validate output

For this basic VQE run, check two signals:

1. **Counts**: non-trivial bitstring distribution (not all shots in one state unless converged there).
2. **Objective trend**: reported energy generally decreases during the first iterations and then plateaus.

Expected qualitative pattern:

- early iterations: larger energy improvements;
- middle iterations: slower improvement;
- final iterations: small oscillations near best-so-far.

## Troubleshooting

- **`INVALID_ARGUMENT` on submit**: verify `apiVersion: eigen.os/v0.1` and `kind: QuantumJob`.
- **Entrypoint not found**: keep `entrypoint: main` in `job.yaml` and `def main()` in source.
- **No convergence**: increase `spec.metadata.max_iters` and `spec.metadata.shots`.

