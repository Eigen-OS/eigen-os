# Contract Map

**Document status:** Normative architecture contract (Source of Truth)
**Scope:** Eigen OS 1.3.0 (Kernel & Data Fabric Detailing) — MVP → Phase runtime baseline
**Contract type:** End-to-end system interface map (APIs, IR formats, storage, observability, security)

---

## 1. Purpose

This document defines the canonical end-to-end contract topology of Eigen OS:

```text
User → SDK/CLI → System API (gRPC/REST)
→ Kernel (QRTX)
→ Compiler (Eigen-DPDA) → Optimizer (GNN) → Driver Manager → QDriver → Backend
→ QFS (L3 CircuitFS, L2 State Store, L1 Live Qubit Manager)
→ Knowledge Base + Observability (OTel → Prometheus/Loki/ES/Jaeger)
→ User
```

It serves as:

- the authoritative architectural interface map,
- the canonical boundary definition between services,
- the normative source for interaction semantics across runtime/compile/execute/data,
- the compatibility baseline for Eigen OS 1.x evolution.

**Normative rule:** Wire contracts, schemas, and stability guarantees live in `docs/reference/`. Component “explanation” docs must not redefine wire-level contracts.

---

## 2. System Architecture Boundaries

### 2.1 External Client Layer

#### Components

- `eigen-cli`
- SDKs
- automation/integration clients

#### Responsibilities

- construct workloads (JobSpec / SDK objects),
- package artifacts deterministically,
- propagate tracing and auth metadata,
- observe job lifecycle/results,
- use public APIs only.

#### Public contract namespace

- gRPC: `eigen.api.v1`
- REST: `/v1/*` (REST mirrors public semantics; see `docs/reference/api/rest-public.md`)

---

### 2.2 Public Gateway Layer (System API)

#### Component

- System API (single public ingress)

#### Responsibilities

- public gRPC/REST exposure,
- authentication/authorization (OAuth2/JWT),
- request validation + normalization,
- idempotency handling (where applicable),
- lifecycle/status/results serving,
- trace propagation (W3C TraceContext),
- delegation to kernel orchestration.

#### Security contract (normative)

- External clients: **JWT/OAuth2**
- All public endpoints: TLS 1.3
- Required scopes/roles per method (see `docs/reference/security/authz.md`)

---

### 2.3 Kernel Orchestration Layer (Eigen Kernel / QRTX)

#### Component

- QRTX (Rust)

#### Responsibilities

- job lifecycle orchestration and state machine,
- DAG construction and dependency execution,
- compiler coordination (DPDA),
- optimizer coordination (GNN),
- execution coordination (Driver Manager / QDriver),
- QFS integration (L1/L2/L3),
- queueing/fairness/priority,
- deadline and retry governance (idempotent-safe),
- audit and telemetry emission.

#### Internal contract namespace

- gRPC: `eigen.internal.v1`

---

### 2.4 Compilation & Optimization Layer

#### Components

- **Eigen-DPDA** (neuro-symbolic compiler): Eigen-Lang → AQO
- **GNN Optimizer** (placement/routing): AQO + topology → QASM (or backend-native)

#### Responsibilities

- deterministic compilation,
- schema validation (Eigen-Lang allowlist; AQO invariants),
- optimization trace emission,
- artifact production + persistence via QFS-L3.

#### Normative formats

- Eigen-Lang spec
- AQO format spec
- QASM export rules (when present)

---

### 2.5 Execution Layer

#### Components

- Driver Manager (sessioning, pooling, capability registry)
- QDriver services (device/simulator specific)

#### Responsibilities

- device discovery, status, capabilities,
- dispatch execution requests,
- normalize results and errors,
- enforce driver isolation (container/process sandbox),
- secrets access via Security Module only,
- emit device/runtime telemetry.

#### Normative driver interface

- QDriver API (gRPC), including:
  - `Initialize`
  - `Execute`
  - `GetStatus`
  - `Calibrate`
  - `Cancel`

---

### 2.6 Backend Layer

#### Components

- simulators (local/cluster)
- vendor simulators
- cloud providers
- physical quantum hardware

#### Notes

- Vendor APIs are not public contracts.
- All provider interaction is normalized through Driver Manager/QDriver.

---

### 2.7 Data & Artifact Layer (QFS)

#### Components

- **QFS Level 3 — CircuitFS:** long-term artifact store (S3/MinIO + metadata DB)
- **QFS Level 2 — Quantum State Store:** checkpoint/restore (HDF5 + SQLite)
- **QFS Level 1 — Live Qubit Manager (LQM):** live qubit allocation + feed-forward

#### Responsibilities

- durable artifact persistence,
- deterministic lineage and provenance,
- checkpoint/restore for eligible modes,
- qubit reservation/isolation guarantees,
- retention policy enforcement.

---

### 2.8 Knowledge & Learning Layer (Knowledge Base + Dataset Pipeline)

#### Components

- Knowledge Base (records, patterns, indices)
- Dataset Pipeline Service (load/validate/convert/register datasets)
- Continuous Learning Pipeline (triggered retraining)

#### Responsibilities

- store circuit/task records and traces,
- similarity search (vector index),
- structural queries (metrics filtering),
- training dataset assembly and governance.

---

### 2.9 Observability Layer

#### Components

- OpenTelemetry instrumentation in all services
- Prometheus (metrics), Grafana (dashboards)
- Loki/Elasticsearch (logs), Jaeger (tracing)
- Alertmanager (alerts)

#### Responsibilities

- metric naming/label boundedness,
- trace continuity across hops,
- audit/security event streams,
- SRE contracts and conformance testing.

---

## 3. Canonical API Namespaces and Surfaces

### 3.1 Public APIs (User-facing)

Canonical namespace:

```text
eigen.api.v1
```

#### Public services (gRPC):

- `JobService`
- `DeviceService`
- `KnowledgeBaseService`

#### Public REST surface (mirrors core functionality):

- `/v1/jobs/*`
- `/v1/devices/*`
- `/v1/benchmarks/*`
- `/v1/explain/*`

**Normative:** gRPC is the primary contract; REST must remain semantically equivalent.

---

### 3.2 Internal APIs (Service-to-service)

Canonical namespace:

```text
eigen.internal.v1
```

Internal services:

- `KernelGatewayService` (System API ↔ QRTX)
- `CompilationService` (QRTX ↔ DPDA compiler service)
- `OptimizerService` (QRTX ↔ GNN optimizer service)
- `DriverManagerService` (QRTX ↔ Driver Manager)
- `StorageService` (QRTX ↔ QFS-L3/L2 service interfaces where applicable)
- `SecurityService` (policy decisions, secrets issuance, audit hooks — if separated)

---

### 3.3 Hardware Abstraction (Device-facing)

QDriver API (gRPC; versioned):

- Device sessioning and execution
- Status/telemetry retrieval
- Calibration
- Cancellation

---

## 4. Versioning and Compatibility

### 4.1 Public API Compatibility (gRPC/REST)

Public APIs are stable contracts.

#### Breaking changes require:

- MAJOR version (e.g., `eigen.api.v2` or `/v2/`)
- coexistence/migration period
- explicit migration documentation

#### Breaking changes include:

- renaming package/service/method/path,
- removing fields or changing requiredness,
- incompatible enum/state changes,
- semantic changes that alter meaning.

#### Non-breaking changes (MINOR) may include:

- adding optional fields,
- adding new RPCs/endpoints,
- adding bounded-cardinality labels,
- adding new result artifact types (without breaking existing retrieval).

---

### 4.2 Internal Contract Compatibility

Internal APIs follow SemVer discipline and must remain synchronized with runtime orchestration semantics. Internal changes must not break running mixed-version deployments unless explicitly allowed by a rolling-upgrade policy document.

---

### 4.3 Job Specification Versioning

#### Current JobSpec contract (Eigen OS 1.x)

```yaml
apiVersion: eigen.os/v1
kind: QuantumJob
```

Canonical descriptor: `job.yaml`

> **Fix applied:** prior `eigen.os/v0.1` reference is invalid for Eigen OS 1.x baseline and conflicts with the JobSpec contract.

---

### Format Versioning (AQO, QFS layouts)

- AQO: versioned format contract (e.g., `AQO v1.0`)
- QFS layouts: versioned storage contracts (e.g., CircuitFS layout v1.0)
- Any breaking format change requires MAJOR bump + migration plan.

---

## 5. End-to-End Execution Flows

### 5.1 Submit Flow

```text
Client
→ (SubmitJob / POST /v1/jobs)
→ System API
→ QRTX
→ persist JobSpec + input artifacts (QFS-L3)
→ initial lifecycle state emitted
```

#### Submit guarantees

- request validation occurs before enqueue,
- accepted jobs receive a stable `job_id`,
- trace context is propagated,
- auth context is propagated,
- orchestration state is persisted.

#### Idempotency

- Public submission MUST support idempotency via either:
  - explicit `idempotency_key` field (preferred when defined), or
  -  a standardized request header/metadata key (e.g., `x-eigen-idempotency-key`).
- Idempotency semantics MUST be documented per endpoint.

--- 

### 5.2 Compilation Flow (Eigen-Lang → AQO)

```text
QRTX
→ CompilationService (Eigen-DPDA)
→ AQO (+ compiler trace, metadata)
→ persist compiled artifacts (QFS-L3)
→ lifecycle update
```

#### Generated artifacts include:

- `compiled/circuit.aqo.json` (required for Eigen-Lang jobs),
- optional `compiled/circuit.aqo.pb`,
- compiler metadata + trace references,
- validation diagnostics when relevant.

---

### 5.3 Optimization Flow (AQO → QASM)

```text
QRTX
→ OptimizerService (GNN Optimizer) + topology from Driver Manager
→ QASM (or backend-native lowered form)
→ persist optimization artifacts (QFS-L3)
→ lifecycle update
```

---

### 5.4 Execution Flow

```text
QRTX
→ DriverManagerService
→ QDriver.Execute
→ Backend execution
→ normalized results + telemetry
→ persist results (QFS-L3) + optional checkpoints (QFS-L2)
→ lifecycle update
```

Driver Manager responsibilities:

- backend normalization,
- error normalization,
- deterministic metadata extraction,
- secure credential handling (no secrets in logs/artifacts).

---

### 5.5 Results Flow

```text
Client
→ GetJobResults / GET /v1/jobs/{job_id}/results
→ System API
→ QRTX
→ QFS-L3 retrieval
→ normalized response + artifact refs
```

Large artifacts are returned through QFS references rather than raw embedding.

---

### 5.6 Explainability Flow (Backend selection / dispatch rationale)

```text
Client
→ GetDispatchRationale / POST /v1/explain/backend-selection
→ System API
→ QRTX / Runtime Controller (reads stored decision snapshot)
→ response with deterministic scoring trace
→ observability events emitted
```

Explainability must be linked to:

- `job_id` (preferred),
- or `decision_id` (internal identifier),
and be auditable via QFS/KB references.

---

## 6. Job Lifecycle Contract

### 6.1 Stable Client-Facing States (Public Contract)

Canonical lifecycle:

```text
PENDING
→ COMPILING
→ QUEUED
→ RUNNING
→ DONE | ERROR | CANCELED
```

Notes:

- `TIMEOUT` may exist as an internal reason or error code, but the public terminal state remains `ERROR` with a stable reason code indicating timeout, unless a dedicated `TIMEOUT` public state is explicitly defined in `eigen.api.*`.

---

### 6.2 Runtime Guarantees (State Semantics)

- **PENDING:** accepted and persisted, not yet compiling.
- **COMPILING:** DPDA compilation in progress.
- **QUEUED:** waiting for backend assignment/resources.
- **RUNNING:** executing on backend (or distributed workers).
- **DONE:** completed successfully; results persisted.
- **ERROR:** terminal failure; normalized error and durable error artifacts available.
- **CANCELED:** canceled by user/system; best-effort cancellation details persisted.

---

## 7. Public Contract Surfaces

### 7.1 JobService (gRPC) / Jobs (REST)

Stable operations:

- `SubmitJob` / `POST /v1/jobs`
- `GetJobStatus` / `GET /v1/jobs/{job_id}`
- `CancelJob` / `POST /v1/jobs/{job_id}:cancel`
- `StreamJobUpdates` / (gRPC stream) and REST alternatives if defined
- `GetJobResults` / `GET /v1/jobs/{job_id}/results`
- `GetDispatchRationale` / `GET /v1/jobs/{job_id}/dispatch-rationale` (or equivalent)

#### Cancel semantics

- allowed for `PENDING`, `COMPILING`, `QUEUED`,
- best-effort for `RUNNING`,
- deterministic terminal behavior for `DONE/ERROR/CANCELED`.

---

### 7.2 DeviceService (gRPC) / Devices (REST)

#### Stable operations:

- `ListDevices` / `GET /v1/devices`
- `GetDeviceStatus` / `GET /v1/devices/{device_id}/status`
- `GetDeviceDetails` / `GET /v1/devices/{device_id}`
- `ReserveDevice` / `POST /v1/devices/{device_id}:reserve` (if supported)

Reservation semantics:

- reservation is a scheduler/runtime capacity signal,
- not guaranteed exclusive hardware lock unless explicitly specified.

---

### 7.3 KnowledgeBaseService

Stable operations (as per KB contract):

- `UpsertRecord`
- `BatchUpsertRecords`
- `QueryRecords`
- `GetRecord`

KB access must be authorization-gated; user data must be anonymized/controlled per policy.

---

### 7.4 Benchmarks (REST/gRPC where defined)

Benchmark runs must integrate:

- dataset pipeline,
- QFS persistence,
- observability contract compliance,
- idempotency.

(See benchmark contracts and observability contracts under `docs/reference/`.)

---

## 8. Internal Service Contracts

### 8.1 KernelGatewayService

Responsibilities:

- job enqueue,
- lifecycle queries,
- cancellation propagation,
- results retrieval integration,
- metadata propagation (user/tenant context).

Internal lifecycle semantics must remain compatible with public semantics.

---

### 8.2 CompilationService (Eigen-DPDA)

Stable operations:

- compile program inputs (Eigen-Lang) to AQO
- validate determinism/security constraints
- return artifacts + compiler trace refs

---

### 8.3 OptimizerService (GNN)

Stable operations:

- optimize AQO against device topology → lowered form (e.g., QASM)
- return placement/routing trace + confidence metadata

---

### 8.4 DriverManagerService

Stable operations:

- list devices, status, details,
- execute circuit,
- calibrate device (when supported),
- cancel backend execution (where supported).

---

## 9. QFS Artifact Contract (Normative Integration)

QFS is a multi-level storage model:

- **L3 CircuitFS** (long-term artifacts)
- **L2 Quantum State Store** (checkpoints)
- **L1 Live Qubit Manager** (live qubit allocation/FF)

Canonical job artifact expectations (L3) include:

- input JobSpec and program source,
- compiled AQO,
- optional lowered QASM,
- results (Parquet + metadata),
- logs/traces references,
- error artifacts for failures.

Artifact access must be authorization-gated.

---

## 10. Error Contract (Normative Integration)

Eigen OS uses **gRPC-status-first semantics** (and equivalent REST mapping).

Transport-level failures must not be encoded in RPC bodies via `success=false` wrappers.

Canonical statuses:

- `INVALID_ARGUMENT`
- `FAILED_PRECONDITION`
- `NOT_FOUND`
- `RESOURCE_EXHAUSTED`
- `UNAVAILABLE`
- `DEADLINE_EXCEEDED`
- `UNAUTHENTICATED`
- `PERMISSION_DENIED`
- `UNIMPLEMENTED`
- `INTERNAL`
- `ABORTED`
- `CANCELLED`

Structured details at public boundaries must be encoded as deterministic `google.rpc.Status` details with `google.rpc.ErrorInfo` first. `ErrorInfo.reason` carries the stable `EIGEN_PUBLIC_*` or normalized `EIGEN_BACKEND_*` reason code, and `ErrorInfo.metadata.retryable` carries the public retryability decision. Additional detail types are attached according to the scenario:

- `google.rpc.BadRequest` for validation and payload shape failures
- `google.rpc.QuotaFailure` for payload/quota limits
- `google.rpc.PreconditionFailure` for lifecycle, version, and idempotency conflicts
- `google.rpc.ResourceInfo` for missing or inaccessible resources
- `google.rpc.RetryInfo` for retryable transient failures
- `google.rpc.RequestInfo` for cancellation/internal correlation when available

Backend/provider failures must be normalized before reaching public contracts.

Async failures must remain inspectable via durable artifacts (e.g., `qfs://jobs/<job_id>/results/error.json`).

---

## 11. Security Contract (Normative Integration)

### 11.1 Transport Security

- External: TLS 1.3
- Internal: **mTLS required** between services (Zero Trust baseline)

### 11.2 Authentication / Authorization

- External: OAuth2/JWT
- Internal: mTLS service identity + propagated user/tenant context
- Policy decision point: centralized policy engine (e.g., OPA/Casbin)

### 11.3 Secret Management

- Secrets stored in Vault/KMS-equivalent
- Never in source code, logs, or artifacts
- Driver credentials issued least-privilege and time-bounded

### 11.4 Auditability

- Security/audit events emitted to observability stack
- Immutable audit trail requirements apply to auth, policy, and critical runtime actions

---

## 12. Tracing and Correlation

### 12.1 Trace Propagation

- W3C TraceContext
- required header/metadata: `traceparent`

### 12.2 Correlation Expectations

Where applicable, systems must correlate via:

- `job_id`
- `device_id`
- `decision_id` (for explainability)
- `trace_id` (traces only; not as metric labels)

---

## 13. Timeout and Deadline Semantics

- Public APIs: clients set deadlines/timeouts.
- System API must propagate deadlines downstream.
- Long-running operations must use async orchestration rather than - indefinite blocking RPCs.
- Timeouts must map deterministically into error codes/reasons and durable failure artifacts.

---

## 14. Observability Contract Integration

Eigen OS must comply with:

- orchestration observability contract,
- intelligent runtime observability contract,
- cluster runtime observability contract (if distributed),
- benchmark observability contract.

Bounded cardinality rule:

- no `job_id`, `trace_id`, `request_id`, user identifiers as metric labels.

---

## 15. Interface Matrix

### 15.1 External Layer

| **Caller** | **Callee** | **Contract** | **Purpose** |
|-----------|-----------|-----------|-----------|
| SDK / CLI | System API | `eigen.api.v1` + REST `/v1` | submit/status/results/explain/devices |

---

### 15.2 Orchestration Layer

| **Caller** | **Callee** | **Contract** | **Purpose** |
|-----------|-----------|-----------|-----------|
| System API | QRTX | `eigen.internal.v1` | enqueue/status/cancel/results |
| QRTX | CompilationService | `eigen.internal.v1` | Eigen-Lang → AQO |
| QRTX | OptimizerService | `eigen.internal.v1` | AQO + topology → lowered form |
| QRTX | DriverManagerService | `eigen.internal.v1` | execute/cancel/status |
| QRTX | QFS Services | internal gRPC / storage APIs | artifacts/checkpoints |
| QRTX | Knowledge Base | KB API | ingest/search/patterns |
| All services | Observability stack | OTel | metrics/logs/traces |

---

### 15.3 Hardware Layer

| **Caller** | **Callee** | **Contract** | **Purpose** |
|-----------|-----------|-----------|-----------|
| Driver Manager | QDriver | QDriver gRPC | execute/status/calibrate/cancel |
| QDriver | Vendor backend | vendor-specific | device integration |

---

## 16. CI and Contract Governance Requirements

CI must enforce:

- proto change controls (e.g., `buf lint`, `buf breaking`),
- schema validation tests for formats (AQO, JobSpec, QFS manifests),
- conformance tests for error mapping,
- observability contract tests (metrics presence, label boundedness),
- replay determinism tests where applicable.

Changes affecting:

- APIs,
- formats,
- observability,
- dashboards/alerts,
- must be updated in the same change set.

---

## 17. Production Hardening Targets (1.x Baseline)

Required for a full production-grade freeze:

1. mTLS enabled and enforced across internal hops.
2. OAuth2/JWT scopes and ABAC/RBAC policies fully documented and enforced.
3. Durable QFS-L3 persistence + retention policies.
4. Observability contracts wired end-to-end.
5. Backend error normalization and durable failure artifacts.
6. Deterministic compilation + replay safety for defined modes.
7. Explainability trace linkage: job submission → decision snapshot → explain endpoint.

---

## 18. MVP Success Criterion (End-to-end)

A baseline success path must work deterministically:

```text
eigen-cli submit --job job.yaml
```

followed by:

- validation,
- orchestration,
- compilation (Eigen-Lang → AQO),
- optimization (AQO → lowered),
- execution (Driver Manager → QDriver → backend),
- persistence (QFS-L3),
- observability emission,
- results retrieval.

This path must operate consistently on at least one supported simulator/runtime profile for Eigen OS 1.x.

---

## Appendix A. Diagrams (normative)

### A.1 System contract topology (E2E map)

![System contract topology](https://i.imgur.com/s3pkqQL.png)

<details>
<summary>code</summary>

```text
flowchart TB
  subgraph External["External clients"]
    CLI[eigen-cli]
    SDK[SDKs]
    Auto[Automation clients]
  end

  subgraph Public["Public surface (stable)"]
    API["System API\n(gRPC eigen.api.v1 / REST /v1)"]
  end

  subgraph Internal["Internal runtime (eigen.internal.v1)"]
    K["Kernel / QRTX"]
    C["CompilationService\n(Eigen-DPDA)"]
    O["OptimizerService\n(GNN)"]
    DM["DriverManagerService"]
    Sec["SecurityService\n(policy/secrets/audit)\n(optional split)"]
    QFS["QFS\n(L3 CircuitFS + future L2/L1)"]
    KB["KnowledgeBaseService (public records)\n+ OKB (internal target)"]
  end

  subgraph Hardware["Hardware abstraction"]
    QD["QDriver\n(plugin or remote service)"]
    BE[(Backends / Simulators / Vendor clouds)]
  end

  subgraph Obs["Observability stack"]
    OTel[OpenTelemetry]
    Prom[(Prometheus)]
    Logs[(Loki/ES)]
    Trace[(Jaeger)]
    Graf[(Grafana)]
  end

  CLI --> API
  SDK --> API
  Auto --> API

  API --> K

  K --> C
  K --> O
  K --> DM
  K --> QFS
  K -. "optional" .-> Sec
  C -. "optional" .-> KB
  O -. "optional" .-> KB

  DM --> QD --> BE

  API -. "emits" .-> OTel
  K -. "emits" .-> OTel
  C -. "emits" .-> OTel
  O -. "emits" .-> OTel
  DM -. "emits" .-> OTel
  QFS -. "emits" .-> OTel
  KB -. "emits" .-> OTel

  OTel --> Prom
  OTel --> Logs
  OTel --> Trace
  Prom --> Graf
  Logs --> Graf
  Trace --> Graf

  %% Цвета слоёв
  classDef external fill:#e3f2fd,stroke:#1565c0
  classDef public fill:#fff3e0,stroke:#ef6c00
  classDef internal fill:#e8f5e9,stroke:#2e7d32
  classDef hardware fill:#f3e5f5,stroke:#6a1b9a
  classDef obs fill:#fce4ec,stroke:#c62828

  class CLI,SDK,Auto external
  class API public
  class K,C,O,DM,Sec,QFS,KB internal
  class QD,BE hardware
  class OTel,Prom,Logs,Trace,Graf obs
```

</details>

---

### A.2 Contract namespace map (public vs internal vs device-facing)

![Contract namespace map](https://i.imgur.com/PZIHMEY.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Public["Public contracts (stable)"]
    P1["eigen.api.v1\n(JobService, DeviceService, KnowledgeBaseService)"]
    R1[/"REST /v1/*\n(semantic mirror)"/]
  end

  subgraph Internal["Internal contracts (SemVer, rolling policy)"]
    I1["eigen.internal.v1\n(KernelGatewayService,\nCompilationService,\nOptimizerService,\nDriverManagerService,\nStorage/Security if separated)"]
  end

  subgraph Device["Device-facing contracts (versioned)"]
    D1["QDriver API (gRPC)\nInitialize/Execute/GetStatus/Calibrate/Cancel"]
    V1[("Vendor/provider SDKs/APIs\n(non-contractual)")]
  end

  P1 --> I1
  R1 --> P1
  I1 --> D1
  D1 --> V1
```

</details>

---

### A.3 Sequence: Submit → persist input → compile → optimize → execute → persist results

![Submit → persist input → compile → optimize → execute → persist results](https://i.imgur.com/bguEyhe.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant Client as SDK/CLI
  participant API as System API (eigen.api.v1)
  participant K as Kernel/QRTX (eigen.internal.v1)
  participant Q as QFS (L3)
  participant C as CompilationService (Eigen-DPDA)
  participant O as OptimizerService (GNN)
  participant DM as DriverManagerService
  participant QD as QDriver
  participant BE as Backend/Simulator

  Client->>API: SubmitJob / POST /v1/jobs
  API->>K: EnqueueJob (KernelGatewayService)
  K->>Q: store input/job.yaml + source bundle
  K->>C: CompileJob/CompileCircuit
  C->>Q: write compiled/* (AQO + metadata + diagnostics ref)
  K->>DM: GetDeviceStatus (topology/capabilities snapshot)
  DM-->>K: topology + capability snapshot (bounded)
  K->>O: OptimizeCircuit (AQO + topology + policy + seed)
  O->>Q: write optimizer/* (placement/routing/decision)
  K->>DM: ExecuteCircuit (lowered payload/AQO + device_id)
  DM->>QD: Execute
  QD->>BE: vendor execute
  BE-->>QD: raw results/errors
  QD-->>DM: raw provider response
  DM-->>K: normalized ExecutionResult + canonical errors
  K->>Q: write results/results.json OR results/error.json
  K-->>API: "accepted + job_id, later status/results"
  API-->>Client: GetJobStatus / GetJobResults
```

</details>

---

### A.4 Artifacts lineage flow (what persists where)

![Artifacts lineage flow](https://i.imgur.com/qMymO7K.png)

<details>
<summary>code</summary>

```text
flowchart TB
  subgraph QFSRoot["qfs://jobs/<job_id>/"]
    IN[input/job.yaml\nsource/*]
    COMP[compiled/\ncompiled.aqo.json\nmetadata.json\ndiagnostics.json?]
    OPT[optimizer/\nrequest.json\noptimized_aqo.json\nplacement.json?\nrouting.json?\ndecision.json]
    RES[results/\nresults.json\nerror.json?]
    TL[timeline/timeline.json?]
    LOG[logs/run.log?]
  end

  IN --> COMP
  COMP --> OPT
  OPT --> RES
  IN -. references .-> TL
  COMP -. references .-> TL
  OPT -. references .-> TL
  RES -. references .-> TL
```

</details>

---

### A.5 “No contract drift” rule visualization (contracts live in docs/reference)

![“No contract drift” rule visualization](https://i.imgur.com/vNvsPuj.png)

<details>
<summary>code</summary>

```text
flowchart TB
  Ref["docs/reference/\n(proto, schemas, error model,\nobservability contracts, JobSpec, AQO, QFS layout)"]
  Arch["docs/architecture/\n(contract-map.md, data-flow.md,\narchitecture topology)"]
  Comp["components/*.md\n(explanations)"]

  Arch -->|MUST reference| Ref
  Comp -->|MUST reference| Ref
  Comp -. "MUST NOT redefine" .-> Ref
```

</details>

---

### A.6 Allowed call graph (enforced boundaries)

![Allowed call graph](https://i.imgur.com/OtY9Jgy.png)

<details>
<summary>code</summary>

```text
flowchart LR
  Client[SDK/CLI] --> API[System API]
  API --> K[Kernel/QRTX]

  K --> C[CompilationService]
  K --> O[OptimizerService]
  K --> DM[Driver Manager]
  K --> QFS[QFS]

  DM --> QD[QDriver] --> BE[(Backend)]

  %% hard prohibitions
  API -. MUST NOT .-> BE
  K -. MUST NOT .-> BE
  C -. MUST NOT .-> BE
  O -. MUST NOT .-> BE
```

</details>
