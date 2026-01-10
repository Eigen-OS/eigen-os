# RFC 0006: QDriver API v0.1 and Driver Manager service contract

- **Status:** Discussion
- **Authors:** NYankovich
- **Created:** 2026-01-08
- **Target milestone:** Phase 0 (MVP)
- **Tracking issue:** (TBD)
- **Supersedes / Related:** 0004,0005,0007

## Summary

Defines the standardized driver interface and the RPC contract between kernel and driver-manager.

## Motivation

Hardware diversity is the main integration risk. A small, strict QDriver API lets the kernel run on simulators and real QPUs via plugins.

## Goals

- Lock down BaseDriver method set for MVP.
- Define DriverManagerService RPC used by kernel.
- Define result normalization (counts + metadata).

## Non-Goals

- Pulse-level control.
- Full calibration pipelines and noise models (Phase 2).

## Guide-level explanation

Driver manager loads drivers from `driver-manager/src/plugins/*_driver.py`.
Each driver implements BaseDriver methods:
- `initialize(config)`
- `get_devices()`
- `execute_circuit(device_id, circuit, shots, options)`
- `get_device_status(device_id)`
- `calibrate_device(device_id)`

Kernel talks to driver-manager via gRPC (DriverManagerService). Driver-manager then calls plugin driver.

## Reference-level design

### Interfaces / APIs

### driver-manager.proto (internal, kernel-facing)

```proto
service DriverManagerService {
  rpc ListDevices(ListDevicesRequest) returns (ListDevicesResponse);
  rpc GetDeviceStatus(DeviceStatusRequest) returns (DeviceStatusResponse);
  rpc ExecuteCircuit(ExecuteCircuitRequest) returns (ExecuteCircuitResponse);
  rpc CalibrateDevice(CalibrateDeviceRequest) returns (CalibrateDeviceResponse);
}

message ExecuteCircuitRequest {
  string job_id = 1;
  string device_id = 2;
  CircuitPayload payload = 3;  // AQO/QASM/native bytes + format enum
  int32 shots = 4;
  map<string,string> options = 5;
}

message ExecuteCircuitResponse {
  map<string,int64> counts = 1;
  double execution_time_sec = 2;
  map<string,string> metadata = 3;
}
```


### Data model

**CircuitPayload:** `{format, bytes}` where format ∈ {AQO_JSON, AQO_PROTO, QASM3_TEXT, BACKEND_NATIVE}.
**DeviceInfo:** `device_id`, `name`, `backend_type`, `status`, `queue_depth`, `estimated_wait_time`.
Driver-manager must normalize backend results into `counts` (bitstring→count).

### Error model

For MVP, **DriverManagerService MUST use gRPC status codes for failures** (non-OK), optionally with structured details.
The response message itself must not contain `success` flags or `error_message` fields.


Driver errors are mapped to gRPC statuses:
- UNAVAILABLE: backend down
- FAILED_PRECONDITION: device offline
- INVALID_ARGUMENT: bad payload
- UNIMPLEMENTED: unsupported format

### Security & privacy

Driver-manager runs on private network.
No direct user access.
Options/config must be validated to avoid injecting arbitrary code paths.

### Observability

Per-driver metrics: request count/latency, error rate, backend wait time.
Logs include `job_id`, `device_id`, `driver_name`, `trace_id`.

### Performance notes

Driver-manager should keep connection pools and reuse SDK clients.
Payload size can be large; prefer bytes + references for huge circuits (future).

## Testing plan

Compliance tests for BaseDriver methods.
SimulatorDriver must be the golden reference for MVP.
Integration test: kernel ExecuteCircuit → simulator → results.

## Rollout / Migration

MVP supports simulator only by default; real drivers come in Phase 2.

## Alternatives considered

- Embed vendor SDKs directly in kernel (rejected: Rust ecosystem mismatch).
- Only Python kernel (rejected: performance and safety goals).

## Open questions

- Do we need an async streaming execution API for long-running jobs in Phase 1?
- Where do we store calibration artifacts (QFS vs driver-manager cache)?
