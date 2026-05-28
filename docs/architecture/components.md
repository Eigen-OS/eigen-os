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
docs/reference/runtime-decisioning.md
docs/reference/multi-device-execution-contract.md
```

### 2.3 Compiler

Document: c`omponents/compiler.md`

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
docs/reference/compiler-contracts/
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
docs/reference/runtime-decisioning.md
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
docs/reference/qfs-contracts/
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
docs/reference/runtime-decisioning.md
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
docs/reference/runtime-decisioning.md
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
docs/reference/benchmark-contracts/
docs/reference/observability-contracts/
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
docs/reference/security-contracts/
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
- adaptive orchestration reasoning.

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
