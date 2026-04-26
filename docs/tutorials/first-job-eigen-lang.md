# First job in Eigen-Lang

## Goal

Run a minimal submit → status → watch → results cycle using the MVP-3 runtime CLI contract:

- `job.yaml`
- `program.eigen.py`

Example directory: `examples/basic/vqe_cycle/`.

## Steps

1. Open the example directory.

```bash
cd examples/basic/vqe_cycle
```

2. (Recommended) install local CLI launcher once:

```bash
../../../scripts/install-eigen-cli.sh
```

Run this command without `sudo`.

3. Check `job.yaml`:

- `apiVersion: eigen.os/v0.1`
- `kind: QuantumJob`
- `metadata.name`
- `spec.target`
- source via `spec.program_path` (or omit it to use default `program.eigen.py`)

4. Submit a job.

```bash
eigen submit -f job.yaml
```

5. Track status updates.

```bash
eigen watch <job_id>
```

6. Check one-shot status at any time.

```bash
eigen status <job_id>
```

7. Fetch final output.

```bash
eigen results <job_id>
```

## CLI runtime behavior (MVP-3)

- `eigen status <job_id>` returns current lifecycle state and exits `0` for valid requests.
- `eigen watch <job_id>` streams transitions and exits on terminal state.
- `eigen results <job_id>` exits `0` for `DONE`, non-zero for `ERROR|CANCELLED|TIMEOUT`.

## Common validation errors

- `apiVersion` mismatch → use exactly `eigen.os/v0.1`.
- `spec.program_path` path traversal / missing file → keep a safe relative path and ensure file exists.
- invalid entrypoint → keep one `@hybrid_program` and match `spec.entrypoint`.
