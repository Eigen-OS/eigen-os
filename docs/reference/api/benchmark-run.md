# Benchmark Run API Contract (`/benchmarks/run`)

- **Endpoint:** `POST /benchmarks/run`
- **Contract version:** `1.0.0`
- **DTO versioning policy:** SemVer (`MAJOR.MINOR.PATCH`)
- **Current artifact markers:**
  - `api_version: 1.0.0`
  - `run.state_contract_version: 1.0.0`
  - `snapshot.contract_version: 1.0.0`
  - `snapshot.snapshot_version: 1.0.0`
  - `snapshot.history_entry_version: 1.0.0`

## Request schema

Required fields:

- `idempotency_key` (`string`, non-empty)
- `config` (`object`, non-empty)

Example:

```json
{
  "idempotency_key": "phase3-run-001",
  "config": {
    "dataset": "qsbench-core",
    "dataset_version": "2026.04.27",
    "backend": "simulator",
    "seed": 42
  }
}
```

## Success response schema

```json
{
  "api_version": "1.0.0",
  "run": {
    "run_id": "run_...",
    "state": "PENDING",
    "state_contract_version": "1.0.0",
    "parent_run_id": null,
    "idempotency_key": "phase3-run-001"
  },
  "snapshot": {
    "contract_version": "1.0.0",
    "snapshot_version": "1.0.0",
    "history_entry_version": "1.0.0",
    "run_id": "run_...",
    "request_hash": "<sha256>",
    "created_at": "2026-04-27T00:00:00+00:00",
    "payload": "{\"backend\":\"simulator\",...}"
  }
}
```

## Error envelope

Validation failures map to the existing public API style with a canonical code and structured field details:

```json
{
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "benchmark run request validation failed",
    "details": [
      {
        "code": "field_required",
        "field": "idempotency_key",
        "message": "idempotency_key is required and must be a non-empty string"
      }
    ]
  }
}
```

## Compatibility policy

- Removing/changing required request fields without a MAJOR bump is prohibited.
- Optional additive fields use MINOR.
- PATCH may only include fixes and clarifications, with no public semantic change.
- Fields marked for removal must be deprecated for at least one MINOR release first.

## Contract tests and CI gate

Contract fixture tests are stored under:

- `src/services/benchmark-service/tests/fixtures/contracts/benchmark_run_v1/`
- `src/services/benchmark-service/tests/test_run_api_contract.py`

These tests enforce required request/response/error envelope fields and block incompatible changes in CI.
