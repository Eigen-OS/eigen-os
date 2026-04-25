# Quickstart (local simulator)

## Goal

Run a local end-to-end flow (`submit -> status -> watch -> results`) with a minimal 2-qubit VQE example.

Reference example: `examples/basic/vqe_cycle/`.

## What this quickstart validates

This quickstart is verified against the current repository state (MVP scaffold):

- CLI binary: `src/rust/apps/cli` (`eigen` command)
- Local mocked System API behavior in CLI internals (no external services required for this smoke flow)
- Example package: `examples/basic/vqe_cycle/{job.yaml,program.eigen.py}`

## Prerequisites

- Rust toolchain installed (`cargo` available).
- From repository root (`/workspace/eigen-os`).

Optional check:

```bash
cargo --version
```

## Steps

1. Build and run the CLI from the workspace:

```bash
cargo run -p cli --manifest-path src/rust/Cargo.toml -- --help
```

2. (Recommended) install `eigen` into your active shell environment:

```bash
./scripts/install-eigen-cli.sh
```

If you prefer no installation, use `cargo run -p cli --manifest-path src/rust/Cargo.toml -- ...` in every step below.

3. Go to the example directory:

```bash
cd examples/basic/vqe_cycle
```

4. Submit a job:

```bash
eigen submit -f job.yaml
```

Copy the printed `job_id` (example format: `job-xxxxxxxxxxxx`).

5. Check current status (optional but recommended):

```bash
eigen status <job_id>
```

6. Watch progress:

```bash
eigen watch <job_id>
```

For a happy path demo, you can also force a completed flow using a known suffix:

```bash
eigen watch job-demo-done
```

7. Read final results:

```bash
eigen results <job_id>
```

If your generated `job_id` is not done yet, run:

```bash
eigen results job-demo-done
```

## Minimal expected output

A successful flow includes:

- `submit`: non-empty `job_id` plus hints for `status/watch/results`;
- `status`: current lifecycle state snapshot (for example `PENDING`, `RUNNING`, or terminal state);
- `watch`: sequence of updates ending in terminal state;
- `results`: success payload for `DONE`, and actionable diagnostics/non-zero exit for failed terminals.

Example qualitative sanity checks for this VQE sample:

- `counts` is populated with measured bitstrings;
- metadata includes backend/runtime fields;
- objective/energy behavior can vary between implementations, but early iterations should typically improve before flattening.

## Troubleshooting

For common failures and copy/paste fixes, see:

- `docs/howto/troubleshooting.md`
