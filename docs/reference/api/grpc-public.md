# gRPC Public API (eigen.api.v1)

The public gRPC API (`eigen.api.v1`) is the user-facing interface. It is frozen at v1.0.0 (breaking changes require v2). The `.proto` files are the source of truth (`proto/eigen/api/v1/*.proto`).

## 1. Services and Methods

- **JobService:**

   - `SubmitJob(SubmitJobRequest) → SubmitJobResponse`

   - `GetJobStatus(GetJobStatusRequest) → GetJobStatusResponse`

   - `CancelJob(CancelJobRequest) → CancelJobResponse`

   - `StreamJobUpdates(StreamJobUpdatesRequest) → stream StreamJobUpdatesResponse`

   - `GetJobResults(GetJobResultsRequest) → GetJobResultsResponse`

   - `GetDispatchRationale(GetDispatchRationaleRequest) → GetDispatchRationaleResponse`

- **DeviceService:**

   - `ListDevices(ListDevicesRequest) → ListDevicesResponse`

   - `GetDeviceDetails(GetDeviceDetailsRequest) → GetDeviceDetailsResponse`

   - `GetDeviceStatus(GetDeviceStatusRequest) → GetDeviceStatusResponse`

   - `ReserveDevice(ReserveDeviceRequest) → ReserveDeviceResponse`

- **KnowledgeBaseService:** (frozen by RFC 0034 at v1.0.0)

   - `UpsertRecord(UpsertRecordRequest) → UpsertRecordResponse`

   - `BatchUpsertRecords(BatchUpsertRecordsRequest) → BatchUpsertRecordsResponse`

   - `QueryRecords(QueryRecordsRequest) → QueryRecordsResponse`

   - `GetRecord(GetRecordRequest) → GetRecordResponse`

   - `AppendDecisionLog(…)` (not listed, if present for linking decisions, check proto)

*Compilation APIs are internal and **not** exposed publicly.*

## 2. Key Messages

**SubmitJobRequest**

```text
message SubmitJobRequest {
  string name = 1;
  oneof program {
    EigenLangSource eigen_lang = 2;
    QasmSource qasm = 3;
    AqoRef aqo_ref = 4;
  }
  string target = 5;
  int32 priority = 6;                // [0..100], default 50
  map<string,string> compiler_options = 7;
  map<string,string> metadata = 8;
  repeated string dependencies = 9;
  // (Optional) Tenant quotas envelope:
  message TenantQuotaEnvelope {
    string contract_version = 1;
    string tenant_id = 2;
    string project_id = 3;
    uint32 tenant_max_queued_jobs = 4;
    uint32 project_max_queued_jobs = 5;
  }
  TenantQuotaEnvelope tenant = 10;
}
```

- `name` (string): Job name.

- `program`: Exactly one of `eigen_lang` (embedded DSL source), `qasm` (Quantum Assembly text), or `aqo_ref` (IR reference).

- `target` (string): Backend target ID (e.g. `"sim:local"`, `"vendor:device"`).

- `priority` (int): 0–100, default 50.

- `compiler_options`, `metadata`: Arbitrary key-value maps.

- `dependencies`: List of other `job_ids` this job depends on.

- `tenant`: Optional quotas envelope (can be omitted).

**SubmitJobResponse**

```text
message SubmitJobResponse {
  string job_id = 1;
  JobStatus status = 2;
}
```

- `job_id`: Assigned job identifier (globally unique).

- `status`: The initial job status (likely `PENDING`).

**CancelJobRequest / Response**

```text
message CancelJobRequest {
  string job_id = 1;
}
message CancelJobResponse {
  bool accepted = 1; // true if cancellation was accepted
}
```

- Cancels only valid jobs.

**StreamJobUpdatesRequest / Response**

```text
message StreamJobUpdatesRequest {
  string job_id = 1;
  uint64 last_event_seq = 2;  // (Optional) resume from next event
}
message StreamJobUpdatesResponse {
  JobUpdate update = 1;
}
```

- Returns a stream of `JobUpdate` messages in order.

- Clients can supply `last_event_seq` to resume a stream (best-effort).

**GetDispatchRationale**

(Returns scheduling rationale, not fully detailed here.)

## 3. Behavioral Contracts

- **Job Lifecycle:**

   1. `SubmitJob` returns a new `job_id` and status.

   2. Clients poll `GetJobStatus` or use `StreamJobUpdates` to track progress.

   3. Once `state=SUCCEEDED` or `FAILED`, call `GetJobResults` for outputs.

   4. `CancelJob` may be called on `PENDING`/`QUEUED`/`RUNNING` tasks; it is ignored in final states.

- **Reservation:** `ReserveDevice` reserves capacity but does not guarantee exclusive lock; returning `reservation_id`, `expires_at`.

- **Errors:** Use standard gRPC status codes (not a separate `success=false`). Example:

   - Invalid input → `INVALID_ARGUMENT` with ErrorDetail.

   - Not found → `NOT_FOUND`.

   - Unavailable hardware → `UNAVAILABLE`.

## 4. Identified Gaps

1. **Idempotency Key:** The public API proto does not include an idempotency field. (Currently, idempotency is handled via metadata `client_request_id` if at all.) We should define a standard idempotency mechanism or require clients to use `client_request_id` header.

2. **Cancel Semantics:** The allowed states for cancellation should be documented (e.g. cannot cancel a DONE or ERROR job). An explicit matrix in docs is needed.

3. **Dispatch Rationale:** If no rationale exists, it's unclear whether `GetDispatchRationale` returns an empty message or a NOT_FOUND error. We should clarify: e.g. return NOT_FOUND if no rationale, or an empty response with `NULL`.

4. **Error Details:** We need to align with the overall Error Model. For each RPC, specify how to return structured `ErrorDetail` messages. Example: field-wise errors vs. status code vs. application errors.

5. **Stream Replay:** The retention or replay limits for `StreamJobUpdates` (how long events are kept) are not specified. We should document any window or retries.

6. **Reservation Binding:** The protocol is unclear on how to enforce a `ReserveDevice` with subsequent `SubmitJob`. E.g. if a reservation is held, how does the next `SubmitJob` use it? The `SubmitJobRequest` has no `reservation_id` field. We may need a feature to bind them.

7. **SLA/SLO:** Performance expectations (e.g. `SubmitJob` <100ms, status fetch <50ms) are not documented. We should consider adding service-level targets.

8. **Auth Model:** The expected JWT scopes are only partially documented. We should list required OAuth scopes or RBAC roles for each method (e.g. `jobs:submit`, `devices:list`).

9. **SDK Conformance:** There is no formal test suite for language SDKs or CLI. We should publish example requests/responses or WireMock tests for clients.

## 5. Action Items

- **Idempotency:** Consider adding a `string client_request_id = 12`; to `SubmitJobRequest` (and update versions accordingly), or clearly document use of metadata: {"x-client-request-id": ...}.

- **Cancel Logic:** Document in reference (and possibly enforce in code) which states can be cancelled.

- **Detail Examples:** Add rich examples for each RPC, including error cases, in the docs.

- **Appendix:** Include a state machine diagram and a cancellation legality table in docs.

- **Replay Policy:** Clarify and codify `last_event_seq` behavior and event retention (e.g. keep logs for 24h or 1000 events).

- **Auth Appendix:** Add a security section in docs describing required tokens/claims (e.g. `sub`, `roles`, `aud`).
