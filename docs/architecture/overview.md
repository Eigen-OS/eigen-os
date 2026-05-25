# Eigen OS Architecture Overview

- **Document Status:** Normative MVP Architecture Specification
Version: 1.0
- **Scope:** Phase 0 / MVP baseline + implemented extensions
- **Last Updated:** 2026-05-24
- **Supersedes:** Previous draft architecture overview revisions
- **Audience:** Core developers, infrastructure engineers, compiler/runtime contributors, driver authors
- **Related Documents:**

    - `architecture/contract-map.md`
    - `architecture/data-flow.md`

---

## 1. Introduction

### 1.1 Purpose

Eigen OS is a modular hybrid quantum-classical operating environment for orchestrating compilation, scheduling, execution, and result management of quantum workloads across heterogeneous backends.

The system provides:

- a stable high-level programming model,
- deterministic compilation contracts,
- runtime orchestration,
- backend abstraction,
- artifact persistence,
- observability and traceability,
- extensible compiler/runtime/driver infrastructure.

This document defines the canonical architectural structure of the Eigen OS MVP and the accepted forward-compatible extensions already implemented beyond the original MVP specification.

It is the primary architectural reference for implementation alignment.

---

## 2. System Vision

Eigen OS abstracts unstable and vendor-specific quantum infrastructure behind stable contracts and orchestration layers.

The platform is designed to allow domain specialists to execute hybrid quantum-classical workflows without requiring direct interaction with:

- low-level qubit topology,
- vendor SDK internals,
- hardware routing constraints,
- pulse-level execution,
- backend-specific compilation pipelines.

---

## 3. Architectural Principles

### 3.1 Hybrid-First Execution

The system is designed primarily for hybrid workloads combining:

- classical optimization,
- quantum execution,
- iterative parameter refinement,
- distributed orchestration.

Variational algorithms (VQE, QAOA, hybrid ML workloads) are first-class architectural targets.

---

### 3.2 Stable Interface Boundaries

All major components communicate exclusively through versioned contracts.

Primary interface categories:

| **Boundary** | **Contract** |
|---|---|
| Client ↔ System API | `eigen.api.v1` |
| System API ↔ Kernel | `eigen.internal.v1` |
| Kernel ↔ Compiler | `eigen.internal.v1` |
| Kernel ↔ Driver Manager | `eigen.internal.v1` |
| Driver ↔ Backend | Vendor SDK / REST / gRPC |

Internal implementation changes must not break external contracts.

---

### 3.3 Deterministic Compilation

Compilation is deterministic.

Identical:

- source,
- compiler options,
- target metadata,
- referenced artifacts

must produce identical AQO output.

Server-side user code execution is prohibited.

Only AST parsing and transformation are permitted.

---

### 3.4 Backend Abstraction

The same Eigen-Lang program must execute on any supported backend through compatible drivers without source modification.

Backend-specific optimizations must remain encapsulated within:

- compiler target passes,
- driver translation layers,
- runtime scheduling logic.

---

### 3.5 Observability by Default

All runtime stages expose:

- metrics,
- structured logs,
- traces,
- correlation IDs.

Minimum required correlation identifiers:

- `trace_id`
- `job_id`
- `device_id`

---

### 3.6 Modular Extensibility

The architecture supports independent evolution of:

- compilers,
- optimizers,
- schedulers,
- drivers,
- orchestration policies,
- backend integrations.

No core service modifications should be required to add new drivers or compiler backends.

---

## 4. High-Level System Architecture

Eigen OS is organized into four architectural layers.

```text
┌────────────────────────────────────────────┐
│ Level 1 — Abstraction Layer               │
│ Eigen-Lang / SDK / CLI / System API       │
└────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│ Level 2 — Kernel Layer                    │
│ QRTX Scheduler / QFS / Runtime State      │
└────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│ Level 3 — Runtime Services                │
│ Compiler / Driver Manager / KB / GNN      │
└────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│ Level 4 — Hardware Abstraction Layer      │
│ Drivers / Simulators / Quantum Hardware   │
└────────────────────────────────────────────┘
```

---

## 5. Level 1 — Abstraction Layer

### 5.1 Eigen-Lang

Eigen-Lang is the high-level hybrid DSL of Eigen OS.

Current MVP baseline:

- Python-based syntax
- AST-only compilation
- deterministic transformation pipeline
- symbolic parameter support

#### Supported Conceptual Primitives

| **Category** | **Examples** |
|---|---|
| Quantum types | `QubitRegister`, `Observable`, `Ansatz` |
| Decorators | `@hybrid_program`, `@cost_function` |
| Hybrid constructs | `ExpectationValue`, `minimize()` |
| Templates | `create_hea_ansatz()` |
| Utilities | `visualize_circuit()` |

#### MVP Compiler Restrictions

Allowed:

- declarative program structure,
- symbolic expressions,
- constrained imports.

Disallowed:

- arbitrary runtime execution,
- unrestricted dynamic evaluation,
- unsafe filesystem/network execution.

Compilation operates strictly on Python AST.

---

### 5.2 SDK and CLI

The CLI and SDK provide the user-facing execution interface.

Primary commands:

| **Command** | **Purpose** |
|---|---|
| `eigen submit` | Submit jobs |
| `eigen status` | Query state |
| `eigen results` | Retrieve results |
| `eigen devices` | Query backend catalog |

The CLI packages user assets into `SubmitJobRequest`.

---

### 5.3 System API

The System API is the only public ingress to the runtime.

#### Responsibilities

- authentication,
- authorization,
- request validation,
- routing,
- observability boundary,
- external API compatibility.

#### Public API Contract

Package:

```text
eigen.api.v1
```

#### Public Services

| **Service** | **Status** |
|---|---|
| JobService | Implemented |
| DeviceService | Implemented |
| KnowledgeBaseService | Implemented |
| StreamJobUpdates | Implemented |
| GetDispatchRationale | Implemented |
| GetDeviceDetails | Implemented |

#### Primary RPCs

| **RPC** | **Purpose** |
|---|---|
| SubmitJob | Submit workload |
| GetJobStatus | Query runtime state |
| CancelJob | Cancel execution |
| GetJobResults | Retrieve results |
| StreamJobUpdates | Poll-stream updates |
| ListDevices | Enumerate backends |

---

## 6. Level 2 — Kernel Layer

### 6.1 QRTX Kernel

The Eigen Kernel is the orchestration core.

Implementation language:

```text
Rust
```

The kernel owns:

- job lifecycle,
- state machine,
- orchestration,
- scheduling,
- artifact coordination,
- runtime transitions.

---

### 6.2 Runtime State Machine

Canonical client-visible states:

```text
PENDING
→ COMPILING
→ QUEUED
→ RUNNING
→ DONE | ERROR | CANCELLED
```

The kernel is the single source of truth for runtime state.

System API must not invent or reinterpret states.

---

### 6.3 Scheduling Model

Current MVP scheduler:

- queue-based,
- deterministic,
- backend-aware,
- simulator-first.

Future-compatible extension points already defined:

- noise-aware scheduling,
- topology-aware placement,
- multi-program scheduling,
- adaptive retry policies,
- hardware scoring.

---

### 6.4 QFS — Quantum File System

QFS is the artifact persistence layer.

#### Current Production Baseline

Implemented:

```text
QFS Level 3
```

#### Level 3 Responsibilities

Persistent storage for:

- source bundles,
- AQO artifacts,
- QASM,
- execution results,
- logs,
- metadata,
- manifests.

#### Storage Backends

Current implementations:

- SQLite
- MinIO / S3-compatible object storage

---

### 6.5 Future QFS Layers

#### Level 2 — Quantum State Store

Target capability:

- serialized quantum state persistence,
- tomography checkpointing,
- debugging snapshots.

Not required for MVP execution.

---

#### Level 1 — Live Qubit Manager

Target capability:

- direct qubit allocation,
- feed-forward execution,
- hardware isolation management.

Not part of MVP runtime.

---

## 7. Level 3 — Runtime Services

### 7.1 Compiler Service

Implementation language:

```text
Python
```

#### Responsibilities

- AST parsing,
- validation,
- deterministic lowering,
- AQO generation,
- target optimization.

#### Compilation Pipeline

```text
Eigen-Lang Source
→ AST
→ Validation
→ Transformation
→ AQO
→ Backend Payload
```

#### Current Compiler Guarantees

Implemented:

- deterministic AQO,
- AST safety enforcement,
- import allowlists,
- symbolic parameter handling.

---

### 7.2 AQO — Abstract Quantum Operations

AQO is the canonical intermediate representation.

#### Properties

- backend-independent,
- deterministic,
- serializable,
- symbolic.

#### Example Operations

```json
{
  "op": "RY",
  "q": [0],
  "params": {
    "theta": "p0"
  }
}
```

AQO is the boundary contract between compiler and execution runtime.

---

### 7.3 Driver Manager

The Driver Manager abstracts backend execution.

#### Responsibilities

- driver lifecycle,
- backend translation,
- execution dispatch,
- result normalization,
- capability discovery.

#### Current Runtime Baseline

Implemented:

- simulator-first drivers,
- backend abstraction,
- execution normalization,
- driver contracts.

---

### 7.4 Knowledge Base

The Knowledge Base stores reusable execution intelligence.

Current implemented APIs:

- `UpsertRecord`
- `BatchUpsertRecords`
- `QueryRecords`
- `GetRecord`

Target capabilities:

- circuit reuse,
- optimization reuse,
- execution analytics,
- adaptive scheduling intelligence.

---

### 7.5 Hardware Optimizer

Future runtime optimization subsystem.

Target responsibilities:

- qubit placement,
- routing optimization,
- topology-aware transformations,
- backend-specific scheduling optimization.

Planned implementation:

```text
Graph Neural Networks (GNN)
```

---

## 8. Level 4 — Hardware Abstraction Layer

### 8.1 QDriver API

The QDriver API standardizes backend integrations.

#### Core Driver Responsibilities

| **Method** | **Purpose** |
|---|---|
| initialize | Driver startup |
| get_devices | Capability discovery |
| execute_circuit | Execution |
| get_device_status | Health monitoring |
| calibrate_device | Calibration hooks |

---

### 8.2 Supported Backend Categories

#### Current MVP Baseline

Implemented:

- simulator backends,
- Qiskit Aer integration path,
- local execution flows.

#### Planned Extensions

- IBM Quantum
- AWS Braket
- IonQ
- Rigetti
- photonic systems
- trapped-ion systems

---

## 9. Service Topology

### 9.1 Runtime Services

| **Service** | **Language** | **Role** |
|---|---|---|
| system-api | Python | Public ingress |
| eigen-kernel | Rust | Runtime orchestration |
| eigen-compiler | Python | Compilation |
| driver-manager | Python | Backend execution |

---

### 9.2 Mandatory Communication Paths

```text
Client
  ↓
System API
  ↓
Kernel
  ├── Compiler
  ├── Driver Manager
  └── QFS
```

#### Runtime Flow

```text
Submit
→ Validate
→ Enqueue
→ Compile
→ Execute
→ Persist
→ Retrieve
```

---

## 10. Key Data Models

### 10.1 JobSpec

Canonical user workload description.

#### Structure

```yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
spec:
```

#### Contains

- program source,
- target backend,
- compiler options,
- execution metadata,
- runtime parameters.

---

### 10.2 CircuitPayload

Execution-ready transport wrapper.

Contains:

- AQO bytes,
- format enum,
- metadata,
- execution options.

---

## 10.3 ExecutionResult

Normalized backend output.

#### Canonical Contents

- counts,
- execution metadata,
- timing,
- backend identifiers.

---

### 10.4 JobResults

User-facing final result envelope.

May contain:

- normalized results,
- AQO references,
- QASM references,
- logs,
- manifests,
- metrics.

---

## 11. Observability Architecture

### 11.1 Trace Propagation

Eigen OS uses W3C TraceContext.

Propagation key:

```text
traceparent
```

The trace context propagates through:

```text
Client
→ System API
→ Kernel
→ Compiler
→ Driver Manager
→ Backend
```

---

### 11.2 Metrics

All services expose:

```text
/metrics
```

Primary telemetry stack:

| **Component** | **Technology** |
|---|---|
| Metrics | Prometheus |
| Dashboards | Grafana |
| Tracing | OpenTelemetry |
| Logs | Structured JSON |

---

### 11.3 Correlation Requirements

All logs and traces must include:

- `trace_id`
- `job_id`
- `service_name`

Optional:

- `device_id`
- `backend_id`

---

## 12. Security Model

### 12.1 Public Boundary

Only `system-api` is externally reachable.

Internal services are network-restricted.

---

### 12.2 Compilation Safety

User code execution on the server is prohibited.

The compiler:

- parses AST,
- validates syntax,
- transforms declarative structures,
- rejects unsafe constructs.

---

### 12.3 Auth Model

Current MVP baseline:

- interceptor-based auth,
- metadata propagation,
- internal claims forwarding.

Advanced multi-provider auth remains a future extension.

---

## 13. Technology Stack

| **Area** | **Technology** |
|---|---|
| Kernel | Rust |
| Runtime Services | Python 3.12+ |
| RPC | gRPC + Protocol Buffers |
| Persistence | SQLite + MinIO/S3 |
| Serialization | JSON / Parquet |
| Observability | Prometheus / Grafana / OTel |
| Containers | Docker / Kubernetes |
| Python Packaging | Poetry |
| Rust Packaging | Cargo |

---

## 14. MVP Scope

The MVP guarantees:

- end-to-end job execution,
- deterministic AQO generation,
- simulator execution,
- artifact persistence,
- observability,
- gRPC public API,
- runtime orchestration.

### MVP Success Criterion

```bash
eigen-cli submit --job job.yaml
```

must execute a complete hybrid workflow on a simulator and return normalized results.

---

## 15. Post-MVP Extensions Already Reflected in Architecture

The architecture already includes forward-compatible contracts for:

- Knowledge Base APIs,
- dispatch rationale APIs,
- device detail APIs,
- hybrid loop orchestration,
- advanced scheduling hooks,
- optimizer integration,
- distributed orchestration,
- hardware-aware compilation.

These extensions are additive and do not invalidate MVP contracts.

---

## 16. Architectural Invariants

The following invariants are mandatory.

### 16.1 Abstraction Invariant

Programs execute across compatible backends without source modification.

### 16.2 Safety Invariant

User code is never executed server-side.

### 16.3 Determinism Invariant

Compilation outputs are deterministic.

### 16.4 Observability Invariant

All runtime flows expose metrics, logs, and traces with correlation IDs.

### 16.5 Security Invariant

System API is the sole public ingress.

### 16.6 Extensibility Invariant

Drivers and compilers can be added without modifying kernel core logic.

---

## 17. Acceptance Criteria

The architecture is considered MVP-complete when:

| **Criterion** | **Target** |
|---|---|
| End-to-end execution | Functional |
| Deterministic AQO | Enforced |
| Simulator support | Functional |
| Public gRPC API | Stable |
| Observability | JSON / Functional |
| Artifact persistence | Functional |
| Runtime orchestration | Functional |

---

## 18. Compatibility Policy

### 18.1 API Compatibility

Breaking changes require:

- new package version,
- parallel support window,
- migration documentation.

---

### 18.2 Protobuf Governance

Proto contracts must pass:

```text
buf lint
buf breaking
```

before merge.

---

## 19. Final Architectural Position

Eigen OS MVP is defined as:

- a deterministic hybrid quantum runtime,
- based on stable service contracts,
- with strict orchestration boundaries,
- simulator-first execution,
- extensible backend abstraction,
- artifact persistence,
- observable runtime execution,
- future-compatible distributed architecture.

This document is the authoritative architectural baseline for implementation alignment and future extension governance.
