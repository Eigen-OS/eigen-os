# Driver Manager

- **Phase**: MVP (current implementation baseline: MVP-3 runtime package)
- **Source**: RFC 0006 (`rfcs/0006-qdriver-api-v0.1.md`), RFC 0016 (`rfcs/0016-mvp3-kernel-driver-execution-contract.md`), ADR 0006, ADR 0007

## Responsibility

The Driver Manager is a core Eigen OS component that provides the internal `kernel -> driver-manager` runtime boundary via gRPC and normalizes backend execution responses.

**Implemented now:**

- gRPC `DriverManagerService` with `ListDevices`, `GetDeviceStatus`, `ExecuteCircuit`; `CalibrateDevice` is explicitly `UNIMPLEMENTED`.
- In-memory driver registry with device-to-driver ownership mapping.
- Base driver contract (`BaseDriver` / `QDriver`) with capability handshake and healthcheck.
- Request validation and backend error mapping to normalized gRPC status/details.
- Structured RPC start/end logging with `trace_id` extraction from gRPC metadata.
- Health and metrics HTTP endpoints exposed by service runtime.

**TODO (not fully implemented yet):**

- Dynamic runtime plugin discovery/loading/unloading from filesystem directories.
- Connection pooling abstraction for vendor SDK sessions.
- Built-in retry / circuit-breaker / failover orchestration in manager layer.
- Dedicated caches for metadata/results/compiled circuits with TTL policy controls.
- Full production SLO evidence for 99.9% availability target.

## Interfaces

### 1) External RPC interface (Kernel-facing)

**Implemented now:**

- Contract is generated from internal protobuf (`eigen_internal/v1/driver_manager_service.proto`).
- `DriverManagerService` methods:
  - `ListDevices()`
  - `GetDeviceStatus()`
  - `ExecuteCircuit()`
  - `CalibrateDevice()` (present in proto, returns `UNIMPLEMENTED` in service implementation)
- `ExecuteCircuitRequest` includes `job_id`, `device_id`, `payload`, `shots`, `options`.
- `ExecuteCircuitResponse` includes normalized `counts`, `execution_time_sec`, `metadata`.

**TODO:**

- Support additional `CircuitPayload.format` variants from RFC 0006 data model beyond current MVP path.
- Define/ship streaming or async execution API for long-running backend jobs (RFC 0006 open question, post-MVP).

### 2) Internal software interface (driver plugins)

 **Implemented now:**

- `BaseDriver` protocol methods present:
  - `initialize(config)`
  - `capability_handshake()`
  - `healthcheck()`
  - `get_devices()`
  - `execute_circuit(device_id, circuit, shots, options)`
  - `get_device_status(device_id)`
  - `calibrate_device(device_id, options)`

**TODO:**

- Enforce strict conformance suite for every plugin implementation (beyond current service tests).
- Freeze and version plugin capability feature schema across driver ecosystem phases.

### 3) Internal components and interfaces

**Implemented now:**

- `DriverRegistry`:
  - driver registration/removal,
  - duplicate-device ownership protection,
  - plugin runtime policy checks (`add_plugin_driver`) and reject counters,
  - capability and health snapshots.

**TODO:**

- `ConnectionPool` component (not yet present as standalone manager module).
- `ResilienceManager` (retry/backoff/circuit-breaker) as first-class shared component.
- `MetadataCache` / `ResultsCache` modules with configurable TTL/eviction.
- Prometheus metric families from architecture target list are not fully materialized yet.

## Inputs / Outputs

### Inputs

**Implemented now:**

1. Kernel gRPC requests:
   - `ListDevicesRequest`
   - `DeviceStatusRequest`
   - `ExecuteCircuitRequest`
   - `CalibrateDeviceRequest` (method currently unimplemented)
2. Driver objects registered during service bootstrap.
3. gRPC metadata used for trace context propagation (`traceparent`, `trace_id`).

**TODO:**

1. Externalized `driver_manager.yaml` config described by target architecture is not wired as normative source.
2. Filesystem plugin directory loading (`/usr/lib/eigen/drivers`, `./plugins`) is not active in current baseline.

### Outputs

**Implemented now:**

1. gRPC responses for list/status/execute flows with normalized result fields.
2. gRPC status/error details for validation and backend-mapped failures.
3. Service logs (`rpc_start`/`rpc_end`) including job/trace context fields.
4. Runtime HTTP `/metrics` and `/healthz` endpoints.

**TODO:**

- Expand response metadata conventions for queue-time/provider diagnostics across all drivers.
- Align logs with full target field set (`driver_name`, `device_id` for every path, standardized event taxonomy).

## Storage / State

### Internal state

### External Storage (QFS — Quantum File System):

**Implemented now:**

1. In-memory registry of drivers and device reverse index.
2. In-memory policy reject counters for plugin runtime guardrails.

**TODO:**

1. In-memory caches (metadata/status/results/topology) with TTL are not implemented as dedicated subsystems.
2. Optional distributed cache (Redis/Memcached) is not implemented.
3. Circuit-breaker state machine (`closed/open/half-open`) is not implemented.
4. Connection pool state is not implemented.

### External storage (QFS)

**Implemented now:**

- Contractually, long-term artifacts are owned outside driver-manager (`kernel`/QFS flows per runtime RFC package).

**TODO:**

- Add explicit integration notes/tests proving artifact lifecycle boundaries for all supported execution modes.

## Failure modes

### Implemented now

1. **Invalid request data**
   - required-field validation in `ExecuteCircuit`/`GetDeviceStatus`.
   - returns `INVALID_ARGUMENT` with structured violations.
2. **Unknown device**
   - mapped to normalized gRPC error response (`INVALID_ARGUMENT`).
3. **Unsupported payload format**
   - returns `UNIMPLEMENTED`.
4. **Driver execution failure**
   - mapped via backend error mapper into gRPC status/details.

### TODO

1. Automated retries with exponential backoff at manager layer.
2. Circuit-breaker state transitions and controlled recovery probing.
3. Fallback device routing strategy.
4. Connection-level health checking/timeout-based pool eviction.
5. Resource isolation limits for driver processes as a general runtime mechanism.
6. Formal availability SLO enforcement with objective evidence.

## Observability

### Implemented now

- Structured logging for gRPC lifecycle events in driver-manager.
- Trace context acceptance from gRPC metadata (`traceparent` + derived `trace_id`).
- Service-level `/metrics` and `/healthz` endpoints.

### TODO

1. Full Prometheus metric contract from architecture target state:
   - `eigen_driver_requests_total{driver,operation,status}`
   - `eigen_driver_request_duration_seconds{driver,operation}`
   - `eigen_driver_connections{driver,state}`
   - `eigen_available_devices{driver,provider}`
   - `eigen_device_queue_depth{driver,device_id}`
   - `eigen_driver_connection_errors_total{driver,error_type}`
2. OpenTelemetry spans emitted directly by driver-manager (current state is trace-context logging, not full tracing pipeline).
3. Complete health model exposing per-driver readiness/degradation in standardized endpoint payload.
4. Grafana-ready dashboards and alerting runbooks tied to driver-manager-specific SLO/SLI targets.
