# Eigen OS — Reference Diagrams Pack

> This document contains **diagrams only** for all `docs/reference/*` contracts found in the provided archive.

## Legend
- Diagrams are authored in **Mermaid**.
- Component names follow contract namespaces: `eigen.api.v1` (public) and `eigen.internal.v1` (internal).

---

## Public API (gRPC) — Contract Topology

_Source:_ `reference/api/grpc-public.md`

![Public API (gRPC)](https://i.imgur.com/qu3XJol.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Client
    SDK[SDK/CLI]
  end
  subgraph Public
    API["System API\n(eigen.api.v1)"]
  end
  subgraph Internal
    K["Kernel Gateway\n(eigen.internal.v1)"]
    C["Compiler Service\n(eigen.internal.v1)"]
    DM["Driver Manager\n(eigen.internal.v1)"]
    QFS["QFS Store\n(QFS L3)"]
  end
  subgraph Backend
    QD[QDriver]
    B[Provider / Simulator / Hardware]
  end

  SDK -->|gRPC: eigen.api.v1| API
  API -->|gRPC: eigen.internal.v1| K
  K --> C
  K --> DM
  K --> QFS
  DM --> QD --> B
```

</details>

### SubmitJob — happy path (async)

![SubmitJob](https://i.imgur.com/hvsTlic.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant SDK as SDK/CLI
  participant API as System API (eigen.api.v1)
  participant K as Kernel (eigen.internal.v1)
  participant QFS as QFS (L3)
  participant C as Compiler Service
  participant DM as Driver Manager
  participant QD as QDriver

  SDK->>API: SubmitJob(JobSpec/program)
  API->>K: EnqueueJob(normalized request)
  K->>QFS: atomic_write input/job.yaml + source/*
  K-->>API: job_id + initial state=PENDING
  API-->>SDK: SubmitJobResponse(job_id)

  Note over K: Async orchestration
  K->>C: CompileJob(source_ref or bytes)
  C-->>K: AQO + metadata + diagnostics?
  K->>QFS: atomic_write compiled/*
  K->>DM: ExecuteCircuit(job_id, device_id, CircuitPayload)
  DM->>QD: Execute(backend-native)
  QD-->>DM: raw result or error
  DM-->>K: normalized ExecutionResult
  K->>QFS: atomic_write results/* (and results.parquet if success)
```

</details>

### GetJobStatus / StreamJobUpdates

![GetJobStatus / StreamJobUpdates](https://i.imgur.com/Cv66CMK.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant SDK as SDK/CLI
  participant API as System API
  participant K as Kernel

  alt polling
    SDK->>API: GetJobStatus(job_id)
    API->>K: GetJobStatus(job_id)
    K-->>API: state + timestamps
    API-->>SDK: state
  else streaming
    SDK->>API: StreamJobUpdates(job_id)
    API->>K: SubscribeToJobUpdates(job_id)  %% kernel-owned stream (target)
    loop events
      K-->>API: JobUpdate(event)
      API-->>SDK: JobUpdate(event)
    end
  end
```

</details>

### GetJobResults — terminal visibility

![GetJobResults — terminal visibility](https://i.imgur.com/EztZT09.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant SDK as SDK/CLI
  participant API as System API
  participant K as Kernel
  participant QFS as QFS

  SDK->>API: GetJobResults(job_id)
  API->>K: GetJobResults(job_id)
  alt DONE
    K->>QFS: get results/results.json + results.parquet ref
    QFS-->>K: artifact refs
    K-->>API: JobResults (refs)
    API-->>SDK: JobResults
  else ERROR
    K->>QFS: get results/error.json
    QFS-->>K: error artifact ref
    K-->>API: error_code + summary + error_details_ref
    API-->>SDK: JobResults (error visibility)
  else non-terminal
    K-->>API: FAILED_PRECONDITION (results not ready)
    API-->>SDK: FAILED_PRECONDITION
  end
```

</details>

---

## Internal APIs (gRPC) — Orchestration Hops

_Source:_ `reference/api/grpc-internal.md`

![Internal APIs (gRPC) — Orchestration Hops](https://i.imgur.com/StM9t23.png)

<details>
<summary>code</summary>

```text
flowchart TB
  API["System API\n(public gateway)"] --> KG["KernelGatewayService\n(eigen.internal.v1)"]
  KG --> CS["CompilationService\n(eigen.internal.v1)"]
  KG --> OS["OptimizerService\n(eigen.internal.v1)"]
  KG --> DMS["DriverManagerService\n(eigen.internal.v1)"]
  KG --> QS[QFS facade / storage]

  DMS --> QD[QDriver gRPC]
  QD --> Vendor[Vendor backend]
```

</details>

### Kernel orchestration — compile → (optimize) → execute

![Kernel orchestration — compile → (optimize) → execute](https://i.imgur.com/FpKDNHA.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant K as Kernel
  participant CS as CompilationService
  participant OS as OptimizerService
  participant DM as DriverManagerService
  participant QFS as QFS

  K->>CS: CompileJob / CompileCircuit
  CS-->>K: AQO + metadata
  K->>QFS: store compiled artifacts

  opt optimizer enabled
    K->>DM: GetDeviceStatus(device_id) (topology/calibration)
    DM-->>K: topology + calibration (bounded)
    K->>OS: OptimizeCircuit(AQO, topology, policy, deterministic+seed)
    OS-->>K: optimized AQO/QASM + plans + digest
    K->>QFS: store optimizer artifacts
  end

  K->>DM: ExecuteCircuit(job_id, device_id, payload)
  DM-->>K: ExecutionResult (normalized)
  K->>QFS: store results + error artifact (if failure)
```

</details>

---

## JobSpec v1.0 — Packaging and Validation

_Source:_ `reference/jobspec.md`

![JobSpec v1.0 — Packaging and Validation](https://i.imgur.com/OUz8DSN.png)

<details>
<summary>code</summary>

```text
flowchart LR
  J[job.yaml] --> P["Packaging\n(path normalization\nline ending normalization\nhashing)"]
  S["Program source\n(path|inline|uri)"] --> P
  P --> R["SubmitJobRequest\n(normalized)"]
  R --> V{Server validation}
  V -->|ok| A[Accepted job_id]
  V -->|INVALID_ARGUMENT| E[BadRequest violations]
```

</details>

### Program source mutual exclusivity

![Program source mutual exclusivity](https://i.imgur.com/TNYXmT1.png)

<details>
<summary>code</summary>

```text
flowchart TB
  Start([program specification])
  Start --> Choice{Exactly one of}
  Choice --> Path[path]
  Choice --> Inline[inline]
  Choice --> URI[uri]
  Choice -->|more than one| Fail[INVALID_ARGUMENT]
```

</details>

### Submission lifecycle (client-visible)

![Submission lifecycle](https://i.imgur.com/3lg3l3P.png)

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
  PENDING --> CANCELLED
  COMPILING --> CANCELLED
  QUEUED --> CANCELLED
  RUNNING --> CANCELLED
  DONE --> [*]
  ERROR --> [*]
  CANCELLED --> [*]
```

</details>

---

## Error Model — gRPC status-first + structured details

_Source:_ `reference/error-model.md`

![Error Model — gRPC status-first + structured details](https://i.imgur.com/aJq4xcz.png)

<details>
<summary>code</summary>

```text
flowchart TB
  Err[Failure event] --> S[gRPC Status Code]
  S --> D[google.rpc.Status.details]
  D --> EI["ErrorInfo (reason/domain)"]
  D --> BR["BadRequest (field violations)"]
  D --> RI["RetryInfo (retry delay)"]
  D --> ResI["ResourceInfo (resource context)"]
  D --> DebI["DebugInfo (internal only)"]
```

</details>

### Retry decision (client-side)

![Retry decision](https://i.imgur.com/GeXk7oe.png)

<details>
<summary>code</summary>

```text
flowchart LR
  C{gRPC code}
  C -->|UNAVAILABLE| R["Retry w/ backoff\n(use RetryInfo if present)"]
  C -->|RESOURCE_EXHAUSTED| R
  C -->|ABORTED| R
  C -->|DEADLINE_EXCEEDED| R2["Retry policy-dependent\nrespect overall deadline"]
  C -->|FAILED_PRECONDITION| N["No retry by default\n(policy-dependent)"]
  C -->|NOT_FOUND| N
  C -->|INVALID_ARGUMENT| X[Do not retry]
  C -->|PERMISSION_DENIED| X
  C -->|UNAUTHENTICATED| X
  C -->|INTERNAL| X2[No automatic retry by default]
```

</details>

---

## Error Mapping — Provider/Subsystem → Canonical Errors

_Source:_ `reference/error-mapping.md`

![Error Mapping — Provider/Subsystem → Canonical Errors](https://i.imgur.com/QLCeaAM.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant Caller
  participant Svc as Eigen Service
  participant Dep as Downstream / Provider

  Caller->>Svc: RPC
  Dep-->>Svc: provider error / exception
  Note over Svc: Normalize to gRPC status + google.rpc details
  Svc-->>Caller: status code + ErrorInfo.reason (+ RetryInfo/BadRequest)
```

</details>

### Canonical mapping pipeline

![Canonical mapping pipeline](https://i.imgur.com/n9OrZna.png)

<details>
<summary>code</summary>

```text
flowchart TB
  Raw["Raw error\n(exception, HTTP status, vendor code)"] --> Classify["Classify taxonomy\n(transient/quota/auth/validation)"]
  Classify --> Map[Map to gRPC code\n+ stable reason code]
  Map --> Details["Attach structured details\nErrorInfo/RetryInfo/BadRequest"]
  Details --> Emit[Emit gRPC status-first]
```

</details>

---

## AQO v1.0 — IR structure and validation invariants

_Source:_ `reference/formats/aqo.md`

![AQO v1.0 — IR structure and validation invariants](https://i.imgur.com/47aJehF.png)

<details>
<summary>code</summary>

```text
classDiagram
  class AQO {
    +string version
    +int qubits
    +Operation[] operations
  }
  class Operation {
    +string op
    +int[] q
    +int[] c?  %% for MEASURE
    +number[] params?
    +map<string,any> meta?
  }
  AQO "1" --> "many" Operation
```

</details>

### AQO validation gates

![AQO validation gates](https://i.imgur.com/wVU6lPM.png)

<details>
<summary>code</summary>

```text
flowchart LR
  A[AQO bytes] --> P[Parse JSON / Proto]
  P --> V1{version==1.0}
  V1 -->|no| Fail["INVALID_ARGUMENT\nEIGEN_AQO_VERSION_UNSUPPORTED"]
  V1 --> V2{indices in bounds}
  V2 -->|no| Fail2["INVALID_ARGUMENT\nEIGEN_AQO_INDEX_OOB"]
  V2 --> V3{opcode known + arity valid}
  V3 -->|no| Fail3["INVALID_ARGUMENT\nEIGEN_AQO_UNKNOWN_OPCODE"]
  V3 --> V4{"MEASURE len(q)==len(c)"}
  V4 -->|no| Fail4["INVALID_ARGUMENT\nEIGEN_AQO_MEASURE_MISMATCH"]
  V4 --> OK[Validated AQO]
```

</details>

---

## QFS Layout v1.0 — Job-scoped artifact tree

_Source:_ `reference/formats/qfs-layout.md`

![QFS Layout v1.0 — Job-scoped artifact tree](https://i.imgur.com/xmDB7g5.png)

<details>
<summary>code</summary>

```text
flowchart TB
  root[qfs://jobs/<job_id>/]
  root --> in[input/]
  in --> job[job.yaml]
  in --> src[source/*]
  root --> comp[compiled/]
  comp --> aqo[compiled.aqo.json]
  comp --> qasm["compiled.qasm (opt)"]
  comp --> cmeta[metadata.json]
  root --> res[results/]
  res --> rjson[results.json]
  res --> parquet[results.parquet]
  res --> err["error.json (on ERROR)"]
  root --> logs[logs/]
  root --> meta[meta/]
  root --> timeline[timeline/]
```

</details>

### Atomic publish pattern (local FS / object store)

![Atomic publish pattern](https://i.imgur.com/zTMGGD8.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant W as Writer (Kernel/Service)
  participant S as Storage backend
  participant R as Reader

  W->>S: write temp object (tmp/uuid)
  W->>S: fsync/flush (or multipart finalize)
  W->>S: rename/move to final path (atomic publish)
  R->>S: read final path
  S-->>R: complete bytes (no partial reads)
```

</details>

---

## Orchestration Observability — Control-plane telemetry

_Source:_ `reference/orchestration-observability-contract.md`

![Orchestration Observability — Control-plane telemetry](https://i.imgur.com/pYiMfDg.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Services
    API[System API]
    K[Kernel/QRTX]
    RM[Resource/Scheduler]
    W["Workers (if distributed)"]
  end
  subgraph Telemetry
    OTel[OpenTelemetry SDK]
    Prom[Prometheus]
    Logs[Loki/Elastic]
    Trace[Jaeger/Tempo]
  end

  API --> OTel
  K --> OTel
  RM --> OTel
  W --> OTel

  OTel -->|metrics| Prom
  OTel -->|logs| Logs
  OTel -->|traces| Trace
```

</details>

### Span coverage — enqueue to execute

![Span coverage — enqueue to execute](https://i.imgur.com/fzZ8gHR.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant API as System API
  participant K as Kernel
  participant RM as Scheduler/Resource
  participant DM as Driver Manager

  API->>K: EnqueueJob
  Note over API,K: traceparent propagated
  K->>RM: Allocate/Queue
  RM-->>K: placement decision
  K->>DM: ExecuteCircuit
  DM-->>K: result
```

</details>

---

## Intelligent Runtime Observability — Decisioning + fallback signals

_Source:_ `reference/intelligent-runtime-observability-contract.md`

![Intelligent Runtime Observability — Decisioning + fallback signals](https://i.imgur.com/S7mivOq.png)

<details>
<summary>code</summary>

```text
flowchart TB
  D["Decision point\n(backend select / optimize / adapt)"] --> I["Inputs digests\n(policy/topology/aqo)"]
  I --> S["Scoring\n(heuristic/ML)"]
  S --> V[Symbolic/policy validation]
  V --> O["Decision output\n+ digest"]
  O --> Q["Persist explain/replay artifacts (QFS)"]
  O --> M[Emit metrics: decisions_total, fallbacks_total]
```

</details>

### Fallback chain (deterministic)

![Fallback chain](https://i.imgur.com/XK5HUlI.png)

<details>
<summary>code</summary>

```text
flowchart LR
  GNN[GNN inference] -->|fail / low confidence| H["Heuristic (deterministic)"]
  H -->|fail| S["Static mapper (deterministic)"]
  S -->|fail| R["Reject (FAILED_PRECONDITION/UNIMPLEMENTED)"]
```

</details>

---

## Cluster Runtime Observability — Split/Merge telemetry

_Source:_ `reference/cluster-runtime-observability-contract.md`

![Cluster Runtime Observability](https://i.imgur.com/1lrdJrN.png)

<details>
<summary>code</summary>

```text
flowchart TB
  SP[Split Planner] --> W1[Worker 1]
  SP --> W2[Worker 2]
  SP --> Wn[Worker N]
  W1 --> MC[Merge Coordinator]
  W2 --> MC
  Wn --> MC
  MC --> OUT[Final result]

  SP -.metrics/traces.-> OTel[OTel]
  W1 -.metrics/traces.-> OTel
  W2 -.metrics/traces.-> OTel
  MC -.metrics/traces.-> OTel
```

</details>

---

## Multi-Device Execution — Split/Execute/Merge

_Source:_ `reference/multi-device-execution-contract.md`

![Multi-Device Execution](https://i.imgur.com/x0Ew2oe.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant K as Kernel/QRTX
  participant SP as SplitPlanner
  participant W as Worker Pool
  participant MC as MergeCoordinator
  participant QFS as QFS

  K->>SP: PlanSplit(job_id, circuit, constraints)
  SP-->>K: shard plan + determinism digest
  K->>QFS: persist split plan

  loop for each shard
    K->>W: ExecuteShard(shard)
    W-->>K: shard result + telemetry
    K->>QFS: persist shard result
  end

  K->>MC: Merge(job_id, shard results refs)
  MC-->>K: merged result + merge decision digest
  K->>QFS: persist merged result + lineage
```

</details>

### Distributed job state (illustrative)

![Distributed job state](https://i.imgur.com/NQ2vVye.png)

<details>
<summary>code</summary>

```text
stateDiagram-v2
  [*] --> PLANNING
  PLANNING --> EXECUTING_SHARDS
  EXECUTING_SHARDS --> MERGING
  MERGING --> DONE
  EXECUTING_SHARDS --> ERROR
  MERGING --> ERROR
  PLANNING --> CANCELLED
  EXECUTING_SHARDS --> CANCELLED
  DONE --> [*]
  ERROR --> [*]
  CANCELLED --> [*]
```

</details>

---

## Eigen-Lang v1.0 — Compiler-facing structure

_Source:_ `reference/eigen-lang.md`

![Eigen-Lang v1.0 — Compiler-facing structure](https://i.imgur.com/WDObmPI.png)

<details>
<summary>code</summary>

```text
flowchart LR
  Src["Eigen-Lang source\n(program.eigen.py)"] --> AST[Parse to Python AST]
  AST --> Allow{Allowlist validation}
  Allow -->|ok| Ann["Annotate (symbols/tags)"]
  Allow -->|fail| Err["INVALID_ARGUMENT\nBadRequest violations"]
  Ann --> IR[Lower to internal IR]
  IR --> AQO["AQO v1.0 (canonical)"]
```

</details>

### Safety boundary (AST-only)

![Safety boundary](https://i.imgur.com/4k1SmBA.png)

<details>
<summary>code</summary>

```text
flowchart TB
U[Source]-->P[Parser]
P-->A[AST]
A-->V[Validator]
V-->|forbidden|F[Reject]
V-->|ok|L[Lowering]
L-->Out[AQO]
```

</details>

---

## Benchmark Run API — execution and artifacting

_Source:_ `reference/api/benchmark-run.md`

![Benchmark Run API](https://i.imgur.com/TLcuVPg.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant User
  participant API as System API
  participant K as Kernel
  participant QFS as QFS
  participant BM as Benchmark Runtime

  User->>API: POST /v1/benchmarks/run (or gRPC)
  API->>K: Enqueue benchmark job
  K->>QFS: persist benchmark inputs
  K->>BM: Execute benchmark suite
  BM-->>K: benchmark results
  K->>QFS: persist benchmark artifacts + summary
  API-->>User: run_id/job_id + refs
```

</details>

---

## Explain Backend Selection API — rationale retrieval

_Source:_ `reference/api/explain-backend-selection.md`

![Explain Backend Selection API](https://i.imgur.com/2jGz9XF.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant Client
  participant API as System API
  participant K as Kernel/Runtime Controller
  participant QFS as QFS

  Client->>API: Explain backend selection (job_id or decision_id)
  API->>K: GetDispatchRationale(job_id)
  K->>QFS: load decision snapshot + explain ref
  QFS-->>K: explain.json ref (or payload)
  K-->>API: bounded rationale + artifact refs
  API-->>Client: rationale
```

</details>

---

## Benchmark Observability — telemetry surfaces

_Source:_ `reference/benchmark-observability-contract.md`

![Benchmark Observability](https://i.imgur.com/0cXFnRp.png)

<details>
<summary>code</summary>

```text
flowchart LR
  BR["Benchmark Runner"] --> M["Metrics<br>(eigen_benchmark_*)"]
  BR --> T["Traces<br>benchmark spans"]
  BR --> L["Logs<br>structured"]
  M --> Prom["Prometheus"]
  T --> Trace["Jaeger/Tempo"]
  L --> Logs["Loki/Elastic"]
```

</details>

---

## Reference Docs Index — how contracts relate

_Source:_ `reference/README.md`

![Benchmark Observability](https://i.imgur.com/7AWGErG.png)

<details>
<summary>code</summary>

```text
flowchart TB
  subgraph API
    GP[grpc-public.md]
    GI[grpc-internal.md]
    BR[benchmark-run.md]
    EX[explain-backend-selection.md]
  end
  subgraph Formats
    AQO[aqo.md]
    QL[qfs-layout.md]
  end
  subgraph Runtime
    JS[jobspec.md]
    EM[error-model.md]
    MAP[error-mapping.md]
  end
  subgraph Obs
    OO[orchestration-observability-contract.md]
    IO[intelligent-runtime-observability-contract.md]
    CO[cluster-runtime-observability-contract.md]
    BO[benchmark-observability-contract.md]
  end
  subgraph Distributed
    MD[multi-device-execution-contract.md]
  end
  Lang[eigen-lang.md]

  JS --> GP
  GP --> GI
  GI --> AQO
  AQO --> QL
  EM --> MAP
  OO --> GP
  IO --> GI
  CO --> MD
  Lang --> AQO
```

</details>
