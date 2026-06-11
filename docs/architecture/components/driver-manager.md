# Driver Manager

**Status:** Normative architecture + implementation specification (Eigen OS 1.0 / MVP + approved extensions)
**Subsystem:** Runtime driver orchestration, backend abstraction, execution normalization, device/capability management
**Primary consumers:** `eigen-kernel (QRTX)` and internal runtime services
**Security posture:** Internal-only service; treats all payloads as executable input; zero-trust across boundaries

---

## 1. Purpose

`driver-manager` (DM) is the Eigen OS runtime subsystem responsible for abstracting heterogeneous quantum hardware and simulators behind a unified internal execution interface.

The Driver Manager provides:

- a stable execution boundary between `eigen-kernel` and backend providers,
- normalized device discovery, health, topology, and capability semantics,
- unified driver lifecycle and session management,
- execution dispatch and result normalization,
- backend/provider error normalization into the Eigen OS error model,
- observability and fault isolation for backend interactions,
- security controls for credentials and driver supply chain.

**Only the Driver Manager is allowed to communicate directly with vendor SDKs, cloud quantum APIs, simulator runtimes, or hardware-specific execution libraries.** Kernel and public services must never depend on provider SDKs directly.

---

## 2. Architectural Role

Driver Manager belongs to the Runtime Services layer.

```text
Client
  ↓
system-api
  ↓
eigen-kernel (QRTX)
  ↓
driver-manager
  ↓
QDriver implementations (plugins / remote driver services)
  ↓
Quantum backend / simulator / vendor cloud
```

DM acts as:

- execution abstraction layer
- capability registry
- normalization gateway
- fault isolation boundary
- credential boundary
- device topology source (for hardware-aware compilation/optimization)

---

## 3. Core Responsibilities

### 3.1 Device Catalog & Capability Registry

DM MUST maintain a consistent, queryable view of:

Driver Manager is the canonical source of device topology and capability truth
for Resource Manager inventory snapshots and Kernel scheduling decisions.

- available devices,
- device identity and stable `device_id`,
- device capabilities (`max_qubits`, supported gate sets, dynamic circuit - support, mid-circuit measurement, etc.),
- device health and availability,
- device topology/connectivity (when applicable),
- queue / capacity hints (when available).

DM MUST provide a snapshot-style interface to the kernel for:

- `ListDevices`
- `GetDeviceStatus`
- `GetDeviceDetails` (if present in internal APIs)

---

### 3.2 Execution Dispatch

DM MUST accept execution requests from the kernel and:

1. validate request envelope and payload format,
2. select the appropriate driver/device session,
3. translate the payload into backend-native format if required,
4. execute the circuit on the provider runtime,
5. normalize the result into the canonical Eigen OS `ExecutionResult` shape,
6. normalize provider errors into the canonical Eigen OS error model.

---

### 3.3 Result Normalization

DM MUST return backend-independent results:

- canonical `counts` bitstring ordering (per system contract),
- stable metadata keys (backend id/name, timing, shots, etc.),
- stable error mapping (gRPC status + structured details).

Normalization MUST be deterministic for equivalent backend outputs.

---

### 3.4 Driver Lifecycle & Session Management

DM MUST:

- load and register drivers,
- create per-device sessions when needed,
- manage connection pools for providers (where applicable),
- implement safe shutdown and restart behavior,
- support rolling updates of drivers (graceful restart of sessions).

---

### 3.5 Device Topology Source for Hardware Optimization

DM MUST expose device topology and calibration/health snapshots to QRTX so QRTX can:

- provide deterministic inventory material to Resource Manager,
- request topology via `GetDeviceStatus` / `GetDeviceDetails`,
- feed topology into hardware-aware optimization (e.g., GNN placement/routing).

This is required by the technical specification architecture: **GNN-optimizer consumes device topology obtained via Driver Manager**.

---

## 4. Implementation Status (Repository Truthfulness)

### 4.1 Implemented Today

- Internal gRPC service: `DriverManagerService`
  - `ListDevices`
  - `GetDeviceStatus`
  - `ExecuteCircuit`
- In-memory registry:
  - driver registration and device ownership mapping
  - capability snapshots
  - basic health snapshots
- Execution normalization:
  - counts normalization
  - execution metadata passthrough (partial standardization)
  - backend error translation into canonical gRPC status model (baseline)
- Observability endpoints:
  - `/healthz`
  - `/metrics`
  - structured RPC lifecycle logging
  - trace-context propagation

---

### 4.2 Partially Implemented

- OpenTelemetry span coverage (trace propagation exists; full per-driver spans incomplete)
- Metadata schema standardization across all drivers
- Connection reuse policies (some drivers may reuse sessions; pooling not uniform)

---

### 4.3 Planned / Required by Target Architecture (TЗ)

- Dynamic driver discovery and loading (plugin ecosystem)
- Connection pooling, circuit breakers, retries, failover routing
- Signed driver verification (supply chain hardening)
- Driver isolation (container/process sandbox, least privilege)
- Credential vault integration (secret storage; no secrets in configs/artifacts)
- Rich topology/calibration APIs for hardware optimization pipelines
- Capability/version negotiation and compatibility checks

---

## 5. Driver Model: QDriver API and Plugin Modes

Eigen OS supports two normative driver integration modes:

### 5.1 Mode A — In-process Plugin (Current baseline + extension)

Drivers are Python modules/packages (or FFI binaries) loaded by DM.

Normative Python interface (conceptual):

```python
class BaseDriver:
    async def initialize(self, config): ...
    async def capability_handshake(self): ...
    async def healthcheck(self): ...
    async def get_devices(self): ...
    async def execute_circuit(self, request): ...
    async def get_device_status(self, device_id): ...
    async def calibrate_device(self, device_id): ...
```

**Determinism / idempotency requirements** apply equally to both modes.

---

### 5.2 Mode B — Remote QDriver Service (TЗ architecture-aligned)

A QDriver is a **gRPC service** implementing a stable device-facing contract.

Normative methods (conceptual, per TЗ):

- `Initialize(DeviceConfig) -> InitResponse`
- `Execute(ExecutionRequest) -> ExecutionResponse`
- `GetStatus(StatusRequest) -> DeviceStatus`
- `Calibrate(...) -> ...` (optional; may be unimplemented depending on device)

DM acts as the client of QDriver services and provides the kernel-facing abstraction.

---

### 5.3 Isolation Requirement

Drivers MUST run with **minimum privilege** and SHOULD be isolated:

- separate process or container sandbox preferred,
- restricted filesystem/network capabilities,
- no access to kernel memory space.

---

## 6. Kernel-Facing gRPC Interface (Internal)

Canonical internal namespace:

```text
eigen.internal.v1.DriverManagerService
```

### 6.1 Methods

| **Method** | **Status** | **Notes** |
|---|---|---|
| `ListDevices` | Implemented | returns device catalog snapshot |
| `GetDeviceStatus` | Implemented | returns health/topology hints (partial) |
| `ExecuteCircuit` | Implemented | primary execution entrypoint |
| `CalibrateDevice` | Defined; may return `UNIMPLEMENTED` | optional per backend |

---

### 6.2 ExecuteCircuit Contract (Normative Semantics)

Conceptual request:

```protobuf
message ExecuteCircuitRequest {
  string job_id = 1;          // required correlation identity
  string device_id = 2;       // required target device
  CircuitPayload payload = 3; // required (AQO/QASM/etc)
  uint32 shots = 4;           // required for sampling workloads
  uint64 seed = 5;            // optional but REQUIRED for deterministic simulator replay
  map<string,string> options = 6; // optional bounded options
}
```

Conceptual response:

```protobuf
message ExecuteCircuitResponse {
  map<string,int64> counts = 1;
  double execution_time_sec = 2;
  map<string,string> metadata = 3; // bounded metadata only
}
```

#### Determinism Rules

- If `seed` is provided and the backend is a simulator, DM/drivers MUST ensure the simulator uses that seed so the result is replay-stable.
- DM MUST ensure count normalization is deterministic (canonical bit ordering, stable encoding).

#### Idempotency / Retry Safety

- Driver execution SHOULD be idempotent where supported.
- If the backend supports idempotency tokens, DM SHOULD map (`job_id`, `device_id`, `attempt`) to provider idempotency mechanisms.
- Retries MUST NOT silently change semantic options (shots/seed/payload).

---

## 7. Supported Payload Formats

DM MUST accept a `CircuitPayload` which includes:

- `format` (e.g., `AQO_JSON`, `AQO_PROTO`, `QASM`)
- payload bytes or a QFS reference
- optional format-specific metadata (bounded)

Current MVP supported formats:

- AQO JSON (primary)
- QASM (partial / backend-dependent)

Planned:

- AQO protobuf (`AQO_PROTO`)
- backend-native IR (internal only)

Unsupported formats MUST return:

- `UNIMPLEMENTED` (per error model)

---

## 8. Execution Flow

### Device Capability Model

Drivers MUST expose a bounded, stable capability snapshot. Example (illustrative):

```json
{
  "driver_name": "ibm_quantum",
  "driver_version": "1.2.3",
  "backend_type": "superconducting",
  "max_qubits": 127,
  "supports_dynamic_circuits": true,
  "supports_mid_circuit_measurement": true,
  "supports_feed_forward": false,
  "native_gate_set": ["rz", "sx", "cx"],
  "topology": "heavy_hex",
  "connectivity": "sparse"
}
```

#### Capability/Version Registration

At startup (or on refresh), DM SHOULD:

- dynamically load available drivers,
- register driver metadata (name, version, supported devices),
- reject duplicates and incompatible versions deterministically.

---

## 9. Failure Model (Aligned with Error Model / Error Mapping)

DM MUST follow the canonical Eigen OS error model:

- **Transport failures:** gRPC status codes
- **Validation failures:** `INVALID_ARGUMENT` with structured field violations
- **Missing resources: `NOT_FOUND` for unknown `device_id` (preferred)
- **Unsupported featur**e/format:** `UNIMPLEMENTED`
- **Backend/provider outages:** `UNAVAILABLE` (+ `RetryInfo` when appropriate)
- **Quota/capacity limits:** `RESOURCE_EXHAUSTED` (+ `RetryInfo` when appropriate)
- **Unexpected invariants:** `INTERNAL` with correlation metadata

---

### 9.1 Common Mappings

| **Condition** | **Canonical status** |
|---|---|
| Unknown `device_id` | `NOT_FOUND` |
| Malformed payload / schema invalid | `INVALID_ARGUMENT` |
| Unsupported payload format | `UNIMPLEMENTED` |
| Provider throttling / quota exceeded | `RESOURCE_EXHAUSTED` |
| Provider outage / network partition | `UNAVAILABLE` |
| Execution deadline exceeded | `DEADLINE_EXCEEDED` |
| Internal driver crash/panic | `INTERNAL` |

**Provider-native errors MUST be normalized**; raw provider payloads must not leak to public surfaces.

---

## 10. Security Model

### 10.1 Internal-Only Boundary

- DM MUST NOT be publicly reachable.
- All DM RPCs MUST be protected via **TLS 1.3** and SHOULD use **mTLS** for service-to-service auth, consistent with Eigen OS internal security posture.

---

### 10.2 Credential Handling (Mandatory)

- Provider credentials (API keys/tokens/certs) MUST be stored in a **secure secrets store** (vault/secret manager).
- Credentials MUST NOT be embedded in:
  - JobSpec,
  - AQO,
  - QFS artifacts,
  - logs,
  - metrics labels.
- Drivers may receive credentials **only on demand** and only for the duration required.

---

### 10.3 Supply Chain Hardening (Mandatory)

DM MUST support driver trust controls:

- drivers stored in a trusted registry,
- drivers SHOULD be signed,
- DM SHOULD verify signatures/metadata before loading,
- failed verification MUST prevent driver activation deterministically.

---

### 10.4 Least Privilege & Isolation

- Drivers SHOULD run in isolated containers/processes.
- DM MUST restrict driver capabilities (filesystem/network) to the minimum needed.

---

## 11. Observability

### 11.1 Implemented

- structured RPC lifecycle logs: `rpc_start` / `rpc_end`
- correlation fields:
  - `trace_id`
  - `job_id`
  - `method`
  - `device_id`
- `/metrics` and `/healthz`

---

### 11.2 Required Telemetry Shape (Normative Targets)

DM SHOULD export bounded-cardinality metrics such as:

```text
eigen_driver_requests_total{method,device_class,result}
eigen_driver_request_duration_seconds_bucket{method,device_class}
eigen_driver_sessions{driver}
eigen_driver_backend_failures_total{taxonomy}
eigen_available_devices{device_class}
```

Rules:

- labels MUST be bounded (no `job_id`, `trace_id`, raw device ids if unbounded)
- exporter MUST never block execution critical paths
- metrics failures MUST NOT terminate execution

---

### 11.3 Tracing Requirements

Target spans:

- DM `ExecuteCircuit` span (parented to kernel span)
- per-driver execution span
- backend API latency span (where meaningful)

Trace continuity must be preserved across DM → driver → backend boundaries.

---

## 12. Performance Targets

MVP engineering targets (not strict guarantees):

| **Metric** | **Target** |
|---|---|
| Device lookup | < 10 ms |
| Dispatch overhead | < 50 ms |
| Registry lookup | O(1) |
| Service availability | 99.9% |


---

## 13. Architectural Invariants

1. **Abstraction invariant:** Kernel must never depend on vendor SDKs directly.
2. **Normalization invariant:** Equivalent backend results must produce identical normalized result structures.
3. **Isolation invariant:** Driver failures must not crash kernel runtime; DM must contain failures.
4. **Determinism invariant:** Canonical normalization, seed handling (for simulators), and error mapping are deterministic.
5. **Security invariant:** Credentials never leak to clients, logs, metrics labels, or artifacts.
6. **Supply-chain invariant:** Untrusted drivers must not be loaded.
7. **Observability invariant:** All execution flows propagate `trace_id` and correlate with `job_id`.

---

## 14. Compliance Snapshot

| **Capability** | **Status** |
|---|---|
| gRPC runtime boundary | Implemented |
| Driver abstraction | Implemented (baseline) |
| Execution normalization | Implemented (baseline) |
| Health endpoints | Implemented |
| Structured logging | Implemented |
| Simulator drivers | Implemented |
| Unknown device mapping to `NOT_FOUND` | Required (ensure alignment across implementations) |
| Dynamic plugin system | Planned / Required |
| Connection pooling | Planned / Required |
| Retry/failover orchestration | Planned |
| Driver isolation | Partially present / Required |
| Secret vault integration | Planned / Required |
| Signed driver verification | Planned / Required |
| Full OTel spans | Partial |
| Topology/calibration rich API | Partial / Required for HW optimization |

---

## 15. Conclusion

The Driver Manager is the **hardware abstraction and execution orchestration gateway** of Eigen OS.

It already provides an MVP-capable execution boundary with:

- internal gRPC interface,
- driver registry,
- normalized execution results,
- baseline error normalization,
- observability endpoints.

To fully match the technical specification (ТЗ) target architecture, DM additionally MUST (as the system hardens):

- dynamically load and verify drivers (signed supply chain),
- isolate drivers with least privilege,
- integrate secure secret storage for provider credentials,
- standardize connection pooling, retries, and circuit breakers,
- provide reliable topology/health snapshots for hardware-aware optimization,
- preserve deterministic behavior for replay and simulator seed control.

---

## Appendix A. Diagrams (normative)

### A.1 C4 Service Container View (Driver Manager in runtime)

![Service Container View](https://i.imgur.com/Ec8IgMQ.png)

<details>
<summary>code</summary>

```text
flowchart TB
    subgraph ClientLayer ["Client Layer"]
        Client[Client SDKs / CLI]
    end

    subgraph Core ["Core Services"]
        SysAPI["system-api (public gRPC)"]
        Kernel["eigen-kernel / QRTX"]
        DM["driver-manager (internal gRPC)"]
    end

    subgraph Drivers ["Driver Layer"]
        Plugins["In-process QDriver plugins"]
        RemoteDrivers["Remote QDriver services (gRPC)"]
        Providers["Vendor SDKs / Simulators"]
    end

    Client --> SysAPI
    SysAPI --> Kernel
    Kernel --> DM
    DM -->|Mode A| Plugins
    DM -->|Mode B| RemoteDrivers
    Plugins --> Providers
    RemoteDrivers --> Providers

    DM --> QFS["QFS (artifacts/refs)"]
    DM --> Obs["Observability (OTel/metrics/logs)"]
    DM --> Secrets["Secret store / Vault"]
```

</details>

---

### A.2 C4 Component diagram — driver-manager internals

![Component diagram — driver-manager](https://i.imgur.com/Xv3MgiA.png)

<details>
<summary>code</summary>

```text
flowchart LR
    subgraph DM["driver-manager"]
        API["DriverManagerService (gRPC)<br/>ListDevices / GetDeviceStatus / ExecuteCircuit"]
        Registry["Driver Registry<br/>(driver_id → devices, capabilities)"]
        Catalog["Device Catalog<br/>(stable device_id, class, caps)"]
        SessionMgr["Session Manager<br/>(pools, sessions, lifecycle)"]
        Exec["Execution Dispatcher<br/>(validate → translate → run)"]
        Normalizer["Result Normalizer<br/>(counts ordering, metadata schema)"]
        ErrMap["Error Normalizer<br/>(provider → Eigen error model)"]
        Topology["Topology & Calibration Snapshot<br/>(connectivity, health hints)"]
        Supply["Supply-chain verifier<br/>(signature/manifest checks)"]
        SecretsClient["Secrets Client<br/>(on-demand credential fetch)"]
        Telemetry["Telemetry<br/>(logs/metrics/traces)"]
    end

    API --> Exec
    Exec --> SessionMgr
    Exec --> Normalizer
    Exec --> ErrMap
    Registry --> Catalog
    Registry --> SessionMgr
    Catalog --> Topology
    Supply --> Registry
    SecretsClient --> SessionMgr

    Telemetry --- API
    Telemetry --- Exec
    Telemetry --- SessionMgr
```

</details>

---

### A.3 Sequence: ExecuteCircuit — canonical dispatch path

![ExecuteCircuit](https://i.imgur.com/xn7DgDt.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant K as eigen-kernel (QRTX)
  participant DM as driver-manager
  participant S as Session Manager
  participant D as QDriver (plugin/remote)
  participant P as Provider backend / simulator

  K->>DM: ExecuteCircuit(job_id, device_id, payload_ref/bytes, shots, seed?, options)\n(trace ctx)
  DM->>DM: Validate envelope + payload format\n(bound options, size limits)
  DM->>S: AcquireSession(device_id)
  alt credentials required
    DM->>DM: Fetch credentials (on-demand)
    DM->>S: Inject ephemeral creds (no logs)
  end
  S->>D: execute_circuit(request)\n(trace ctx)
  D->>P: Provider-native call (SDK/API)
  P-->>D: Provider result / error
  D-->>S: Raw result / error
  S-->>DM: Raw result / error
  DM->>DM: Normalize counts + metadata schema
  DM->>DM: Map provider errors -> canonical Eigen error model
  DM-->>K: ExecuteCircuitResponse(counts, metadata) OR gRPC status + structured details
```

</details>

---

### A.4 Sequence: Device catalog refresh (startup + periodic)

![Device catalog refresh](https://i.imgur.com/52vWSbv.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant DM as driver-manager
  participant Supply as Supply-chain verifier
  participant D as QDriver (plugin/remote)
  participant P as Provider backend

  DM->>Supply: Verify driver manifests/signatures (if enabled)
  alt verification OK
    Supply-->>DM: OK
    DM->>D: initialize(config)
    D-->>DM: init_ok
    DM->>D: capability_handshake()
    D->>P: Capability query (if applicable)
    P-->>D: caps/topology/health hints
    D-->>DM: capability snapshot (bounded)
    DM->>DM: Update registry + device catalog snapshot (atomic)
  else verification failed
    Supply-->>DM: FAIL
    DM->>DM: Disable driver deterministically (no partial activation)
  end
```

</details>

---

### A.5 Sequence: Provider error normalization (DM boundary)

![Provider error normalization](https://i.imgur.com/WNZIGYY.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant DM as driver-manager
  participant Supply as Supply-chain verifier
  participant D as QDriver (plugin/remote)
  participant P as Provider backend

  DM->>Supply: Verify driver manifests/signatures (if enabled)
  alt verification OK
    Supply-->>DM: OK
    DM->>D: initialize(config)
    D-->>DM: init_oksequenceDiagram
  autonumber
  participant K as eigen-kernel (QRTX)
  participant DM as driver-manager
  participant D as QDriver
  participant P as Provider

  K->>DM: ExecuteCircuit(...)
  DM->>D: execute_circuit(...)
  D->>P: call
  P-->>D: error (provider-specific)
  D-->>DM: error (raw)
  DM->>DM: Classify + map error -> canonical gRPC status
  DM->>DM: Attach google.rpc.Status details\n(ErrorInfo, RetryInfo where applicable)
  DM-->>K: gRPC status (UNAVAILABLE/RESOURCE_EXHAUSTED/...)\n+ structured details
    DM->>D: capability_handshake()
    D->>P: Capability query (if applicable)
    P-->>D: caps/topology/health hints
    D-->>DM: capability snapshot (bounded)
    DM->>DM: Update registry + device catalog snapshot (atomic)
  else verification failed
    Supply-->>DM: FAIL
    DM->>DM: Disable driver deterministically (no partial activation)
  end
```

</details>

---

### A.6 Determinism boundary (seed + normalization)

![Determinism boundary](https://i.imgur.com/3LQCjp2.png)

<details>
<summary>code</summary>

```text
flowchart TB
    Req["ExecuteCircuitRequest<br/>(job_id, device_id, payload, shots, seed?, options)"] 
    --> V["Validation<br/>(size/format/options bounded)"]

    V --> Exec["Provider execution"]
    
    Exec --> Raw["Raw provider result<br/>(counts/metadata/error)"]
    
    Raw --> Norm["Deterministic Normalizer<br/>(bit ordering, stable keys)"]
    Norm --> Out["ExecutionResult<br/>(counts + bounded metadata)"]
    
    Raw --> Map["Deterministic Error Mapper<br/>(provider → Eigen error model)"]
    Map --> Err["gRPC status + structured details"]

    seednote["If backend is a simulator and seed is provided,<br/>result MUST be replay-stable for same inputs."]
    
    Norm --- seednote
```

</details>

---

### A.7 Deployment & trust boundaries (driver-manager)

![Deployment & trust boundaries](https://i.imgur.com/84zJRJ3.png)

<details>
<summary>code</summary>

```text
flowchart LR
    subgraph TrustedRuntime["Eigen OS internal network (trusted by policy)"]
        K["eigen-kernel (mTLS)"] --> DM["driver-manager (mTLS)"]
        DM --> Secrets["Secret store / Vault"]
        DM --> Obs["OTel Collector / Prometheus"]
    end

    subgraph UntrustedOrExternal["External / vendor boundary"]
        Providers["Vendor clouds / QPUs / simulators"]
    end

    DM -->|"egress restricted<br/>allowlist"| Providers

    note1["DM is internal-only.<br/>Providers are treated as untrusted.<br/>Drivers are treated as executable input."]

    DM --- note1

    classDef trusted fill:#e6f7e6,stroke:#2e8b57
    classDef untrusted fill:#fff0f0,stroke:#d9534f
    class TrustedRuntime trusted
    class UntrustedOrExternal untrusted
```

</details>
