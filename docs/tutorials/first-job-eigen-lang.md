# First job in Eigen-Lang

## Goal

Run a minimal submit → watch → results cycle using the canonical MVP-2 package:

- `job.yaml`
- `program.eigen.py`

Example directory: `examples/basic/vqe_cycle/`.

## Steps

1. Open the example directory.

```bash
cd examples/basic/vqe_cycle
```

2. Check `job.yaml`:

- `apiVersion: eigen.os/v0.1`
- `kind: QuantumJob`
- `metadata.name`
- `spec.target`
- source via `spec.program_path` (or omit it to use default `program.eigen.py`)

3. Submit a job.

```bash
eigen submit -f job.yaml
```

4. Track status updates.

```bash
eigen watch <job_id>
```

5. Fetch final output.

```bash
eigen results <job_id>
```

## Common validation errors

- `apiVersion` mismatch → use exactly `eigen.os/v0.1`.
- `spec.program_path` path traversal / missing file → keep a safe relative path and ensure file exists.
- invalid entrypoint → keep one `@hybrid_program` and match `spec.entrypoint`.
