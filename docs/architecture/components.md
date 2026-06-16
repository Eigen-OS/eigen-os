# Components

This page is the authoritative index of Eigen OS architectural component descriptions (**Explanation** documents).

Normative RPC contracts, wire formats, schemas, runtime contracts, observability contracts, and API specifications are maintained under:

```text
docs/reference/
```

Architecture/component documents describe:

- subsystem responsibilities,
- runtime behavior,
- lifecycle semantics,
- orchestration interactions,
- operational boundaries,
- implementation constraints,
- integration topology.

Normative protocol behavior MUST NOT be defined exclusively in component explanation documents.

---

## 1. Architecture Layers

Eigen OS is organized into the following major architectural layers:

| **Layer** | **Purpose** |
|---|---|
| API Layer | Public and internal control surfaces |
| Compilation Layer | Program compilation and optimization |
| Runtime Layer | Execution orchestration and scheduling |
| Distributed Execution Layer | Multi-device and cluster coordination |
| Storage Layer | Immutable artifact and lineage persistence |
| Security Layer | Isolation, policy, and trust enforcement |
| Observability Layer | Metrics, traces, explainability, auditing |
| Intelligence Layer | Adaptive scheduling and optimization |

---

## 2. MVP Components

The following components are required for Eigen OS `1.x`.

### 2.1 System API

Document: `components/system-api.md`

Responsibilities:

- public API surface,
- job submission,
- execution lifecycle management,
- artifact retrieval,
- explainability access,
- orchestration control APIs,
- authentication and authorization integration.

Normative references:

```text
docs/reference/api/
docs/reference/jobspec.md
docs/reference/error-model.md
```

---

### 2.2 Kernel / QRTX

Document: `components/qrtx.md`

Responsibilities:

- hybrid runtime execution,
- task lifecycle orchestration,
- runtime scheduling integration,
- deterministic execution handling,
- async execution state management,
- execution replay coordination.

Normative references:

```text
docs/reference/intelligent-runtime-observability-contract.md
docs/reference/multi-device-execution-contract.md
```

### 2.3 Compiler

Document: `components/compiler.md`

Responsibilities:

- hybrid program compilation,
- IR generation,
- optimization pipelines,
- backend lowering,
- deterministic packaging integration,
- replay-safe compilation semantics.

Normative references:

```text
docs/reference/jobspec.md
docs/reference/eigen-lang.md
docs/reference/formats/aqo.md
```

---

### 2.4 Driver Manager

Document: `components/driver-manager.md`

Responsibilities:

- backend abstraction,
- provider normalization,
- backend capability discovery,
- runtime backend routing,
- provider error normalization,
- backend health integration.

Normative references:

```text
docs/reference/error-model.md
docs/reference/intelligent-runtime-observability-contract.md
```

---

### 2.5 QFS

Document: `components/qfs.md`

Responsibilities:

- immutable artifact persistence,
- lineage storage,
- distributed runtime artifact storage,
- replay artifact preservation,
- checksum validation,
- execution auditability.

Normative references:

```text
docs/reference/formats/qfs-layout.md
docs/reference/multi-device-execution-contract.md
```

---

### 2.6 Resource Manager

Document: `components/resource-manager.md`

Responsibilities:

- resource allocation,
- lease management,
- quota enforcement,
- fairness coordination,
- retry-aware capacity handling,
- distributed execution coordination.

Normative references:

```text
docs/reference/orchestration-observability-contract.md
docs/reference/multi-device-execution-contract.md
```

---

### 2.7 Scheduler & Orchestration

Document: `components/scheduler.md`

Responsibilities:

- workload scheduling,
- shard placement,
- orchestration policy execution,
- starvation prevention,
- fairness enforcement,
- rebalance coordination,
- degraded-mode orchestration.

Normative references:

```text
docs/reference/orchestration-observability-contract.md
docs/reference/intelligent-runtime-observability-contract.md
```

---

### 2.8 Intelligent Runtime Controller

Document: `components/runtime-controller.md`

Responsibilities:

- adaptive backend selection,
- intelligent routing,
- runtime scoring,
- explainability generation,
- policy evaluation,
- degraded runtime handling,
- runtime optimization loops.

Normative references:

```text
docs/reference/intelligent-runtime-observability-contract.md
```

---

### 2.9 Benchmark Service

Document: `components/benchmark-service.md`

Responsibilities:

- benchmark execution,
- reproducible performance evaluation,
- backend comparison,
- telemetry collection,
- deterministic benchmark orchestration.

Notes:

- contract-focused benchmark runtime,
- implementation reference:
- `src/services/benchmark-service/README.md`

Normative references:

```text
docs/reference/api/benchmark-run.md
docs/reference/benchmark-observability-contract.md
```

---

### 2.10 Security & Isolation

Document: `components/security-isolation.md`

Responsibilities:

- sandboxing,
- execution isolation,
- policy enforcement,
- secret protection,
- artifact integrity validation,
- runtime trust boundaries.

Normative references:

```text
docs/reference/security/authz.md
docs/reference/jobspec.md
```

---

### 2.11 Observability

Document: `components/observability.md`

Responsibilities:

- metrics,
- tracing,
- explainability telemetry,
- operational auditing,
- runtime telemetry export,
- SLO instrumentation,
- distributed trace continuity.

Normative references:

```text
docs/reference/intelligent-runtime-observability-contract.md
docs/reference/orchestration-observability-contract.md
```

---

## 3. Distributed Runtime Components

The following components are mandatory for distributed execution support.

### 3.1 Split Planner

Responsibilities:

- deterministic shard planning,
- workload partitioning,
- replay-safe split semantics,
- backend compatibility analysis.

Normative references:

```text
docs/reference/multi-device-execution-contract.md
```

---

### 3.2 Merge Coordinator

Responsibilities:

- partial result validation,
- quorum evaluation,
- merge policy execution,
- lineage-safe merge decisions,
- retry-aware merge semantics.

Normative references:

```text
docs/reference/multi-device-execution-contract.md
```

---

### 3.3 Runtime Workers

Responsibilities:

- shard execution,
- retry handling,
- partial failure reporting,
- envelope generation,
- trace propagation.

Normative references:

```text
docs/reference/multi-device-execution-contract.md
docs/reference/error-model.md
```

---

## 4. Cross-Cutting Runtime Concerns

The following concerns apply across all major components.

| **Concern** | **Description** |
|---|---|
| Determinism | Identical inputs produce identical execution semantics |
| Replayability | Runtime execution remains reproducible |
| Explainability | Runtime decisions remain inspectable |
| Observability | Metrics/traces remain standardized |
| Security | Isolation and policy enforcement are mandatory |
| Auditability | Execution lineage remains durable |
| Compatibility | Stable contracts preserved within MAJOR versions |

---

## 5. Post-MVP Components

The following components are planned extensions beyond the MVP/runtime baseline.

### 5.1 Client SDKs

Document: `components/client-sdks.md`

Responsibilities:

- multi-language API bindings,
- retry normalization,
- structured error handling,
- telemetry propagation,
- async workflow integration.

---

### 5.2 HWE

Document: `components/hwe.md`

Responsibilities:

- hardware execution abstraction,
- topology-aware runtime integration,
- hardware capability discovery.

---

### 5.3 Knowledge Base

Document: `components/knowledge-base.md`

Responsibilities:

- execution knowledge indexing,
- replay intelligence,
- optimization history retention,
- operational recommendations.

---

### 5.4 GNN Optimizer

Document: `components/gnn-optimizer.md`

Responsibilities:

- graph-based optimization,
- adaptive runtime scoring,
- topology-aware scheduling heuristics.

---

### 5.5 Neuro-Symbolic Core

Document: `components/neuro-symbolic-core.md`

Responsibilities:

- symbolic reasoning integration,
- policy inference,
- explainability augmentation,
- adaptive orchestration reasoning,
- internal deployable service boundary (`src/services/neuro-symbolic-service/`).

---

## 6. Component Ownership Rules

Each component document SHOULD define:

- responsibilities,
- external dependencies,
- lifecycle semantics,
- failure domains,
- observability integration,
- security boundaries,
- operational invariants.

Component documents MUST NOT redefine:

- wire contracts,
- RPC schemas,
- canonical status mappings,
- observability metric contracts.

Those definitions belong exclusively under:

```text
docs/reference/
```

----

## 7. Documentation Structure Invariants

The following invariants are mandatory:

`. Contracts live under `docs/reference/`.
2. Component documents remain explanatory.
3. Public runtime semantics remain contract-driven.
4. Cross-component behavior MUST reference normative contracts.
5. Runtime observability contracts MUST remain centralized.
6. Error semantics MUST remain centralized in `error-model.md`.
7. Distributed execution semantics MUST remain centralized in `multi-device-execution-contract.md`.

---

## 8. Minimum Closure Criteria

The component architecture index is considered complete only when:

1. all MVP components are documented,
2. all runtime-critical subsystems reference normative contracts,
3. distributed runtime components are defined,
4. observability ownership boundaries are documented,
5. security boundaries are documented,
6. orchestration/runtime ownership is unambiguous,
7. contract-vs-explanation separation is enforced,
8. all public runtime surfaces map to stable contracts.

---

## Appendix A. Diagrams (normative)

### A.1 Layered architecture map (high-level)

![Layered architecture map](https://i.imgur.com/7Mcy4YS.png)

<details>
<summary>code</summary>

```text
flowchart TB
  subgraph L0["Client / UX"]
    SDK[Client SDKs / CLI]
    Apps[External Clients]
  end

  subgraph L1["API Layer"]
    SysAPI["System API\n(public ingress)"]
  end

  subgraph L2["Runtime Layer"]
    Kernel["Kernel / QRTX\n(orchestration)"]
    RM["Resource Manager\n(allocation/reservations)"]
    Scheduler["Scheduler & Orchestration"]
    RC["Intelligent Runtime Controller"]
    HWE["HWE\n(post-MVP)"]
  end

  subgraph L3["Compilation Layer"]
    Compiler["Compiler\n(AST-only → AQO)"]
    NSC["Neuro-Symbolic Core\n(post-MVP)"]
  end

  subgraph L4["Execution Abstraction"]
    DM[Driver Manager]
    Drivers[QDriver Plugins / Remote QDrivers]
    Backends[(Quantum Hardware / Vendor Cloud / Simulators)]
  end

  subgraph L5["Storage Layer"]
    QFS["QFS\n(CircuitFS / StateStore / LiveQubitManager)"]
    KB["Knowledge Base / OKB\n(post-MVP)"]
  end

  subgraph L6["Cross-cutting"]
    Sec[Security & Isolation]
    Obs[Observability]
  end

  SDK --> SysAPI
  Apps --> SysAPI

  SysAPI --> Kernel

  Kernel --> Compiler
  Kernel --> Scheduler
  Kernel --> RM
  Kernel --> RC
  Kernel --> DM
  Kernel --> QFS

  Compiler -. "advisory" .-> NSC
  RC -. "advisory" .-> NSC
  HWE -. "uses" .-> DM

  DM --> Drivers --> Backends

  NSC -. "optional" .-> KB
  RC -. "optional" .-> KB

  Sec -. "applies" .-> SysAPI
  Sec -. "applies" .-> Kernel
  Sec -. "applies" .-> Compiler
  Sec -. "applies" .-> DM
  Sec -. "applies" .-> QFS

  Obs -. "exports" .-> SysAPI
  Obs -. "exports" .-> Kernel
  Obs -. "exports" .-> Compiler
  Obs -. "exports" .-> DM
  Obs -. "exports" .-> QFS

  %% Цвета слоёв
  classDef L0 fill:#e0f7fa,stroke:#006064
  classDef L1 fill:#ffe0b2,stroke:#e65100
  classDef L2 fill:#c8e6c9,stroke:#1b5e20
  classDef L3 fill:#f8bbd0,stroke:#880e4f
  classDef L4 fill:#d1c4e9,stroke:#4527a0
  classDef L5 fill:#fff9c4,stroke:#f57f17
  classDef L6 fill:#f5f5f5,stroke:#616161,stroke-dasharray: 3 3

  class SDK,Apps L0
  class SysAPI L1
  class Kernel,RM,Scheduler,RC,HWE L2
  class Compiler,NSC L3
  class DM,Drivers,Backends L4
  class QFS,KB L5
  class Sec,Obs L6
```

</details>

---

### A.2 C4-ish container topology (MVP baseline vs Post-MVP extensions)

![C4-ish container topology](https://i.imgur.com/xbs5ODx.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph MVP["MVP baseline (required for 1.x)"]
    SysAPI[system-api]
    Kernel["eigen-kernel (QRTX)"]
    Compiler[eigen-compiler]
    DM[driver-manager]
    QFS["qfs (CircuitFS L3 + facade)"]
    Sec["security-isolation (baseline rules)"]
    Obs["observability (metrics/logs/traces)"]
  end

  subgraph Post["Post-MVP extensions (Phase-1+)"]
    RM["resource-manager (standalone)"]
    Scheduler["scheduler (standalone)"]
    RC[runtime-controller]
    HWE[hwe]
    GNN[gnn-optimizer]
    KB["knowledge-base / OKB"]
    NSC[neuro-symbolic-core]
    NSC[neuro-symbolic-core\ninternal service]
  end

  SysAPI --> Kernel
  Kernel --> Compiler
  Kernel --> DM
  Kernel --> QFS

  Kernel -. "may call" .-> RM
  Kernel -. "may call" .-> Scheduler
  Kernel -. "may call" .-> RC
  RC -. "may call" .-> HWE
  HWE -. "may call" .-> GNN
  NSC -. "may coordinate" .-> GNN
  NSC -. "may read/write" .-> KB

  Sec -. "governs" .-> MVP
  Obs -. "instruments" .-> MVP
  Sec -. "governs" .-> Post
  Obs -. "instruments" .-> Post
```

</details>

---

### A.3 Sequence (E2E job flow): Submit → Compile → Execute → Persist → Results

![E2E job flow](https://i.imgur.com/LBXudDY.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant C as Client SDK/CLI
  participant API as System API
  participant K as Kernel/QRTX
  participant CC as Compiler
  participant Q as QFS
  participant DM as Driver Manager
  participant B as Backend/Simulator

  C->>API: SubmitJob (JobSpec + metadata)
  API->>K: EnqueueJob (forward)
  K->>Q: Persist input/source (job scope)
  K->>CC: CompileJob / CompileCircuit
  CC->>Q: Write compiled AQO + metadata
  K->>DM: ExecuteCircuit (AQO + device_id)
  DM->>B: Provider execution
  B-->>DM: Raw result / error
  DM-->>K: Normalized ExecutionResult
  K->>Q: Write results.json (or error.json)
  K-->>API: job status/results available
  API-->>C: GetJobStatus / GetJobResults
```

</details>

---

### A.4 Sequence (Device discovery & reservation): List → Status → Reserve

![Device discovery & reservation](https://i.imgur.com/Y29mN92.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant C as Client SDK/CLI
  participant API as System API
  participant K as Kernel/QRTX
  participant DM as Driver Manager
  participant RM as Resource Manager (Phase-1+)

  C->>API: ListDevices
  API->>K: (forward) ListDevices / QueryDevices
  K->>DM: ListDevices (internal)
  DM-->>K: Device catalog snapshot
  K-->>API: Device list
  API-->>C: Device list

  C->>API: GetDeviceStatus(device_id)
  API->>K: forward
  K->>DM: GetDeviceStatus
  DM-->>K: Status/topology hints
  K-->>API: Status
  API-->>C: Status

  C->>API: ReserveDevice(device_id)
  alt MVP placeholder reservation
    API-->>C: reservation token (non-enforced)
  else Phase-1 enforced reservation
    API->>K: forward
    K->>RM: ReserveExecutionSlot
    RM-->>K: reservation_id / expiry / constraints
    K-->>API: reservation response
    API-->>C: reservation response
  end
```

</details>

---

### A.5 Contract vs Explanation ownership boundary

![Contract vs Explanation ownership boundary](https://i.imgur.com/jC4SFJz.png)

<details>
<summary>code</summary>

```text
flowchart TB
  Expl["Component docs\n(components/*.md)\nExplanation only"] -->|MUST reference| Ref["Normative contracts\n(docs/reference/*)"]
  Expl -. "MUST NOT redefine" .-> Wire["Wire contracts\n(proto / schemas / error model)"]
  Ref --> Wire
```

</details>

---

### A.6 Allowed call graph (hard boundaries)

![Allowed call graph](https://i.imgur.com/dlC4lnh.png)

<details>
<summary>code</summary>

```text
flowchart LR
  SDK[SDK/CLI] --> API[System API]

  API --> K[Kernel/QRTX]

  K --> CC[Compiler]
  K --> DM[Driver Manager]
  K --> QFS[QFS]

  subgraph Optional["Optional / Phase-1+"]
    K -.-> RM[Resource Manager]
    K -.-> SCH[Scheduler]
    K -.-> RC[Intelligent Runtime Controller]
    RC -.-> HWE[HWE]
    HWE -.-> GNN[GNN Optimizer]
    RC -.-> KB[Knowledge Base / OKB]
    CC -.-> KB
    RC -.-> NSC[Neuro-Symbolic Core]
    CC -.-> NSC
  end

  DM --> Drivers[Drivers/QDrivers] --> Backend[(Providers/Simulators)]

  %% hard constraints
  API -. MUST NOT .-> Backend
  K -. MUST NOT .-> Backend
  CC -. MUST NOT .-> Backend
```

</details>

---

### A.7 Distributed execution topology (Split Planner → Workers → Merge)

![Distributed execution topology](https://i.imgur.com/VCCkdne.png)

<details>
<summary>code</summary>

```text
flowchart TB
  API[System API] --> K[Kernel/QRTX]

  subgraph Dist["Distributed Execution Layer (Phase-1+)"]
    SP[Split Planner]
    W1[Runtime Worker #1]
    W2[Runtime Worker #2]
    WN[Runtime Worker #N]
    MC[Merge Coordinator]
  end

  K --> SP
  SP --> W1
  SP --> W2
  SP --> WN
  W1 --> MC
  W2 --> MC
  WN --> MC

  MC --> QFS[(QFS lineage + artifacts)]
  K --> QFS
  MC --> K
```

</details>
