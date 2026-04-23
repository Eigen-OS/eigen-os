# Basic VQE example (2-qubit Hamiltonian)

This example demonstrates a minimal Variational Quantum Eigensolver (VQE) setup that can be
submitted to the local simulator.

## Files

- `program.eigen.py` — parameterized 2-qubit ansatz + expectation-value objective.
- `job.yaml` — JobSpec for `eigen submit`.

## Run

From this folder:

```bash
eigen submit -f job.yaml
eigen watch <job_id>
eigen results <job_id>
```

## What to expect

The exact values depend on simulator internals and optimizer seed, but healthy runs usually show:

- **Counts distribution** that changes across iterations and then stabilizes.
- **Objective / energy trend** that decreases in early iterations, then plateaus.
- **Convergence behavior** where the best energy improves only slightly near the end.

Example qualitative trend:

- iter 1: energy ≈ -0.15
- iter 6: energy ≈ -0.62
- iter 12: energy ≈ -0.79
- iter 20+: energy oscillates in a narrow band near the current minimum

## Troubleshooting

- If submission fails with validation errors, confirm `apiVersion`, `kind`, and `target` in `job.yaml`.
- If compiler errors mention entrypoint, verify `spec.entrypoint: main` and `def main()` in `program.eigen.py`.
- If objective does not improve, increase `max_iters` and/or shots in `job.yaml`.
