# Troubleshooting

## When to Use

Use this document if the Quickstart from `docs/tutorials/quickstart-local-sim.md` fails at one of the following steps:

- `submit` does not return a `job_id`;
- `watch` does not show the expected updates;
- `results` fails or returns empty output;
- The CLI (`eigen`) does not build or run.

## Prerequisites

Check the basic conditions:

1. You are running commands from the root of the `eigen-os` repository (or use a correct `--manifest-path`).
2. Rust is installed and `cargo` is available.
3. The example contains both files:
   - `examples/basic/vqe_cycle/job.yaml`
   - `examples/basic/vqe_cycle/program.eigen.py`

Quick check:

```bash
cargo --version
test -f examples/basic/vqe_cycle/job.yaml
test -f examples/basic/vqe_cycle/program.eigen.py
```

### 0) `eigen: command not found`

**Symptoms**
- `eigen: command not found`

**What to do**

From repository root:

```bash
./scripts/install-eigen-cli.sh
eigen --help
```

The installer puts `eigen` into your active virtualenv (`$VIRTUAL_ENV/bin`) when available,
or `~/.local/bin` otherwise.
Do **not** run it with `sudo`.

If you previously ran with `sudo` and now see `Permission denied` under `src/rust/target`,
fix ownership once:

```bash
sudo chown -R "$USER:$USER" src/rust/target
```

---

### 1) `cargo run -p cli ...` does not run

**Symptoms**
- Error about package `cli`;
- Error about `--manifest-path`;
- Rust build error.

**What to do**

```bash
cargo run -p cli --manifest-path src/rust/Cargo.toml -- --help
```

If it doesn't run, make sure the command is executed from the repository root.

---

### 2) `submit` fails with `INVALID_ARGUMENT`

**Symptoms**
- `submit failed: INVALID_ARGUMENT ...`

**Common causes**
- Incorrect `apiVersion` or `kind` in `job.yaml`;
- Missing `spec.target`;
- `program.eigen.py` not found;
- `entrypoint` not found in the source.

**What to do**

Check in `job.yaml`:

- `apiVersion: eigen.os/v0.1`
- `kind: QuantumJob`
- `spec.target` is set
- `spec.entrypoint` matches a function in `program.eigen.py` (usually `main`)

Also verify that the program file exists next to `job.yaml`.

---

### 3) `watch`/`results` fails with a network error

**Symptoms**
- `grpc code=UNAVAILABLE` or `grpc code=DEADLINE_EXCEEDED`

**What to do**

For a smoke test, use a deterministic job id:

```bash
cargo run -p cli --manifest-path src/rust/Cargo.toml -- watch job-demo-done
cargo run -p cli --manifest-path src/rust/Cargo.toml -- results job-demo-done
```

If you are testing a real integration environment, retry later and check the availability of the environment services.

---

### 4) `results` returns `FAILED_PRECONDITION`

**Symptoms**
- Message like `job is not done`.

**What to do**

First wait for completion:

```bash
cargo run -p cli --manifest-path src/rust/Cargo.toml -- watch <job_id>
```

Only after the status becomes `DONE` run `results` again.

---

### 5) Empty / unexpected results

**Symptoms**
- Results exist but do not look like the expected form.

**What to do**

1. Make sure you are running the `examples/basic/vqe_cycle` example.
2. Verify that `program.eigen.py` contains exactly one `@hybrid_program`.
3. Restart the `submit -> watch -> results` flow with a new`job_id`.

---

### 6) Diagnose lifecycle delays with per-job timeline (Observability v2)

Each job now exposes a full event timeline with timestamps:

- `QUEUED`
- `COMPILED`
- `DISPATCHED`
- `RUNNING`
- `COMPLETED` (or terminal error/cancel/timeout)

Use `watch` to inspect the ordered event stream:

```bash
cargo run -p cli --manifest-path src/rust/Cargo.toml -- watch <job_id>
```

Troubleshooting patterns:

1. **Stuck before `COMPILED`**  
   Likely compiler queue/saturation or validation retries.
2. **Long gap between `DISPATCHED` and `RUNNING`**  
   Backend/device scheduling delay.
3. **Terminal error after `RUNNING`**  
   Backend runtime failure; inspect `error_code` + `error_summary`.

Correlate logs/metrics/traces with the same `trace_id`:

- timeline events include `trace_id` in event messages,
- results metadata contains `trace_id`, `trace_ref`, and `qfs_job_timeline`.

## Verification

Minimal E2E smoke test (copy/paste):

```bash
cd examples/basic/vqe_cycle
cargo run -p cli --manifest-path ../../../src/rust/Cargo.toml -- submit -f job.yaml
cargo run -p cli --manifest-path ../../../src/rust/Cargo.toml -- watch job-demo-done
cargo run -p cli --manifest-path ../../../src/rust/Cargo.toml -- results job-demo-done
```

Expected outcome:

- `submit` prints a `job_id`;
- `watch` reaches `DONE`;
- `results` returns `state: DONE`, a `summary` block when available, `counts`, and `metadata`.

## AWS Braket degradation runbook (Phase-8D)

- Check `GET /healthz` and inspect `drivers.aws-braket.details.queue_state`; `degraded` indicates provider-side pressure.
- If queue saturation is observed, increase `DRIVER_MANAGER_AWS_BRAKET_TIMEOUT_SEC` and `DRIVER_MANAGER_AWS_BRAKET_MAX_RETRIES` within approved SLO bounds.
- Validate credentials source (`keys`, `env:*`, or `secret_ref:*`) and rotate secrets when auth errors map to `PERMISSION_DENIED`.
- For sustained throttling (`RESOURCE_EXHAUSTED`), quarantine AWS profile from nightly conformance and re-run simulator/IBM matrix while incident is active.
