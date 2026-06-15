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



#### GetPattern semantics

`GetPattern` returns a canonical template, not just a similar historical object.

Required request semantics:

- `tenant_id` and `project_id` MUST be present.
- capability boundary metadata (`capability_scope`, `capability_tags`, `capabilities`, or equivalent backend capability discriminator) MUST normalize deterministically.
- `snapshot_id`, `circuit_id`, and `backend_class` MUST be present.
- `schema_version`, `compiler_version`, `aqo_version`, `optimizer_version`, `policy_mode`, and `policy_digest` MUST be present.
- compatibility metadata MUST be machine-verifiable by exact string equality.
- incompatible patterns MUST remain visible only as candidates or diagnostics, never as the canonical result.
- diagnostics, replay envelopes, and explanation payloads MUST remain scoped to the current tenant/project and MUST NOT echo foreign identifiers or payload fragments.

Canonical selection semantics:

- exact compatibility is the canonical eligibility gate,
- among compatible candidates the canonical template is selected by `support` desc, `pattern_family` asc, then `pattern_id` asc,
- canonical selection is independent from similarity scoring,
- `GetPattern` MUST return a fallback/diagnostics envelope when no canonical template is found.

Incompatibility reason codes:

- `SCHEMA_MISMATCH`
- `COMPILER_MISMATCH`
- `AQO_MISMATCH`
- `OPTIMIZER_MISMATCH`
- `POLICY_MISMATCH`

Returned responses MUST expose:

- `tenant_id`
- `project_id`
- `candidate_budget`
- `canonical_pattern_id`
- `canonical_pattern`
- `candidate_patterns`
- `explanation_pattern`
- `diagnostics`

The canonical pattern MUST be distinct from the candidate pattern list and MUST not be recomputed from an arbitrary nearest neighbor.

---

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

#### SearchSimilar semantics

`SearchSimilar` is a deterministic scoped similarity query.

Required request semantics:

- `tenant_id` and `project_id` MUST be present.
- `query_mode` MUST be one of `structural`, `vector`, or `hybrid`.
- `candidate_budget` MUST be clamped to the service maximum of `8`.
- `deterministic=true` MUST replay to the same ordered results.

Ranking semantics:

- `structural`: final rank uses the structural score.
- `vector`: final rank uses the vector score.
- `hybrid`: final rank uses the combined score.
- tie-breakers: `confidence` desc, then `candidate_id` asc.

Scope semantics:

- candidates MUST be filtered by tenant/project before scoring,
- candidates MUST also be filtered by capability boundary before scoring,
- capability metadata MUST be honored when present and must fail closed on mismatch,
- diagnostics, selection digests, and replay outputs MUST not expose third-party identifiers or payload fragments.

Returned responses MUST expose:

- `tenant_id`
- `project_id`
- `candidate_budget`
- `selected_candidate_id`
- `okb_selection_digest`
- `index_status`
- `capability_scope`

The `index_status` diagnostic envelope SHOULD report:

- overall status,
- per-index status,
- source fingerprint,
- desync detection,
- recovery timestamps.

---

## 5.1.1 KB index lifecycle

The KB storage layer uses the primary store as the source of truth and maintains structural/vector derived indexes as deterministic replicas.

Required behavior:

- derived indexes MUST be built in deterministic order: structural first, then vector,
- rebuild and backfill operations MUST be idempotent,
- cold-start recovery MUST rebuild from the primary store,
- partial failure MUST mark the affected scope `degraded`,
- `ready`, `rebuilding`, `degraded`, and `unavailable` are the canonical status values.

Operational flow:

1. inspect `index_status`,
2. recover or rebuild the scope from the primary store when needed,
3. backfill historical records after outage recovery,
4. resume similarity queries only when the scope reports `ready`.

---

### 5.2 NeuroSymbolicService

#### Purpose

Internal-only DPDA model service used for advisory scoring of compilation plans.

This service is callable only by authenticated internal service identities. Public ingress paths MUST NOT expose a direct route to this service.

#### Security and versioning requirements

- All requests MUST include an authenticated internal service identity.
- Transport MUST use mTLS in deployment; service identity tokens MAY be used as the request-level assertion.
- Each request MUST include a SemVer contract envelope.
- Requests without a valid internal identity MUST fail closed with `UNAUTHENTICATED`.
- Unsupported contract versions MUST be rejected before model scoring.

#### Service definition

```text
service NeuroSymbolicService {
    rpc ScoreCompilationPlan(ScoreCompilationPlanRequest)
        returns (ScoreCompilationPlanResponse);
}
```

#### Request/response envelope contract

- `ScoreCompilationPlanRequest.envelope.contract_version` is required.
- `ScoreCompilationPlanRequest.context.feature_schema_version` is required.
- `ScoreCompilationPlanRequest.context.policy_snapshot_version` is required.
- The active policy snapshot MUST be frozen at service start and treated as immutable for the lifetime of the service process.
- `ScoreCompilationPlanRequest.context.policy_snapshot_version` MUST match the active immutable snapshot version or the request MUST fail closed before scoring.
- The service MUST run a mandatory feature-extraction redaction pass before scoring.
- The service MUST minimize the inference payload before scoring by deleting raw payloads, full request bodies, unnecessary metadata, stack traces, and large trace dumps.
- The redaction pass MUST delete bearer tokens, API keys, tenant-private secrets, credentials, session cookies, raw auth headers, internal endpoints, and secret-bearing paths.
- The redaction pass MUST mask email addresses, phone numbers, and internal identifiers.
- The minimized/redacted feature vector, not the raw payload, MUST be used for model scoring and replay digests.
- The post-minimization feature payload MUST be bounded by policy, and oversized requests MUST fail closed with `RESOURCE_EXHAUSTED`.
- Every edited field path MUST be emitted in audit/log metadata as redacted-only evidence.
- `ScoreCompilationPlanRequest.context.tenant_id` is required.
- `ScoreCompilationPlanRequest.context.project_id` is required.
- Internal request metadata MUST also carry `x-eigen-tenant-id` and `x-eigen-project-id`, and those values MUST match the request context bound for scoring.
- `ScoreCompilationPlanRequest.context.subject_id` is required.
- `ScoreCompilationPlanRequest.context.workload_id` is required.
- `ScoreCompilationPlanRequest.context.authz_decision_id` is required.
- `x-eigen-tenant-id` and `x-eigen-project-id` gRPC metadata keys are required and MUST match the request context exactly.
- Any tenant/project mismatch MUST fail closed with `PERMISSION_DENIED` before model scoring.
- The normalized security context MUST be fully traceable in audit events and replay digests.
- Raw bearer tokens and header values MUST be sanitized before normalization; only bounded, secret-free security context metadata may be forwarded into inference.
- `ScoreCompilationPlanResponse.contract_version` MUST echo the accepted request contract version.
- `ScoreCompilationPlanResponse.policy_snapshot_version` MUST echo the active immutable snapshot version used for scoring.
- Responses SHOULD echo the normalized security context fields for bounded auditability.
- Responses MUST remain bounded and MUST NOT return raw secrets, bearer tokens, or unredacted payload fragments.

#### Determinism requirements

- The service MUST be deterministic for the same feature vector, contract version, active policy snapshot version, and deterministic seed.
- The response MUST include a replay digest and a bounded confidence value.
- The service output is advisory only and MUST NOT directly change security-relevant decisions.

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

---

## Appendix A. Diagrams

### A.1 Architectural Alignment with Eigen OS

![Architectural Alignment with Eigen OS](https://i.imgur.com/UASV5gf.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Ingress[Ingress]
    SA["System API<br/>(public boundary)"] --> KG[KernelGatewayService]
  end

  subgraph Orchestration[Orchestration]
    KG --> QRTX[QRTX Orchestrator]
  end

  subgraph RuntimeServices[Runtime Services]
    QRTX --> COMP[CompilationService]
    QRTX --> OPT[OptimizerService]
    QRTX --> DM[DriverManagerService]
    QRTX --> QFS[QFSService]
    QRTX --> KB[KnowledgeBaseService]
  end

  subgraph Hardware[Backend Boundary]
    DM --> QDR[QDriver gRPC]
    QDR --> BK["Backend / Provider"]
  end

  subgraph CrossCutting[Cross-cutting]
    SEC["Security Module<br/>(mTLS + identity + policy)"] --- Ingress
    OBS["Observability<br/>(OTel traces/metrics/logs)"] --- Orchestration
    OBS --- RuntimeServices
  end
	style CrossCutting fill:#FFFFFF
```

</details>

---

### A.2 Transport Requirements

![Transport Requirements](https://i.imgur.com/34laUka.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant A as Service A (caller)
  participant B as Service B (callee)
  participant CA as mTLS / CA
  participant OTel as OTel Collector

  A->>CA: mTLS handshake (client cert + server cert validation)
  CA-->>A: session established
  A->>B: gRPC over HTTP/2\nmetadata: traceparent, authorization,\nx-eigen-tenant-id, x-eigen-request-id,\nx-eigen-service-id, x-eigen-user-id
  B-->>A: gRPC response\n(status + details)
  A->>OTel: export spans/metrics/logs (bounded labels)
  B->>OTel: export spans/metrics/logs (bounded labels)
```

</details>

---

### A.3 Core Services

![Core Services](https://i.imgur.com/0mebOJO.png)

<details>
<summary>code</summary>

```text
flowchart TB
  KG[KernelGatewayService] -->|orchestrates| COMP[CompilationService]
  KG -->|orchestrates| OPT[OptimizerService]
  KG -->|orchestrates| DM[DriverManagerService]
  KG -->|persists| QFS[QFSService]
  KG -->|learn/ingest| KB[KnowledgeBaseService]

  DM -->|exec| QDR[QDriver]
  QDR --> BK[Backend]

  %% side channels
  COMP -. compiler trace refs .-> QFS
  OPT -. placement/routing artifacts .-> QFS
  DM -. execution telemetry refs .-> QFS
  KG -. decision/explain artifacts .-> QFS
  KG -. records/feedback .-> KB
```

</details>

---

### A.4 KernelGatewayService

![KernelGatewayService](https://i.imgur.com/2fN7UmR.png)

<details>
<summary>code</summary>

```text
stateDiagram-v2
  [*] --> PENDING
  PENDING --> COMPILING
  COMPILING --> QUEUED
  QUEUED --> RUNNING
  RUNNING --> DONE
  RUNNING --> ERROR
  QUEUED --> CANCELLED
  RUNNING --> CANCELLED
  COMPILING --> CANCELLED
  PENDING --> CANCELLED

  %% timeout is a reason, not a public state
  RUNNING --> ERROR: deadline_exceeded
```

</details>

---

### A.5 PollJobUpdates

![PollJobUpdates](https://i.imgur.com/DatbBWG.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant Client as Internal Client
  participant KG as KernelGatewayService
  participant QRTX as QRTX

  Client->>KG: PollJobUpdates(job_id) (stream)
  KG->>QRTX: Subscribe(job_id)
  loop stream events
    QRTX-->>KG: JobUpdateEvent(state/progress/refs)
    KG-->>Client: JobUpdateEvent
  end
  Note over Client,KG: Heartbeats MUST be emitted under idle periods
  Client->>KG: Cancel stream / deadline exceeded
  KG->>QRTX: Cancel subscription + propagate cancellation
```

</details>

---

### A.6 CompilationService

![CompilationService](https://i.imgur.com/k8SuINm.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant QRTX
  participant COMP as CompilationService
  participant QFS as QFSService

  QRTX->>COMP: CompileJob / CompileCircuit\n(seed, policy_digest, traceparent)
  COMP-->>QRTX: AQO + diagnostics + compiler_trace_ref
  QRTX->>QFS: StoreArtifact(compiled/a qo + diagnostics + trace)
  QFS-->>QRTX: artifact refs + digests
```

</details>

---

### A.7 DriverManagerService

![DriverManagerService](https://i.imgur.com/c42q1X6.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant QRTX
  participant DM as DriverManagerService
  participant QDR as QDriver
  participant BK as Backend
  participant QFS as QFSService

  QRTX->>DM: ExecuteCircuitAsync(payload or qfs_ref)
  DM-->>QRTX: ExecutionHandle(handle_id)
  QRTX->>DM: StreamExecutionUpdates(handle_id) (stream)
  DM->>QDR: Execute(handle_id, translated payload)
  QDR->>BK: Provider execute
  loop updates
    BK-->>QDR: queue/executing/done/error
    QDR-->>DM: ExecutionEvent(...)
    DM-->>QRTX: ExecutionEvent(...)
  end
  QRTX->>QFS: StoreArtifact(results / error / telemetry snapshots)
```

</details>

---

### A.8 OptimizerService

![OptimizerService](https://i.imgur.com/2e7xiEa.png)

<details>
<summary>code</summary>

```text
flowchart TD
  A[OptimizeCircuitRequest] --> B["Feature extraction<br/>AQO graph + topology + calibration"]
  B --> C["GNN inference (seeded if deterministic)"]
  C --> D{"confidence >= threshold<br/>and policy allows?"}
  D -->|yes| E[Generate placement/routing plan]
  D -->|no| F[Deterministic fallback chain]
  E --> V[Symbolic/structural validation]
  F --> V
  V -->|pass| OUT["OptimizeCircuitResponse<br/>optimized_circuit + plans + digest"]
  V -->|fail| ERR["INVALID_ARGUMENT / FAILED_PRECONDITION<br/>+ EIGEN_OPT_* reason"]
```

</details>

---

### A.9 QFSService

![QFSService](https://i.imgur.com/87glRWf.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant S as Any Service
  participant QFS as QFSService

  S->>QFS: StoreArtifact(ref_path, bytes, content_type, schema_version)
  QFS-->>S: ArtifactHandle(ref, digest, size_bytes, created_at, producer)
  S->>QFS: GetArtifact(ref)
  QFS-->>S: bytes + handle
  S->>QFS: ListArtifacts(prefix)
  QFS-->>S: refs[] + handles[]
  S->>QFS: CheckpointState / RestoreState (Phase-1)
  QFS-->>S: checkpoint_ref / restored_ref
```

</details>

---

### A.10 Common Types

![Common Types](https://i.imgur.com/G5z5z6b.png)

<details>
<summary>code</summary>

```text
classDiagram
  class CircuitPayload {
    +format: enum
    +payload_bytes: bytes?
    +qfs_ref: string?
    +shots: int
    +options: map<string,string>
  }

  class AQOPayload {
    +version: string
    +canonical_bytes: bytes
    +digest: string
  }

  class TopologyGraph {
    +nodes: int
    +edges: int
    +snapshot_digest: string
  }

  class ArtifactHandle {
    +ref: string
    +digest: string
    +size_bytes: int
    +content_type: string
    +producer: string
    +schema_version: string
  }

  CircuitPayload --> AQOPayload : may_wrap
  AQOPayload --> TopologyGraph : optimized_against
  CircuitPayload --> ArtifactHandle : may_reference
```

</details>

---

### A.11 Error Model

![Error Model](https://i.imgur.com/zIn43vi.png)

<details>
<summary>code</summary>

```text
flowchart LR
  A[gRPC Status] --> B[google.rpc.ErrorInfo<br/>reason=EIGEN_*]
  A --> C[google.rpc.BadRequest<br/>field violations]
  A --> D[google.rpc.ResourceInfo<br/>resource context]
  A --> E[google.rpc.RetryInfo<br/>retry delay]
  A --> F["google.rpc.DebugInfo<br/>(internal only)"]
  B --> Z[Client/Caller handling]
  C --> Z
  D --> Z
  E --> Z
  F --> Z
```

</details>

---

### A.12 Determinism Requirements

![Determinism Requirements](https://i.imgur.com/WoW7lC0.png)

<details>
<summary>code</summary>

```text
flowchart TB
  subgraph CanonInputs[Canonical deterministic inputs]
    I1[contract_version]
    I2[canonical request bytes]
    I3[topology_snapshot_digest]
    I4["calibration_snapshot_digest (or sentinel)"]
    I5["policy_envelope_digest"]
    I6["seed (required if deterministic=true)"]
    I7["model_version / fallback marker"]
  end

  CanonInputs --> H["sha256(canonical_inputs)"]
  H --> DEC[Deterministic decision output]
  DEC --> OUT[Canonical outputs]
  OUT --> DIG["replay_digest = sha256(inputs + outputs)"]
  DIG --> QFS["Persist replay bundle + digest refs (QFS)"]
	style CanonInputs fill:#FFFFFF
```

</details>

---

### A.13 Observability Requirements

![Observability Requirements](https://i.imgur.com/WSf8Xwf.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant Caller
  participant Callee
  participant OTel as OTel Collector

  Caller->>Callee: RPC (traceparent + bounded metadata)
  Caller->>OTel: span.client (rpc.service, rpc.method, grpc.status_code)
  Callee->>OTel: span.server (rpc.service, rpc.method, grpc.status_code)
  Callee->>OTel: metrics grpc_requests_total{rpc,code}
  Callee->>OTel: metrics grpc_latency_ms_bucket{rpc}
  Callee->>OTel: logs {trace_id, request_id, service_id, rpc_name, result_code}
  Note over Caller,Callee: job_id/tenant/user belong in traces/logs only (NOT metric labels)
```

</details>

---

### A.14 Security Requirements

![Security Requirements](https://i.imgur.com/1w8lmPc.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Identity["mTLS + Service Identity"]
    A["Caller cert / SPIFFE ID"] --> MTLS[mTLS]
    MTLS --> B[Callee verifies identity]
  end

  B --> AuthZ["Policy decision (RBAC/ABAC)"]
  AuthZ -->|allow| Exec[Execute RPC]
  AuthZ -->|deny| Deny["PERMISSION_DENIED + ErrorInfo.reason"]

  Exec --> Audit[Emit audit event]
  Audit --> OBS[Observability stack]
  Exec --> Redact[Redaction rules]
  Redact --> Logs["Structured logs (no secrets)"]
```

</details>
