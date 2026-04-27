# benchmark-service

Phase-3 benchmark core service for run lifecycle contract `1.0.0`.

## Run lifecycle state machine (v1)

```text
PENDING -> PREPARING -> RUNNING -> SUCCEEDED
                        \-> FAILED
PENDING/PREPARING/RUNNING -> CANCELLED
```

Terminal states: `SUCCEEDED`, `FAILED`, `CANCELLED`.

## Contract guarantees

- Idempotent `start_run(idempotency_key)`.
- Idempotent `retry_run(run_id, retry_key)` from `FAILED|CANCELLED`.
- Immutable run snapshot with explicit `contract_version` and `snapshot_version`.
- Deterministic snapshot payload canonicalization (`json.dumps(..., sort_keys=True)`).
