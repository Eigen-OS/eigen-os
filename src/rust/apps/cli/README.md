# Eigen CLI

Current package version: `0.4.0`.

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
