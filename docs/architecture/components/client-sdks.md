# Eigen OS Client SDKs

Status snapshot: updated on 2026-05-25 based on implemented repository state, RFC index, ADR index, integration tests, and architectural contracts.

This document is the canonical specification of the Eigen OS Client SDK layer.
It explicitly separates:

- functionality required by the technical specification (target architecture),
- functionality already implemented,
- functionality planned but not yet implemented.

The document is normative for SDK architecture, public contracts, and integration behavior.

---

## 1. Purpose

The Eigen OS Client SDKs provide standardized client interfaces for interacting with the Eigen OS distributed hybrid quantum-classical runtime.

The SDK layer abstracts:

- transport protocols,
- authentication,
- serialization,
- job lifecycle management,
- observability,
- compatibility handling,
- backend communication complexity.

The SDKs are intended for:

- research environments,
- production orchestration systems,
- ML/AI pipelines,
- scientific computing workflows,
- cloud automation platforms,
- IDE and notebook integrations.

---

## 2. Scope

The Client SDK layer is responsible for:

- submitting quantum and hybrid jobs,
- interacting with runtime services,
- monitoring execution state,
- retrieving execution results,
- querying device information,
- managing authentication and session state,
- exposing observability hooks,
- handling retries and transport failures,
- providing language-native developer ergonomics.

The SDK layer is **not responsible** for:

- executing quantum programs locally,
- bypassing Eigen OS validation,
- direct hardware access,
- server-side scheduling,
- compilation determinism guarantees,
- runtime isolation.

Those responsibilities belong to the Eigen OS backend services.

---

## 3. Supported SDKs

### 3.1 Current Status

| **SDK** | **Status** | **Notes** |
|---|---|---|
| Python SDK | Planned | Primary reference SDK |
| Rust SDK | Planned | High-performance production integration |
| JavaScript/TypeScript SDK | Planned | Browser and Node.js support |
| CLI | Partially implemented | Uses gRPC APIs |
| Go SDK | Deferred | Not part of MVP |
| Java SDK | Deferred | Enterprise roadmap item |

---

## 4. Architectural Principles

### 4.1 Unified API Semantics

All SDKs MUST expose equivalent semantic behavior:

- identical lifecycle concepts,
- consistent naming,
- compatible error categories,
- equivalent transport behavior,
- equivalent authentication behavior.

Language-specific idioms MAY differ, but behavioral contracts MUST remain equivalent.

---

### 4.2 Transport-First Architecture

#### Mandatory transport hierarchy

| **Priority** | **Transport** | **Status** |
|---|---|---|
| Primary | gRPC | Implemented |
| Secondary | REST | Planned |
| Streaming | WebSocket | Planned |

#### Current implementation

Implemented now:

- gRPC transport,
- protobuf-based serialization,
- server-streaming job updates.

Not implemented:

- REST fallback transport,
- WebSocket real-time transport,
- automatic transport failover.

---

### 4.3 Stateless Client Model

SDK clients SHOULD remain stateless whenever possible.

Persistent state MAY include:

- auth credentials,
- connection pools,
- local cache entries,
- retry metadata.

Execution state is authoritative only on Eigen OS services.

---

### 4.4 Versioned Contracts

All SDKs MUST follow versioned API contracts defined by:

- RFC 0003 — JobSpec,
- RFC 0004 — Public APIs,
- RFC 0005 — AQO,
- RFC 0006 — Driver API,
- RFC 0011 — Program sources,
- RFC 0012 — Eigen-Lang subset.

---

## 5. Implemented Architecture

### 5.1 Public API Surface

Implemented public services:

| **Service** | **Status** |
|---|---|
| JobService | Implemented |
| DeviceService | Implemented |

Internal-only services:

| **Service** | **Status** |
|---|---|
| CompilationService | Internal-only |

Compilation APIs are not currently exposed as stable public SDK endpoints.

---

### 5.2 Transport Layer

Implemented:

- gRPC channels,
- protobuf serialization,
- streaming RPC updates,
- request validation,
- status/error propagation.

Planned:

- REST transport,
- WebSocket transport,
- automatic transport downgrade.

---

### 5.3 Authentication Baseline

Implemented:

- service-side auth enforcement,
- token propagation,
- request authorization hooks.

Not yet standardized across SDKs:

- JWT helpers,
- OAuth2 flows,
- API key abstraction,
- mTLS helpers,
- token refresh lifecycle.

---

### 5.4 Validation

Implemented:

-  JobSpec validation,
- Eigen-Lang AST restrictions,
- request schema validation,
- protobuf validation contracts.

Planned:

- client-side preflight validation wrappers,
- unified validation middleware across SDK languages.

---

### 5.5 Observability

Implemented:

- trace propagation,
- correlation IDs,
- structured service logs,
- OpenTelemetry-compatible tracing.

Planned:

- dedicated SDK telemetry packages,
- SDK metric exporters,
- standardized SDK log schemas.

---

## 6. SDK Responsibilities

The SDK layer MUST provide the following capabilities.

### 6.1 Job Submission

The SDK MUST support submission of:

- Eigen-Lang source,
- OpenQASM 3.0 source,
- AQO references.

Submission MUST support:

- compiler options,
- metadata,
- priority,
- target backend selection.

---

### 6.2 Job Lifecycle Management

SDKs MUST support:

- job creation,
- status polling,
- streaming updates,
- cancellation,
- result retrieval.

---

### 6.3 Device Interaction

SDKs MUST support:

- listing devices,
- querying device status,
- querying capabilities,
- device reservation requests.

---

### 6.4 Error Handling

SDKs MUST expose structured error categories.

Mandatory categories:

| **Category** | **Description** |
|---|---|
| NetworkError | Transport/connectivity failure |
| AuthenticationError | Invalid or expired credentials |
| AuthorizationError | Access denied |
| ValidationError | Invalid request payload |
| ResourceError | Quota/device exhaustion |
| InternalError | Server-side failure |
| TimeoutError | Deadline exceeded |

---

### 6.5 Observability Hooks

SDKs MUST support:

- trace propagation,
- metrics emission,
- structured logging hooks,
- correlation IDs.

---

## 7. Public Interfaces

### 7.1 JobService

#### SubmitJob

```text
rpc SubmitJob(SubmitJobRequest)
    returns (JobResponse);
```

#### GetJobStatus

```text
rpc GetJobStatus(JobStatusRequest)
    returns (JobStatusResponse);
```

#### CancelJob

```text
rpc CancelJob(CancelJobRequest)
    returns (CancelJobResponse);
```

#### StreamJobUpdates

```text
rpc StreamJobUpdates(JobUpdatesRequest)
    returns (stream JobUpdate);
```

#### GetJobResults

```text
rpc GetJobResults(JobResultsRequest)
    returns (JobResultsResponse);
```

---

### 7.2 DeviceService

#### ListDevices

```text
rpc ListDevices(ListDevicesRequest)
    returns (ListDevicesResponse);
```

#### GetDeviceDetails

```text
rpc GetDeviceDetails(DeviceDetailsRequest)
    returns (DeviceDetailsResponse);
```

#### GetDeviceStatus

```text
rpc GetDeviceStatus(DeviceStatusRequest)
    returns (DeviceStatusResponse);
```

#### ReserveDevice

```text
rpc ReserveDevice(ReserveDeviceRequest)
    returns (ReserveDeviceResponse);
```

---

## 8. Input Formats

### 8.1 JobSpec

Canonical format:

```yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: example-job

spec:
  program: |
    @hybrid_program
    def main():
        pass

  target: sim:local
  priority: 50
```

---

### 8.2 Supported Program Sources

| **Source Type** | **Status** |
|---|---|
| Eigen-Lang source | Implemented |
| OpenQASM 3 source | Planned/partial |
| AQO reference | Implemented internally |

---

## 9. Output Formats

### 9.1 Job Results

Result payloads MUST support:

```json
{
  "counts": {
    "00": 512,
    "11": 512
  },
  "metadata": {
    "shots": "1024"
  }
}
```

---

### 9.2 Device Status

Mandatory statuses:

- ONLINE
- OFFLINE
- CALIBRATING
- MAINTENANCE

---

## 10. Client State Management

### 10.1 Current State

Implemented:

- gRPC channel lifecycle,
- server-side authoritative job states.

Not implemented:

- unified SDK state manager,
- distributed cache layer,
- persistent local job registry.

---

### 10.2 Planned Cache Architecture

Target architecture:

| **Level** | **Purpose** |
|---|---|
| L1 | In-memory TTL cache |
| L2 | Redis distributed cache |
| L3 | Persistent disk cache |

This architecture is not yet implemented.

---

## 11. Failure Handling

### 11.1 Retry Policy

Target SDK behavior:

- exponential backoff,
- retry budget limits,
- retryable gRPC status handling,
- timeout propagation.

Example policy:

```Python
max_retries = 3
initial_delay = 0.1
max_delay = 10.0
backoff_factor = 2.0
```

Not yet standardized across released SDKs.

---

### 11.2 Circuit Breaker

Planned states:

- CLOSED,
- OPEN,
- HALF_OPEN.

Not yet implemented in released SDK packages.

---

### 11.3 Transport Fallback

Planned behavior:

- fallback from gRPC to REST,
- degraded-mode operation.

Not implemented.

---

## 12. Observability

### 12.1 Metrics

Planned SDK metrics namespace:

```text
eigen_sdk_requests_total
eigen_sdk_request_duration_seconds
eigen_sdk_retries_total
eigen_sdk_cache_hits_total
```

Current status:

- service-side metrics exist,
- SDK metric packages are not yet released.

---

### 12.2 Logging

Mandatory structured fields:

| **Field** | **Required** |
|---|---|
| timestamp | Yes |
| level | Yes |
| trace_id | Yes |
| span_id | Yes |
| job_id | Optional |
| device_id | Optional |
| message | Yes |

---

### 12.3 Tracing

Implemented:

- OpenTelemetry-compatible tracing,
- trace propagation through services.

Planned:

- SDK instrumentation packages,
- semantic span conventions.

---

## 13. Security

### 13.1 Mandatory Security Requirements

SDKs MUST support:

- TLS transport,
- authenticated requests,
- secure credential handling,
- request validation,
- payload size limits.

---

### 13.2 Planned Credential Features

Not yet implemented:

- encrypted credential vault,
- OS keychain integration,
- automatic token refresh manager.

---

## 14. Integration Targets

### 14.1 Planned Framework Integrations

Target integrations:

- Qiskit,
- PyTorch,
- Jupyter,
- VS Code,
- CI/CD tooling.

These integrations are architectural targets and are not currently delivered as maintained SDK adapters.

---

## 15. Testing Requirements

SDK implementations MUST include:

| **Test Type** | **Required** |
|---|---|
| Unit tests | Yes |
| Integration tests | Yes |
| Contract tests | Yes |
| Security tests | Yes |
| Performance tests | Yes |

---

## 16. Configuration

### 16.1 Configuration Sources

Order of precedence:

1. CLI arguments
2. Environment variables
3. Config file
4. Built-in defaults

---

### 16.2 Standard Environment Variables

```text
EIGEN_ENDPOINT
EIGEN_TOKEN
EIGEN_TIMEOUT
EIGEN_LOG_LEVEL
```

---

## 17. Compatibility Policy

### 17.1 Semantic Versioning

SDKs MUST follow semantic versioning.

| **Version Type** | **Compatibility** |
|---|---|
| Major | Breaking changes allowed |
| Minor | Backward compatible |
| Patch | Bug fixes only |

---

### 17.2 Minimum Supported Platform

| **Component** | **Minimum** |
|---|---|
| Eigen OS | v0.1 |
| Python | 3.12+ |
| Rust | 1.92+ |

---

## 18. Performance Targets

### 18.1 MVP Targets

| **Metric** | **Target** |
|---|---|
| Submission latency | <100 ms |
| Result retrieval | <50 ms |
| Concurrent connections | 10–100 |
| Baseline memory usage | <50 MB |

These are target engineering requirements, not guaranteed achieved benchmarks.

---

## 19. Architectural Constraints

The SDK layer MUST obey the following invariants.

### 19.1 No User Code Execution

SDKs MUST NOT execute arbitrary user code received from remote services.

---

### 19.2 Transport Isolation

Transport implementations MUST remain replaceable without changing public SDK semantics.

---

### 19.3 API Compatibility

SDKs MUST remain compatible with declared Eigen OS API versions.

---

### 19.4 Observability Consistency

All SDK-generated telemetry MUST propagate:

- trace_id,
- request correlation context,
- service boundaries.

---

## 20. Current Repository Status Summary

### Implemented

- gRPC public APIs,
- protobuf contracts,
- JobService,
- DeviceService,
- streaming updates,
- service-side validation,
- tracing infrastructure,
- structured observability,
- contract-based architecture,
- integration/e2e test coverage.

---

### Partially Implemented

- authentication abstraction,
- OpenQASM support,
- CLI tooling,
- observability standardization.

---

### Planned

- official SDK packages,
- REST transport,
- WebSocket transport,
- retry/circuit breaker libraries,
- IDE integrations,
- cache layers,
- framework adapters,
- credential vault integration,
- compatibility negotiation layer.

---

## 21. Conclusion

The Eigen OS Client SDK architecture defines a unified, transport-oriented, contract-driven client layer for interacting with distributed hybrid quantum-classical infrastructure.

The current implementation already provides:

- stable gRPC contracts,
- production-oriented service interfaces,
- deterministic validation boundaries,
- structured observability,
- integration-grade APIs.

The remaining roadmap primarily concerns:

- SDK productization,
- multi-language packaging,
- transport expansion,
- developer ergonomics,
- advanced reliability tooling.

This document is the authoritative specification for SDK behavior, integration contracts, and implementation boundaries.
