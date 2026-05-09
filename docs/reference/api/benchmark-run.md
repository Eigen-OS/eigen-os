# Benchmark Run API Contract (`/benchmarks/run`)

- **Endpoint (contract target):** `POST /benchmarks/run`
- **Current implementation artifact:** `BenchmarkRunApi.run(request: dict) -> dict` in `benchmark_service.run_api`
- **Contract version:** `1.0.0`
- **DTO versioning policy:** SemVer (`MAJOR.MINOR.PATCH`)
- **Current artifact markers:**
  - `api_version: 1.0.0`
  - `run.state_contract_version: 1.0.0`
  - `snapshot.contract_version: 1.0.0`
  - `snapshot.snapshot_version: 1.0.0`
  - `snapshot.history_entry_version: 1.0.0`

## Purpose and scope

This contract documents the stable payload surface for creating benchmark runs in Phase-3 benchmark-service.

Runtime behavior covered by this contract:

- request validation;
- idempotent run creation by `idempotency_key`;
- deterministic snapshot metadata (`request_hash`, canonical `payload`);
- normalized success/error envelopes.

## Request schema

Required fields:

- `idempotency_key` (`string`, non-empty after `trim`)
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

Field notes:

- `run.run_id` is deterministic for the same start tuple (`scope=start`, `idempotency_key`, canonicalized `config`).
- `run.state` is always `PENDING` immediately after successful creation.
- `snapshot.payload` is canonical JSON (`sort_keys=True`, compact separators).
- `snapshot.request_hash` is SHA-256 of canonical `snapshot.payload`.

## Error envelope

Validation failures map to canonical public style with structured field details:

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

Validation rules currently enforced:

- `idempotency_key` must be non-empty string;
- `config` must be non-empty object.

## Lifecycle linkage

`/benchmarks/run` creates a run in lifecycle state machine `1.0.0`:

`PENDING -> PREPARING -> RUNNING -> SUCCEEDED|FAILED|CANCELLED`

Transition rules and retry semantics are defined in lifecycle core (`retry_run` allowed only from `FAILED` or `CANCELLED`).

## Compatibility policy

- Removing/changing required request fields without MAJOR bump is prohibited.
- Optional additive fields use MINOR.
- PATCH may include only fixes/clarifications without public semantic change.
- Deprecated fields must live through at least one MINOR release before removal.

## Implementation status snapshot (фиксируем текущее состояние)

Status as of **2026-05-09**:

- ✅ Contract-level request/response surface is implemented and covered by fixture tests.
- ✅ Idempotent start by `idempotency_key` is implemented in lifecycle service.
- ✅ Deterministic payload canonicalization + hash generation are implemented.
- ⚠️ HTTP transport binding for `POST /benchmarks/run` is not part of benchmark-service code here; current implementation is a Python contract API object (`BenchmarkRunApi`) invoked directly in tests.
- ⚠️ No persisted storage in this module: lifecycle store is in-memory, so idempotency/replay guarantees are process-local.
- ⚠️ No authn/authz, quotas, and rate-limiting rules are specified in this API contract yet.
- ⚠️ No explicit request size limits / schema-level `config` constraints beyond "non-empty object".

## What is missing to reach production-ready endpoint (чего не хватает)

1. **Transport layer binding**
   - Explicit HTTP handler/controller that maps `POST /benchmarks/run` to `BenchmarkRunApi.run`.
2. **Durable state**
   - Persistent run store + idempotency index (DB-backed) with crash-safe recovery.
3. **Operational policies**
   - AuthN/AuthZ, tenant isolation, quotas/rate limits, and audit events.
4. **Schema hardening**
   - Structured schema for `config` (required keys, types, allowed ranges).
5. **SLO/SLA and errors**
   - Timeout/retry semantics, expanded error taxonomy, and observability SLO instrumentation.
6. **Backward-compat governance**
   - Automated SemVer contract check against previous released fixtures/tags.

## Contract tests and CI gate

Contract fixture tests are stored under:

- `src/services/benchmark-service/tests/fixtures/contracts/benchmark_run_v1/`
- `src/services/benchmark-service/tests/test_run_api_contract.py`

These tests enforce required request/response/error envelope fields and block incompatible changes in CI.
