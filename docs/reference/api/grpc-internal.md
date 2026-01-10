# Internal gRPC APIs (MVP)

## Summary

Defines the internal gRPC service contracts used between Eigen OS services during MVP. These APIs are **not exposed to clients** and may evolve more freely than the public API.

## Services Overview

| **Service** | **Purpose** | **Language** | **Caller(s)** |
|-------------------|-------------------|-------------------|-------------------|
| `KernelGateway` | Entry point for system‑api to forward job requests | Rust | system‑api |
| `CompilationService` | Compile/validate/optimize quantum circuits | Python | eigen‑kernel |
| `DriverManagerService` | Execute circuits on backends via plugins | Python | eigen‑kernel |

### 1. KernelGateway (kernel_api.v0.1)

Internal gateway exposed by eigen‑kernel for system‑api to forward requests.

**Service Definition**
```proto
service KernelGateway {
  // Job lifecycle
  rpc EnqueueJob(EnqueueJobRequest) returns (EnqueueJobResponse);
  rpc GetJobStatus(GetJobStatusRequest) returns (GetJobStatusResponse);
  rpc CancelJob(CancelJobRequest) returns (CancelJobResponse);
  rpc GetJobResults(GetJobResultsRequest) returns (GetJobResultsResponse);
  
  // Device management
  rpc ListDevices(ListDevicesRequest) returns (ListDevicesResponse);
  rpc GetDeviceStatus(DeviceStatusRequest) returns (DeviceStatusResponse);
  
  // Streaming updates (polling‑based in MVP)
  rpc PollJobUpdates(PollJobUpdatesRequest) returns (PollJobUpdatesResponse);
}

// Request/response examples (key fields only)
message EnqueueJobRequest {
  string job_id = 1;
  string name = 2;
  oneof program {
    EigenLangSource eigen_lang = 3;
    QasmSource qasm = 4;
    AqoRef aqo_ref = 5;
  }
  string target = 6;
  int32 priority = 7;
  map<string, string> compiler_options = 8;
  map<string, string> metadata = 9;
  repeated string dependencies = 10;
  // Auth context from system‑api
  string subject = 11;
  repeated string roles = 12;
  string tenant = 13;
}

message EnqueueJobResponse {
  string job_id = 1;  // echoed back
  google.protobuf.Timestamp enqueued_at = 2;
}

message PollJobUpdatesRequest {
  string job_id = 1;
  uint64 last_event_seq = 2;  // 0 for start
  int32 max_events = 3;
}

message PollJobUpdatesResponse {
  repeated JobUpdate updates = 1;
  bool has_more = 2;
}
```

**Notes**:

- Used by system‑api to forward `SubmitJobRequest` after validation/auth

- Auth context (`subject`, `roles`, `tenant`) must be propagated via gRPC metadata

- `PollJobUpdates` is polling‑based in MVP; true streaming may come in Phase 1

- Device methods may proxy to driver‑manager or return cached aggregates

### 2. CompilationService (compiler_api.v0.1)

Service for compiling, validating, and optimizing quantum circuits.

**Service Definition**
```proto
service CompilationService {
  // Compile Eigen‑Lang source to AQO
  rpc CompileCircuit(CompileCircuitRequest) returns (CompileCircuitResponse);
  
  // Optimize an existing circuit
  rpc OptimizeCircuit(OptimizeCircuitRequest) returns (OptimizeCircuitResponse);
  
  // Validate circuit syntax/semantics
  rpc ValidateCircuit(ValidateCircuitRequest) returns (ValidateCircuitResponse);
}

message CompileCircuitRequest {
  oneof source {
    EigenLangSource eigen_lang = 1;
    QasmSource qasm = 2;
    AqoBytes aqo = 3;
  }
  string target = 4;  // e.g., "sim:local", "ibmq:quito"
  map<string, string> options = 5;  // compiler_options
  string job_id = 6;  // for tracing
}

message CompileCircuitResponse {
  CircuitPayload payload = 1;
  CompilationMetadata metadata = 2;
}

message CircuitPayload {
  enum Format {
    AQO_JSON = 0;
    AQO_PROTO = 1;
    QASM3_TEXT = 2;
    BACKEND_NATIVE = 3;
  }
  Format format = 1;
  bytes data = 2;
}

message CompilationMetadata {
  int32 logical_qubits = 1;
  int32 depth = 2;
  int32 gate_count = 3;
  map<string, string> metrics = 4;
  repeated string warnings = 5;
}
```

**Notes**:

- Called by eigen‑kernel during the Compilation stage

- Must perform AST‑only compilation (no execution of user code)

- Returns `CircuitPayload` in one of several formats; kernel chooses based on target

- `BACKEND_NATIVE` format is vendor‑specific bytes (driver‑manager responsibility)

### 3. DriverManagerService (driver_api.v0.1)

Service for executing circuits on quantum backends via plugin drivers.

**Service Definition**
```proto
service DriverManagerService {
  // List available backends/devices
  rpc ListDevices(ListDevicesRequest) returns (ListDevicesResponse);
  
  // Get detailed device status
  rpc GetDeviceStatus(DeviceStatusRequest) returns (DeviceStatusResponse);
  
  // Execute a circuit
  rpc ExecuteCircuit(ExecuteCircuitRequest) returns (ExecuteCircuitResponse);
  
  // Calibrate a device (optional in MVP)
  rpc CalibrateDevice(CalibrateDeviceRequest) returns (CalibrateDeviceResponse);
}

message ExecuteCircuitRequest {
  string job_id = 1;
  string device_id = 2;
  CircuitPayload payload = 3;
  int32 shots = 4;
  map<string, string> options = 5;  // backend‑specific
}

message ExecuteCircuitResponse {
  map<string, int64> counts = 1;  // bitstring → count
  double execution_time_sec = 2;
  map<string, string> metadata = 3;  // backend‑specific
}

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

**Notes**:

- Called by eigen‑kernel during QuantumExecution stage

- Must normalize backend results into `counts` (bitstring→int64)

- `metadata` may contain backend‑specific info (fidelity, T1/T2, etc.)

- Errors must use gRPC status codes, not embedded error fields

- Simulator driver is required for MVP

## Error Handling

All internal services must use **gRPC status codes** for failures:

| **Code** | **Typical Use** |
|-------------------|-------------------|
| `INVALID_ARGUMENT` | Malformed request, unsupported format |
| `NOT_FOUND` | Job/device doesn't exist |
| `FAILED_PRECONDITION` | Device offline, job not in runnable state |
| `RESOURCE_EXHAUSTED` | No available slots, quota exceeded |
| `UNAVAILABLE` | Backend down, driver unreachable |
| `UNIMPLEMENTED` | Operation not supported |

Structured error details may be provided using `google.rpc.Status` in the response trailers.

## Security & Observability

- **Network isolation**: These services run on internal network only

- **mTLS**: Optional for MVP, recommended for production

- **Trace propagation**: `traceparent` must be passed via gRPC metadata

- **Auth context**: System‑api passes `x-eigen-sub`, `x-eigen-roles`, `x-eigen-tenant` to KernelGateway

- **Metrics**: Each service exports Prometheus metrics on `/metrics`

## MVP Implementation Notes

1. **Streaming**: `PollJobUpdates` is used instead of true streaming for MVP simplicity

2. **Caching**: Kernel may cache device listings from driver‑manager

3. **Fallbacks**: Simulator driver must always be available

4. **Timeouts**: All inter‑service calls should have reasonable timeouts (configurable)

## Future Evolution

- True streaming from kernel to system‑api (Phase 1)

- Async/long‑running execution API for driver‑manager (Phase 1)

- More granular device capabilities and calibration API (Phase 2)

- Versioning of internal APIs (post‑MVP)

---

**References:**

    RFC 0004: Public gRPC API (client‑facing)

    RFC 0005: AQO format (compiler output)

    RFC 0006: QDriver API (driver‑manager plugin contract)

    RFC 0007: QRTX MVP (kernel pipeline)