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

## Dataset ingestion contract (QSBench-compatible)

Dataset manifest schema version: `1.0.0`.

Ingestion guarantees:

- Manifest schema validation with structured error payloads (`code`, `field`, `message`).
- Provenance validation via required `source_uri` and `source_checksum`.
- Bundle checksum verification for `source_file`.
- Dataset catalog registration with queryable versions per dataset.
