# gRPC Internal API Specification (eigen.internal.v1)

**Version**: 1.0.0  
**Status**: Target Standard  
**Compatibility**: Eigen OS v1.3.0+  
**Primary Transport**: gRPC over HTTP/2  
**Serialization**: Protocol Buffers v3  
**Security Model**: mTLS + Service Identity Tokens  
**Canonical Namespace**: `eigen.internal.v1`

---

## 1. Purpose

This document defines the authoritative internal gRPC contracts used between Eigen OS services.

The gRPC Internal API is the backbone of:
- QRTX orchestration,
- compilation pipelines,
- scheduling,
- driver execution,
- optimizer execution,
- observability propagation,
- Knowledge Base ingestion,
- Continuous Learning workflows,
- storage operations.

This specification supersedes informal implementation behavior and acts as the **source of truth** for all internal service-to-service communication. All implementations **MUST** conform to this document.

---

## 2. Architectural Alignment with Eigen OS

This API layer directly implements the architecture defined in Eigen OS Target Standard v1.3.0.

#### Integrated components:

| **Component**               | **Role** |
|-----------------------------|------|
| System API                  | External ingress |
| QRTX                        | Central orchestration |
| Compilation Service         | Neuro-DPDA compiler |
| Optimizer Service           | GNN routing & placement |
| Driver Manager              | Hardware abstraction |
| QFS                         | Artifact and state persistence |
| Knowledge Base              | Long-term learning memory |
| Security Module             | AuthN/AuthZ and policy |
| Observability Stack         | Tracing, metrics, audit |
| Dataset Pipeline            | Dataset ingestion |
| Continuous Learning Pipeline| Retraining orchestration |

---

## 3. Transport Requirements

#### Protocol

All internal APIs **MUST** use:
```http
gRPC over HTTP/2
```

#### Serialization

All payloads MUST use:

```text
Protocol Buffers v3
```

#### Connection Security

All service-to-service communication MUST use:

- TLS 1.3
- mutual TLS (mTLS)

Unencrypted internal traffic is prohibited.

#### Identity Propagation

Each request MUST propagate:

| **Metadata Key**     | **Purpose** |
|----------------------|------|
| `x-eigen-user-id`    | External ingress |
| `x-eigen-tenant-id`  | Central orchestration |
| `x-eigen-request-id` | Neuro-DPDA compiler |
| `x-eigen-trace-id`   | GNN routing & placement |
| `x-eigen-service-id` | Hardware abstraction |
| `authorization`      | Artifact and state persistence |
| `traceparent`        | Long-term learning memory |

These metadata keys are mandatory unless explicitly exempted.

---

## 4. Canonical Proto Namespace

```text
package eigen.internal.v1;
```

Canonical source location:
```text
proto/eigen/internal/v1/
```

All `.proto` files under this directory are authoritative schema definitions.

---

## 5. Core Services

### 5.1 KernelGatewayService

#### Purpose

Primary orchestration interface into QRTX.

Acts as the internal bridge between:
- System API
- QRTX Scheduler
- Runtime services

#### Service Definition

```text
service KernelGatewayService {
    rpc EnqueueJob(EnqueueJobRequest)
        returns (EnqueueJobResponse);

    rpc GetJobStatus(GetJobStatusRequest)
        returns (GetJobStatusResponse);

    rpc CancelJob(CancelJobRequest)
        returns (CancelJobResponse);

    rpc GetJobResults(GetJobResultsRequest)
        returns (GetJobResultsResponse);

    rpc PollJobUpdates(PollJobUpdatesRequest)
        returns (stream JobUpdateEvent);
}
```

---

#### Required Semantics

#### EnqueueJob

Creates a new execution workflow.

MUST:
- validate authorization,
- assign deterministic `job_id`,
- persist JobSpec,
- enqueue into QRTX.

#### GetJobStatus

Returns lifecycle state.

Canonical states:
```text
PENDING
COMPILING
QUEUED
RUNNING
DONE
ERROR
CANCELLED
TIMEOUT
```

#### CancelJob

MUST:

- propagate cancellation to all downstream services,
- cancel queued/running backend executions,
- release qubit reservations,
- update observability traces.

#### PollJobUpdates

Streaming API for incremental updates.

Replaces polling loops.

MUST support:

- server streaming,
- heartbeat events,
- cancellation propagation,
- deadline handling.

---

### 5.2 CompilationService

#### Purpose

Neuro-symbolic compilation interface.

Transforms:
```text
Eigen-Lang → AST → AQO → Intermediate representations
```

**Service Definition**
```text
service CompilationService {
    rpc CompileCircuit(CompileCircuitRequest)
        returns (CompileCircuitResponse);

    rpc CompileJob(CompileJobRequest)
        returns (CompileJobResponse);

    rpc OptimizeCircuit(OptimizeCircuitRequest)
        returns (OptimizeCircuitResponse);

    rpc ValidateCircuit(ValidateCircuitRequest)
        returns (ValidateCircuitResponse);
}
```

#### CompileCircuit

Compiles a standalone circuit.

Outputs:

- AQO,
- IR,
- diagnostics,
- compiler trace.

#### CompileJob

Compiles a full hybrid workflow.

MUST support:

- multiple circuits,
- classical orchestration,
- dataset references,
- parameter binding.

#### OptimizeCircuit

Previously stubbed.

MUST now be implemented.

Responsibilities:

- AQO optimization,
- gate simplification,
- SWAP reduction,
- noise-aware rewriting,
- topology-aware transformations.

#### ValidateCircuit

Previously stubbed.

MUST now be implemented.

Validation includes:

- AST safety,
- deterministic semantics,
- unsupported gates,
- recursion prevention,
- bounded resources,
- prohibited runtime constructs.

---

### 5.3 DriverManagerService

#### Purpose

Hardware abstraction orchestration layer.

Provides unified access to:

- simulators,
- local hardware,
- cloud quantum devices.

#### Service Definition

```text
service DriverManagerService {
    rpc ListDevices(ListDevicesRequest)
        returns (ListDevicesResponse);

    rpc GetDeviceStatus(GetDeviceStatusRequest)
        returns (GetDeviceStatusResponse);

    rpc ExecuteCircuit(ExecuteCircuitRequest)
        returns (ExecuteCircuitResponse);

    rpc ExecuteCircuitAsync(ExecuteCircuitRequest)
        returns (ExecutionHandle);

    rpc StreamExecutionUpdates(ExecutionHandle)
        returns (stream ExecutionEvent);

    rpc CalibrateDevice(CalibrateDeviceRequest)
        returns (CalibrateDeviceResponse);
}
```

#### ExecuteCircuit

Synchronous unary execution.

Recommended only for short-running jobs.

#### ExecuteCircuitAsync

Required for:

- cloud devices,
- queued systems,
- long-running executions.

Returns execution handle.

#### StreamExecutionUpdates

Streams:

- queue status,
- execution start,
- execution completion,
- telemetry,
- cancellation,
- failure events.

#### CalibrateDevice

Previously stubbed.

MUST now be implemented.

Calibration MAY include:

- T1/T2 refresh,
- gate recalibration,
- readout recalibration,
- topology refresh.

---

### 5.4 OptimizerService

#### Purpose

GNN-based routing and placement optimization.

Transforms:

```text
AQO → topology-aware executable QASM
```

#### Service Definition

```text
service OptimizerService {
    rpc OptimizeCircuit(OptimizeCircuitRequest)
        returns (OptimizeCircuitResponse);
}
```

#### Required Semantics

MUST support:

- deterministic seed replay,
- confidence scoring,
- fallback algorithms,
- topology-aware routing,
- SWAP minimization,
- noise prediction.

#### Required Failure Codes

| **Code** | **Meaning** |
|----------------------|------|
| `OPT_INVALID_AQO` | Invalid intermediate representation |
| `OPT_TIMEOUT` | Optimization exceeded deadline |
| `OPT_NO_FEASIBLE_MAPPING` | No routing solution |
| `OPT_MODEL_FAILURE` | ML model failure |
| `OPT_INTERNAL_ERROR` | Internal optimizer failure |

---

### 5.5 QFSService

#### Purpose

Internal persistence interface for QFS.

Previously undocumented in internal API contracts.

Now mandatory.

#### Service Definition

```text
service QFSService {
    rpc StoreArtifact(StoreArtifactRequest)
        returns (StoreArtifactResponse);

    rpc GetArtifact(GetArtifactRequest)
        returns (GetArtifactResponse);

    rpc ListArtifacts(ListArtifactsRequest)
        returns (ListArtifactsResponse);

    rpc CheckpointState(CheckpointStateRequest)
        returns (CheckpointStateResponse);

    rpc RestoreState(RestoreStateRequest)
        returns (RestoreStateResponse);
}
```

---

### 5.6 KnowledgeBaseService

#### Purpose

Persistent memory and learning interface.

Previously omitted from internal API spec.

Now mandatory.

#### Service Definition

```text
service KnowledgeBaseService {
    rpc SearchSimilar(SearchSimilarRequest)
        returns (SearchSimilarResponse);

    rpc QueryCircuits(QueryCircuitsRequest)
        returns (QueryCircuitsResponse);

    rpc GetPattern(GetPatternRequest)
        returns (GetPatternResponse);

    rpc IngestCircuit(IngestCircuitRequest)
        returns (IngestCircuitResponse);

    rpc IngestBatch(IngestBatchRequest)
        returns (IngestBatchResponse);
}
```

---

## 6. Common Types

Canonical shared types include:

| **Type** | **Purpose** |
|----------------------|------|
| `CircuitPayload` | Circuit representation |
| `AQOPayload` | AQO intermediate representation |
| `DeviceInfo` | Device metadata |
| `DeviceStatus` | Live telemetry |
| `ExecutionMetrics` | Runtime metrics |
| `CompilerTrace` | DPDA trace |
| `TopologyGraph` | Device topology |
| `JobSpec` | Workflow specification |

---

## 7. Error Model

Internal APIs MUST use canonical gRPC status codes.

No:
```text
success = false
```

patterns are permitted.

### 7.1 Canonical gRPC Codes

| **Code** | **Usage** |
|----------------------|------|
| `INVALID_ARGUMENT` | Validation failure |
| `NOT_FOUND` | Missing resource |
| `FAILED_PRECONDITION` | Invalid lifecycle state |
| `RESOURCE_EXHAUSTED` | Quota exhaustion |
| `UNAUTHENTICATED` | Missing auth |
| `PERMISSION_DENIED` | Access denied |
| `UNAVAILABLE` | Temporary outage |
| `DEADLINE_EXCEEDED` | Timeout |
| `UNIMPLEMENTED` | Unsupported RPC |
| `INTERNAL` | Unexpected failure |

---

### 7.2 Retry Semantics

Retry recommendations:

| **Status** | **Retry** |
|----------------------|------|
| `UNAVAILABLE` | yes |
| `DEADLINE_EXCEEDED` | yes |
| `RESOURCE_EXHAUSTED` | backoff |
| `INTERNAL` | conditional |
| `INVALID_ARGUMENT` | never |
| `PERMISSION_DENIED` | never |

Exponential backoff REQUIRED.

---

## 8. Determinism Requirements

All services MUST support deterministic replay where applicable.

Deterministic replay requires:

- fixed seeds,
- version-pinned models,
- topology snapshots,
- compiler trace persistence,
- immutable artifacts.

---

## 9. Observability Requirements

#### OpenTelemetry

All RPCs MUST create spans.

Required attributes:

| **Attribute** | **Description** |
|----------------------|------|
| `rpc.service` | gRPC service |
| `rpc.method` | RPC method |
| `eigen.job_id` | Job ID |
| `eigen.device_id` | Backend |
| `eigen.user_id` | User |
| `eigen.trace_id` | Trace |

#### Metrics

Each RPC MUST expose:

| **Metric** | **Type** |
|----------------------|------|
| `grpc_requests_total` | counter |
| `grpc_failures_total` | counter |
| `grpc_latency_ms` | histogram |

#### Structured Logging

All services MUST emit structured logs.

Required fields:

- `trace_id`,
- `request_id`,
- `service_id`,
- `rpc_name`,
- `latency_ms`,
- `result_code`.

---

## 10. Security Requirements

#### Mutual TLS

Mandatory for ALL internal traffic.

#### Service Identity

Each service MUST authenticate using:

- SPIFFE/SPIRE,
- or signed JWT service identities.

#### Least Privilege

Each service account MUST have minimal scopes.

Example:

| **Service** | **Allowed Actions** |
|----------------------|------|
| Compiler | compile only |
| Optimizer | optimize only |
| Driver Manager | backend execution only |

#### Auditability

All privileged operations MUST be auditable.

---

## 11. Versioning Rules

Proto contracts follow SemVer.

#### Minor Versions

May:

- add optional fields,
- add RPCs,
- extend enums safely.

#### Major Versions

Required for:

- field removal,
- semantic changes,
- required field additions.

---

## 12. CI/CD Requirements

CI MUST enforce:

- Buf breaking-change checks,
- deterministic proto generation,
- linting,
- metadata propagation tests,
- replay fixture validation,
- backward compatibility tests.

---

## 13. Acceptance Criteria

Implementation is compliant only if:

- all RPCs use mTLS,
- metadata propagation is enforced,
- streaming APIs work,
- deterministic replay passes,
- observability instrumentation exists,
- retries follow policy,
- stubs are fully implemented,
- QFS/KB services are exposed,
- proto contracts are CI-protected.

---

## 14. Migration Requirements

The following legacy behaviors MUST be removed:

| Legacy Behavior | Replacement |
|----------------------|------|
| unsecured gRPC | mTLS |
| missing metadata | mandatory propagation |
| unary-only execution | async + streaming |
| unimplemented stubs | fully implemented RPCs |
| implicit auth trust | explicit service identity |

---

## 15. Source of Truth Statement

This document is the authoritative specification for all internal gRPC APIs in Eigen OS.

All implementations:

- Rust,
- Python,
- Go,
- SDKs,
- test harnesses,
- mock servers,

MUST conform to this specification.

If code diverges from this document, the implementation MUST be corrected.
