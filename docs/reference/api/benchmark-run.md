# REST API: Benchmark Run (`POST /benchmarks/run`)

## 1. Request Schema

- **Endpoint:** `POST /benchmarks/run`

- **Content-Type:** `application/json`

- **Request JSON:**

```json
{
  "idempotency_key": "<string>",   // required, non-empty
  "config": {                      // required, non-empty object
    // Benchmark configuration parameters (implementation-defined)
    "dataset": "qsbench-core",
    "dataset_version": "2026.04.27",
    "backend": "simulator",
    "seed": 42
    // ... (other domain-specific keys as needed)
  }
}
```

  - `idempotency_key` (string): **required.** A unique client-provided key to ensure idempotent creation. Must be a non-empty string (whitespace trimmed).

  - `config` (object): **required.** Arbitrary JSON with benchmark parameters. Must be a non-empty object.

## 2. Success Response (201 Created)

On successful creation (or retrieval of an existing run with the same idempotency key), returns HTTP 201 and a JSON body:

```json
{
  "api_version": "1.0.0",
  "run": {
    "run_id": "run_...",
    "state": "PENDING",
    "state_contract_version": "1.0.0",
    "parent_run_id": null,
    "idempotency_key": "<same as request>"
  },
  "snapshot": {
    "contract_version": "1.0.0",
    "snapshot_version": "1.0.0",
    "history_entry_version": "1.0.0",
    "run_id": "run_...",
    "request_hash": "<sha256 of payload>",
    "created_at": "2026-05-21T12:34:56Z",
    "payload": "{\"backend\":\"simulator\", ...}" 
  }
}
```

- **Field notes:**

  - `api_version`: API contract version (here `1.0.0`).

  - `run.run_id`: Deterministic identifier of the run.

  - `run.state`: Always "`PENDING`" immediately after creation.

  - `state_contract_version`: Same as `api_version` (since run states are part of the v1.0.0 contract).

  - `parent_run_id`: Always `null` on creation (reserved for future tree of runs).

  - `snapshot.contract_version`: Semantic version of the request envelope (same as `api_version`).

  - `snapshot.snapshot_version`: Version of the snapshot format (also `1.0.0`).

  - `snapshot.history_entry_version`: Version of history entries (set to `1.0.0`).

  - `snapshot.request_hash`: SHA-256 hash of the canonical JSON payload.

  - `snapshot.payload`: Canonical (sorted keys, no whitespace) JSON string of the `config`.

## 3. Error Response (4xx)

Validation or other request failures return HTTP 400 with a structured JSON error envelope:

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
      // ... potentially multiple field errors
    ]
  }
}
```

- **Validation rules:**
  
  - `idempotency_key` must be a non-empty string.

  - `config` must be a non-empty JSON object.

- On validation failure, `code` is `INVALID_ARGUMENT`. The `message` is a summary, and `details` lists each field error with `field`, `code`, and `message`.

## 4. Lifecycle and Semantics

- Runs follow the state machine: `PENDING → PREPARING → RUNNING → SUCCEEDED|FAILED|CANCELLED`.

- The system ensures idempotency by `idempotency_key`: the same key and config will not create duplicate runs.

- On error during creation or if the run exists, the service handles it as idempotent.

## 5. Versioning and Compatibility

- **Contract version:** 1.0.0 (breaking changes require v2.0).

- **Field extensions:** Adding new optional fields may use MINOR bumps; removing required fields needs MAJOR bump.

## 6. Implementation Status & Gaps

- **Implemented:**

  - Contract logic in `BenchmarkRunApi.run()` matches the above schema.

  - Validation, idempotent run creation, and snapshot generation are implemented (in-memory).

  - Fixture tests (`test_run_api_contract.py`) verify the JSON shapes and idempotency.

- **Missing / Partial:**

  - **Transport binding:** No actual HTTP handler is implemented in this repository. The `BenchmarkRunApi` class is a Python object (used in tests) but there is no HTTP endpoint.

  - **Persistence:** Current implementation uses in-memory store; no durable database for run state or idempotency.

  - **AuthN/AuthZ/Quotas:** No authentication or authorization is enforced; multi-tenant isolation or quotas are not implemented.

  - **Size/schema constraints:** No detailed JSON Schema for `config` (all fields allowed), nor request size limits.

- **Tasks to complete:**

  1. **HTTP Handler:** Create a REST controller (e.g. Flask or FastAPI) for `POST /benchmarks/run` that calls `BenchmarkRunApi.run()`. Add routing to expose this endpoint.

  2. **Durable Storage:** Hook up a database (e.g. PostgreSQL or SQLite) for runs and idempotency. Ensure crash recovery and global consistency of `run_id`.

  3. **Security:** Integrate JWT/OAuth2 tokens and ACL checks; ensure only authorized clients can call this endpoint.

  4. **Request Schema:** Define a stricter JSON Schema for `config` (required keys, data types) and enforce it.

  5. **Error taxonomy:** Expand error handling (e.g. return `ALREADY_EXISTS` for duplicate run, `RESOURCE_EXHAUSTED` for quotas, etc.).

  6. **CI Contract Tests:** Add automated tests in CI to catch any JSON contract breaks using the existing fixture tests.
