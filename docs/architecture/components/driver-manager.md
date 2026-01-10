# Driver Manager

- **Phase**: MVP

- **Source**: RFC 0006

## Responsibility

The Driver Manager is a core component of Eigen OS responsible for unified management of quantum device and simulator drivers. Its primary purpose is to abstract the hardware specifics of various quantum platforms (e.g., IBM Qiskit, Google Cirq, AWS Braket) through a single software interface (QDriver API).

**Key Responsibilities:**

- **Dynamic loading and unloading of drivers** as plugins at runtime.

- **Connection pool management** with quantum devices for efficient reuse.

- **Ensuring fault tolerance** through retry mechanisms, Circuit Breaker patterns, and failover strategies.

- **Caching** of device metadata, execution results, and compiled circuits.

- **Monitoring** of driver and device health, and collection of performance metrics.

In the context of MVP (Phase 0), Driver Manager functions as an internal service that interacts with the **Kernel (QRTX)** via gRPC (``DriverManagerService``), while the service itself loads and uses Python driver plugins.

## Interfaces

### 1. External RPC Interface (for Kernel):

- Defined in `driver-manager.proto` (RFC 0006).

- `DriverManagerService`:

    - `ListDevices()` – list available devices.

    - `GetDeviceStatus()` – status of a specific device.

    - `ExecuteCircuit()` – execute a quantum circuit on a target device.

    - `CalibrateDevice()` – initiate device calibration.

- **Circuit payload format**: `CircuitPayload` containing `bytes` and `format` (e.g., `AQO_JSON`, `QASM3_TEXT`). The exact format for MVP is clarified in RFC 0006 open questions.

### 2. Internal Software Interface (for driver plugins):

- **Base class**: `BaseDriver` (from `src/plugins/base_driver.py`).

- **Required methods for driver implementation:**

    - `initialize(config)`

    - `get_devices()`

    - `execute_circuit(device_id, circuit, shots, options)`

    - `get_device_status(device_id)`

    - `calibrate_device(device_id)`

### 3. Internal Components and Their Interfaces:

- **Driver Registry** (`DriverRegistry`): Manages plugin lifecycle (loading, unloading, validation).

- **Connection Pool** (`ConnectionPool`): Manages reuse and timeout of device connections.

- **Resilience Manager** (`ResilienceManager`): Implements retry (with exponential backoff) and Circuit Breaker pattern.

- **Caching System** (`MetadataCache`, `ResultsCache`): Caches data with TTL.

- **Monitoring System** (`MetricsCollector`): Collects and exports metrics (Prometheus).

## Inputs / Outputs

### Inputs:

1. **Requests from Kernel (via gRPC)**:

    - `ExecuteCircuitRequest`: Contains `job_id`, `device_id`, `CircuitPayload` (circuit in one of the formats), `shots` count, execution `options`.

    - ListDevicesRequest / GetDeviceStatusRequest: Driver or device identifier.

2. **Configuration**: YAML file (`driver_manager.yaml`) defining driver load paths, connection pool parameters, resilience strategies, caching, and monitoring settings.

3. **Driver Plugins**: Python modules located in specified directories (`/usr/lib/eigen/drivers, ./plugins`) that implement the `BaseDriver` interface.

### Outputs:

1. **Responses to Kernel (via gRPC):**

    - `ExecuteCircuitResponse`: Normalized results (`counts` — dictionary of "bitstring → count"), execution time, metadata.

    - `ListDevicesResponse` / `DeviceStatusResponse`: List of devices or detailed status, including availability, queue depth, estimated wait time.

2. **Metrics and Logs**: Exports metrics in Prometheus format to a separate HTTP endpoint, structured logs with `trace_id`, `job_id`, `device_id`.

## Storage / State

### Internal State:

1. **Driver Registry**: In-memory storage of loaded driver classes, their instances, and metadata.

2. **Connection Pool**: In-memory management of active and idle connections to devices, tracking their state and last used time.

3. **Cache**:

    - **In-memory cache (default in MVP)**: For device metadata, statuses, topology, and execution results. Uses TTL.

    - **Optional distributed cache**: Configuration for Redis/Memcached (Phase 2+).

4. **Circuit Breaker State**: Tracks error counters and state ("closed"/"open"/"half-open") for each driver or device.

### External Storage (QFS — Quantum File System):

- Driver Manager **does not** manage long-term artifact storage.

- Compiled circuits (`AQO`) and execution results are persisted to QFS by the **Kernel** under paths like `circuit_fs/<job_id>/`.

- Driver Manager may cache this data short-term for performance.

## Failure Modes

### Common Failure Scenarios and Handling Strategies:

1. **Driver or Device Failure:**

    - **Retry**: Automatic retries with exponential backoff (configurable).

    - **Circuit Breaker**: Temporarily blocks calls to problematic driver/device when error threshold is exceeded, allowing recovery.

    - **Failover**: Switching to a fallback device (e.g., simulator) according to configured strategy (`fallback_devices`).

2. **Network Connection Loss:**

    - Connection pool detects and closes idle connections via timeout.

    - Health-check periodically verifies device availability.

3. **Invalid Input Data (Circuit):**

    - Driver or manager validates `CircuitPayload`. Returns gRPC status `INVALID_ARGUMENT` on error.

4. **External Service Unavailability (Provider Backend):**

    - Mapped to gRPC status `UNAVAILABLE`.

    - Activation of graceful degradation strategy.

5. **Resource Exhaustion (Memory, Connections):**

    - Maximum connection pool size limit.

    - Driver isolation in separate processes with memory and CPU limits (Phase 1+).

**Guarantees**: Within MVP, Driver Manager aims to provide high availability (99.9%) and automatic recovery from failures.

## Observability

### Metrics (Prometheus):

- **Core Metrics**: `eigen_driver_requests_total{driver, operation, status}`, `eigen_driver_request_duration_seconds{driver, operation}`.

- **Connection Metrics**: `eigen_driver_connections{driver, state}` (active, idle).

- **Device Metrics**: `eigen_available_devices{driver, provider}`, `eigen_device_queue_depth{driver, device_id}`.

- **Error Metrics**: `eigen_driver_connection_errors_total{driver, error_type}`.

- **Endpoint**: HTTP (e.g., `:9092/metrics`).

### Logs (Structured, JSON):

- Required fields: `timestamp`, `level`, `service="driver-manager"`, `trace_id`, `job_id`, `driver_name`, `device_id`, `message`.

- Key events logged: driver load/unload, connection create/close, retry/Circuit Breaker triggers, execution errors.

### Tracing (Distributed Tracing):

- Integration with OpenTelemetry. Trace context (`traceparent`) is propagated via gRPC metadata from System API through Kernel to Driver Manager.

- Enables end-to-end request tracing across all services.

### Health Monitoring:

- Health-check endpoints for monitoring Driver Manager and loaded driver status.

- Integration with stack monitoring system (e.g., Grafana).