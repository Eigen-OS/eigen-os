# Eigen CLI

Current package version: `0.4.0`.

## Submit command

Product 1.0 submission emits a normalized public payload that includes the canonical request envelope, canonical JobSpec 1.0 normalization, and the legacy `SubmitJobRequest` body used by the current CLI transport shim. The command accepts both file-backed (`spec.program.path`) and inline (`spec.program.source`) JobSpec inputs.

```bash
eigen submit -f job.yaml \
  --idempotency-key idem-demo \
  --request-id req-demo \
  --traceparent 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01 \
  --tenant tenant-a \
  --project project-a
```

If `--idempotency-key` is omitted, the CLI derives a deterministic `idem_<sha256>` value from the normalized JobSpec payload so same-input retries remain stable. If `--request-id` is omitted, the CLI derives `req_<sha256>` from the same normalized payload.

## Benchmark commands

Phase-3 CLI benchmark UX provides reproducible run/compare flows with stable JSON contracts.

### `eigen benchmark run`

Create a deterministic run snapshot from a benchmark config JSON.

```bash
eigen benchmark run \
  --config bench-baseline.json \
  --output json \
  --output-file baseline.snapshot.json
```

Required config fields:

- `workload` (string)
- `dataset` (string)
- `backend` (string)
- `seed` (u64)
- `metrics` (object with numeric values)

Run snapshots always include explicit version markers:

- `contract_version`
- `snapshot_version`

### `eigen benchmark compare`

Compare two run snapshots (`baseline` vs `candidate`) with deterministic regression flags.

```bash
eigen benchmark compare \
  --baseline baseline.snapshot.json \
  --candidate candidate.snapshot.json \
  --output human
```

Comparison outputs always include explicit version markers:

- `contract_version`
- `comparison_version`

### Reproducibility tips

- Keep `seed` fixed between baseline/candidate when you compare implementation changes.
- Store generated snapshot JSON files under version control as golden fixtures for CLI contract compatibility checks.
- Use `--output-file` to persist exact artifacts produced by CI and local runs.
