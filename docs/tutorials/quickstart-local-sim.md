# Quickstart (local simulator)

## Goal

Execute a local end-to-end run (`submit -> watch -> results`) with a small 2-qubit VQE example.

Reference example: `examples/basic/vqe_cycle/`.

## Prerequisites

- Local services started for the MVP stack.
- `eigen` CLI available in your shell.

## Steps

1. Change directory:

```bash
cd examples/basic/vqe_cycle
```

2. Submit:

```bash
eigen submit -f job.yaml
```

3. Watch status:

```bash
eigen watch <job_id>
```

4. Read results:

```bash
eigen results <job_id>
```

## Expected outputs

A successful run typically includes:

- terminal output with a valid `job_id`;
- measurement counts from simulator execution;
- optimization metrics where objective/energy declines before flattening.

Use this as a sanity check (exact numbers can differ by implementation details):

- objective improves in early iterations;
- best value changes less frequently near the end;
- counts distribution becomes more stable when parameters approach a minimum.

## Troubleshooting

- **Job stuck in queued/running**: check local service health and retry submit.
- **Missing program file**: ensure `program.eigen.py` exists beside `job.yaml`.
- **Unexpected counts/objective**: increase shots and max iterations in `job.yaml` and rerun.
