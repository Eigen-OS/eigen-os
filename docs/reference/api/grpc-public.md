# Public gRPC API — eigen_api.v0.1 (MVP)

## Summary

Defines the stable public gRPC surface used by CLI, SDKs, and external tools in MVP. This API is the **only** client‑facing interface to Eigen OS and must remain backward‑compatible within the MVP timeframe.

## Services & Methods

### 1. JobService

Manages quantum job lifecycle.
```proto
service JobService {
  // Submit a new job
  rpc SubmitJob(SubmitJobRequest) returns (JobResponse);
  
  // Get current job status
  rpc GetJobStatus(JobStatusRequest) returns (JobStatusResponse);
  
  // Cancel a running job
  rpc CancelJob(CancelJobRequest) returns (CancelJobResponse);
  
  // Stream job updates (events)
  rpc StreamJobUpdates(JobUpdatesRequest) returns (stream JobUpdate);
  
  // Fetch job results (only when DONE)
  rpc GetJobResults(JobResultsRequest) returns (JobResultsResponse);
}
```

### 2. DeviceService

Queries and reserves quantum devices.
```proto
service DeviceService {
  // List available devices
  rpc ListDevices(ListDevicesRequest) returns (ListDevicesResponse);
  
  // Get detailed device information
  rpc GetDeviceDetails(DeviceDetailsRequest) returns (DeviceDetailsResponse);
  
  // Get current device status
  rpc GetDeviceStatus(DeviceStatusRequest) returns (DeviceStatusResponse);
  
  // Reserve a device for exclusive use
  rpc ReserveDevice(ReserveDeviceRequest) returns (ReserveDeviceResponse);
}
```

### 3. CompilationService (Optional in MVP)

Compiles quantum circuits without execution.
```proto
service CompilationService {
  // Compile source to circuit IR
  rpc CompileCircuit(CompileCircuitRequest) returns (CompileCircuitResponse);
  
  // Optimize an existing circuit
  rpc OptimizeCircuit(OptimizeCircuitRequest) returns (OptimizeCircuitResponse);
  
  // Validate circuit syntax/semantics
  rpc ValidateCircuit(ValidateCircuitRequest) returns (ValidateCircuitResponse);
}
```

**Note**: `CompilationService` may be internal‑only in MVP; see Open Questions.

## Key Data Types

### SubmitJobRequest
```proto
message SubmitJobRequest {
  string name = 1;  // User‑provided job name
  oneof program {
    EigenLangSource eigen_lang = 2;
    QasmSource qasm = 3;
    AqoRef aqo_ref = 4;
  }
  string target = 5;  // e.g., "sim:local", "ibmq:quito"
  int32 priority = 6;  // 0–100, default 50
  map<string, string> compiler_options = 7;
  map<string, string> metadata = 8;  // Free‑form runtime settings
  repeated string dependencies = 9;  // Input artifact URIs
}

message EigenLangSource {
  bytes source = 1;
  string entrypoint = 2;  // Function name (default "main")
  string sha256 = 3;  // Optional, for dedup
}
```

### JobUpdate (Streaming)
```proto
message JobUpdate {
  string job_id = 1;
  JobState state = 2;
  string stage = 3;  // e.g., "COMPILING", "EXECUTING"
  float progress = 4;  // 0.0–1.0
  string message = 5;
  uint64 event_seq = 6;  // Monotonic, starts at 1
  google.protobuf.Timestamp timestamp = 7;
}

enum JobState {
  PENDING = 0;
  COMPILING = 1;
  QUEUED = 2;
  RUNNING = 3;
  DONE = 4;
  ERROR = 5;
  CANCELLED = 6;
  TIMEOUT = 7;
}
```

### DeviceInfo
```proto
message DeviceInfo {
  string device_id = 1;
  string name = 2;
  string backend_type = 3;  // "simulator", "ibmq", "rigetti", etc.
  DeviceStatus status = 4;
  int32 queue_depth = 5;
  int32 estimated_wait_sec = 6;
  map<string, string> capabilities = 7;
}

enum DeviceStatus {
  ONLINE = 0;
  OFFLINE = 1;
  CALIBRATING = 2;
  MAINTENANCE = 3;
  ERROR = 4;
}
```

## Semantics & Behavior

### 1. Job Lifecycle

1. **SubmitJob** → returns `job_id`

2. Client may:

    - Poll **GetJobStatus**

    - Subscribe to **StreamJobUpdates** (preferred)

3.  When state reaches **DONE**, call **GetJobResults**

4. **CancelJob** may be called while job is in any non‑terminal state

### 2. StreamJobUpdates Rules

- Events are **ordered** per `job_id`

- Terminal events (DONE, ERROR, CANCELLED, TIMEOUT) are emitted exactly once

- While RUNNING, server may send periodic heartbeats (progress/message updates)

- Reconnection support: client may resume from `last_event_seq` (best‑effort in MVP)

- **MVP Implementation Note**: Uses polling internally; true event‑driven streaming in Phase 1

### 3. ReserveDevice Semantics

- Reserves a **scheduler slot** in kernel, not hardware‑wide exclusive lock

- Reservation expires after `ttl_seconds`

- Returns `reservation_id` for use in SubmitJob (future enhancement)

- Errors:

    - `FAILED_PRECONDITION`: device offline

    - `RESOURCE_EXHAUSTED`: no slots available

    - `NOT_FOUND`: invalid device_id

### 4. Error Model

- **Success**: gRPC status `OK`

- **Failure**: Non‑OK gRPC status code with optional structured details using `google.rpc.Status`

 - **Never** use `success=false` fields in response messages

Common error mappings:

- `INVALID_ARGUMENT`: malformed request, unsupported program format

- `NOT_FOUND`: job/device doesn't exist

- `FAILED_PRECONDITION`: job not in cancellable state, device offline

- `RESOURCE_EXHAUSTED`: quota exceeded, no device slots

- `UNAVAILABLE`: service temporarily unavailable

## Authentication & Authorization

### MVP Auth Model

- **API keys** or **static tokens** passed via gRPC metadata header

- Header: `authorization: Bearer <token>`

- System‑api validates token and extracts subject/roles

- **No** public auth RPC methods in MVP

### Permissions

- `jobs:submit` → SubmitJob

- `jobs:read` → GetJobStatus, GetJobResults, StreamJobUpdates

- `jobs:cancel` → CancelJob

- `devices:list` → ListDevices, GetDeviceDetails, GetDeviceStatus

- `devices:reserve` → ReserveDevice

## Versioning & Compatibility

### API Version

- Protobuf package: `eigen_api.v1`

- Version included in all requests/responses as `api_version` field

- Backward‑compatible changes only (add optional fields, new methods)

- Breaking changes require new major version (v2)

### MVP Freeze

- Method signatures and semantics frozen for MVP

- New optional fields may be added post‑MVP

- Deprecated fields/methods must follow 3‑month sunset period

## Observability

### Metrics

- Prometheus metrics at `/metrics` endpoint (HTTP, not gRPC)

- Counters: `eigen_api_requests_total{method,status}`

- Histograms: `eigen_api_request_duration_seconds{method}`

### Tracing

    W3C TraceContext (`traceparent`) passed via gRPC metadata

    All logs include `trace_id` and `job_id` (when applicable)

## Examples

### Submit a Job
```python
request = SubmitJobRequest(
    name="vqe-h2",
    program=EigenLangSource(
        source=open("program.eigen.py").read().encode(),
        entrypoint="main"
    ),
    target="sim:local",
    metadata={"shots": "1024", "max_iters": "50"}
)
response = stub.SubmitJob(request)
job_id = response.job_id
```

### Stream Updates
```python
for update in stub.StreamJobUpdates(JobUpdatesRequest(job_id=job_id)):
    print(f"[{update.state}] {update.message}")
    if update.state in [JobState.DONE, JobState.ERROR]:
        break
```

## Open Questions (MVP)

1. **CompilationService public?** Decision: Internal‑only for MVP

2. **Should** `shots` **be a top‑level field?** Decision: Keep in metadata for v0.1, typed in v0.2

3. **Device reservation in SubmitJob?** Decision: Post‑MVP feature

## Future Enhancements (Post‑MVP)

1. Async/long‑running job submission

2. Batch job operations

3. Device reservation integration with SubmitJob

4. Public calibration API

5. WebSocket streaming alternative

---

**References:**

    RFC 0003: JobSpec v0.1 (maps to SubmitJobRequest)

    RFC 0005: AQO format (compiler output)

    RFC 0008: Observability (metrics, tracing)

    RFC 0009: Security (authz model)