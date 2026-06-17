# Eigen OS Architecture Overview

- **Document status:** Normative MVP Architecture Specification  
- **Architecture version:** `1.0.0 ` 
- **Last updated:** 2026-05-24  
- **Audience:** Core developers, infrastructure engineers, compiler/runtime contributors, driver authors  
- **Related documents:**
  - `architecture/contract-map.md`
  - `architecture/data-flow.md`
  - `reference/jobspec.md`
  - `reference/error-model.md`
  - `reference/api/grpc-public.md`
  - `reference/api/grpc-internal.md`

---

## 1. Introduction

### 1.1 Purpose

Eigen OS is a modular hybrid quantum–classical operating environment for orchestrating compilation, scheduling, execution, and result management of quantum workloads across heterogeneous backends.

Eigen OS provides:

- a stable high-level programming model,
- deterministic compilation contracts,
- runtime orchestration and scheduling,
- backend abstraction via drivers,
- artifact persistence via QFS (CircuitFS),
- observability and traceability,
- extensible compiler/runtime/driver infrastructure.

This document defines the canonical architectural structure of the Eigen OS MVP and the accepted forward-compatible extensions already reflected in the repository and contracts.

---

## 2. System vision

Eigen OS abstracts unstable and vendor-specific quantum infrastructure behind stable contracts and orchestration layers. The platform is designed to allow users to execute hybrid quantum–classical workflows without requiring direct interaction with:

- low-level qubit topology,
- vendor SDK internals,
- hardware routing constraints,
- pulse-level execution,
- backend-specific compilation and execution pipelines.

---

## 3. Architectural principles

### 3.1 Hybrid-first execution

Eigen OS is designed primarily for hybrid workloads combining:

- classical optimization,
- quantum execution,
- iterative parameter refinement,
- distributed orchestration.

Variational algorithms (VQE, QAOA, hybrid ML workloads) are first-class architectural targets.

---

### 3.2 Stable interface boundaries

All major components communicate exclusively through versioned contracts.

Primary interface categories:

| Boundary | Contract |
|---|---|
| Client ↔ System API | `eigen.api.v1` (public gRPC), plus selected REST endpoints (see §5.3) |
| System API ↔ Kernel | `eigen.internal.v1` (internal gRPC) |
| Kernel ↔ Compiler | `eigen.internal.v1` (internal gRPC) |
| Kernel ↔ Driver Manager | `eigen.internal.v1` (internal gRPC) |
| Driver ↔ Backend | vendor SDK / REST / gRPC (provider-specific; normalized by Driver Manager) |

Internal implementation changes MUST NOT break external contracts.

---

### 3.3 Deterministic compilation

Compilation is deterministic.

Identical inputs:

- source,
- compiler options,
- target metadata,
- referenced artifacts

The compiler also resolves a workload-family profile from the normalized workload contract before lowering. That profile becomes part of compiler metadata and can change validation and lowering decisions without changing AQO's top-level schema.

MUST produce identical AQO output.

Server-side user code execution is prohibited. Compilation operates on an allowlisted Python AST subset and performs parsing/validation/transformation only.

---

### 3.4 Backend abstraction

The same Eigen-Lang program SHOULD execute on any supported backend through compatible drivers without source modification. Backend-specific optimizations must remain encapsulated within:

- compiler target passes,
- driver translation layers,
- runtime scheduling logic.

---

### 3.5 Observability by default

All runtime stages expose:

- metrics,
- structured logs,
- traces,
- correlation identifiers.

Minimum required correlation identifiers:

- `trace_id` (trace context),
- `job_id` (workload identity),
- `device_id` / `backend_id` (when applicable).

Trace propagation is W3C TraceContext (`traceparent`) across all service boundaries.

---

### 3.6 Modular extensibility

The architecture supports independent evolution of:

- compilers,
- optimizers,
- schedulers,
- drivers,
- orchestration policies,
- dataset and knowledge services,
- backend integrations.

Adding a new backend driver SHOULD NOT require kernel core modifications.

---

## 4. High-level system architecture

Eigen OS is organized into four architectural layers (layered “cake” architecture):

```text
┌────────────────────────────────────────────┐
│ Level 1 — Abstraction Layer               │
│ Eigen-Lang / SDK / CLI / System API       │
└────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│ Level 2 — Kernel Layer                    │
│ Kernel (QRTX) / Scheduling / QFS / State  │
└────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│ Level 3 — Runtime Services                │
│ Compiler / Driver Manager / KB / Data     │
│ (optional) Optimizers, Learning services  │
└────────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│ Level 4 — Hardware Abstraction Layer      │
│ Drivers / Simulators / Quantum Hardware   │
└────────────────────────────────────────────┘
```

---

## 5. Level 1 — Abstraction layer

### 5.1 Eigen-Lang

Eigen-Lang is the high-level hybrid DSL of Eigen OS.

MVP baseline:

- Python-based syntax (`.eigen.py`),
- AST-only compilation (no user code execution),
- deterministic transformation pipeline,
- symbolic parameter support,
- compiler allowlist enforcement for imports and AST nodes.

Conceptual primitives (language-level, not necessarily all implemented end-to-end in MVP):

| Category | Examples |
|---|---|
| Quantum types | `QubitRegister`, `Observable`, `Ansatz` |
| Decorators | `@hybrid_program`, `@cost_function` |
| Hybrid constructs | `ExpectationValue`, `minimize()` |
| Templates | `create_hea_ansatz()` |
| Utilities | `visualize_circuit()` |

Authoritative language contract: `reference/eigen-lang.md`.

---

### 5.2 SDK and CLI

The CLI and SDK provide user-facing interfaces and packaging.

Representative CLI commands:

| Command | Purpose |
|---|---|
| `eigen submit` | Submit jobs |
| `eigen status` | Query state |
| `eigen results` | Retrieve results |
| `eigen devices` | Query backend catalog |

The CLI packages user assets into `SubmitJobRequest` and is responsible for deterministic packaging and hashing rules defined by JobSpec.

---

### 5.3 System API

The System API is the only public ingress to the runtime.

Responsibilities:

- authentication and authorization,
- request validation and normalization, including feature-payload minimization before internal service dispatch,
- routing to internal services,
- trace propagation and observability boundary,
- external API compatibility (public contract governance).

#### Public APIs

- **Primary public interface:** gRPC, package `eigen.api.v1` (stable at v1.0.0).
- **Selected REST endpoints:** used for targeted workflows and tooling where HTTP/JSON is preferred. Examples include:
  - `POST /benchmarks/run` (benchmark run creation)
  - `POST /explain/backend-selection` (explainability for backend selection)

REST endpoints are versioned and must follow the same error and observability policies as gRPC.

---

## 6. Level 2 — Kernel layer

### 6.1 Kernel (QRTX)

The Eigen Kernel is the orchestration core and the single source of truth for runtime state.

Primary responsibilities:

- job lifecycle state machine,
- orchestration and scheduling,
- coordinating compilation and execution,
- artifact persistence coordination (QFS),
- retries and cancellation semantics,
- durable error visibility for async failures.

Implementation language: Rust.

---

### 6.2 Runtime state machine

Canonical client-visible states:

```text
PENDING
→ COMPILING
→ QUEUED
→ RUNNING
→ DONE | ERROR | CANCELLED
```

The kernel is the authoritative owner of lifecycle state. System API and SDKs MUST NOT invent or reinterpret lifecycle states.

---

### 6.3 Scheduling model

MVP scheduler characteristics:

- queue-based,
- deterministic and simulator-first,
- backend-aware via Driver Manager capabilities.

Forward-compatible extension points:

- policy-driven routing (`balanced`, `latency`, `cost`, `availability`, `deterministic`, `compliance`),
- intelligent backend scoring and explainability,
- multi-device execution (split/merge),
- adaptive retry policies and fairness/quota enforcement.

---

### 6.4 QFS (CircuitFS) — artifact persistence

QFS is the canonical persistence layer for:

- JobSpec (`job.yaml`) and submission bundles,
- source programs,
- compiled artifacts (AQO/QASM),
- execution results,
- logs,
- manifests and checksums,
- durable error artifacts for async failures,
- lineage and replay artifacts (when applicable).

Storage backends (deployment dependent):

- SQLite (metadata/indexing),
- MinIO / S3-compatible object storage (artifact payloads),
- alternative backends are allowed if they preserve QFS semantics.

Authoritative artifact layout contract: `reference/formats/qfs-layout.md`.

---

## 7. Level 3 — runtime services

### 7.1 Compiler service

Implementation language: Python.

Responsibilities:

- parse and validate Eigen-Lang source (AST allowlist),
- deterministic lowering,
- AQO generation (canonical IR),
- optional QASM export,
- compiler metadata and diagnostics.

Compilation pipeline:

```text
Eigen-Lang Source
→ AST
→ Validation
→ Transformation
→ AQO (+ optional QASM)
→ Persist to QFS
```

---

### 7.2 AQO (Abstract Quantum Operations)

AQO is the canonical intermediate representation exchanged between compiler and runtime.

Properties:

- backend-independent,
- deterministic,
- serializable,
- supports symbolic parameters.

Authoritative AQO contract: `reference/formats/aqo.md`.

---

### 7.3 Driver Manager

The Driver Manager abstracts backend execution.

Responsibilities:

- driver lifecycle and capability discovery,
- payload translation to vendor formats,
- execution dispatch,
- result normalization,
- backend/provider error normalization per the Error Model.

---

### 7.4 Knowledge Base

The Knowledge Base (KB) stores reusable execution intelligence and records used by the platform and developer tooling.

KB-facing APIs now live in `neuro-symbolic-service` and are no longer owned by `system-api`.

Target capabilities:

- circuit and artifact reuse,
- optimization reuse,
- analytics and trace-backed auditability,
- future integration with intelligent scheduling.

---

### 7.5 Dataset pipeline and learning services (forward-compatible)

Eigen OS architecture includes forward-compatible services for:

- dataset ingestion and caching (Dataset Pipeline),
- continuous learning signals and model refresh,
- optimizer integration (e.g., GNN optimizer).

These are not required for MVP end-to-end execution but are included as architectural extension points.

---

## 8. Level 4 — hardware abstraction layer

### 8.1 QDriver API

The QDriver API standardizes backend integrations.

Core driver responsibilities:

| Method | Purpose |
|---|---|
| `initialize` | Driver startup |
| `get_devices` | Capability discovery |
| `execute_circuit` | Execution |
| `get_device_status` | Health monitoring |
| `calibrate_device` | Calibration hooks |

---

### 8.2 Supported backend categories

MVP baseline:

- simulator backends,
- local execution profiles.

Planned extensions (provider dependent):

- major vendor QPUs,
- cloud provider orchestration backends,
- additional simulator engines.

---

## 9. Service topology

### 9.1 Runtime services

| Service | Language | Role |
|---|---|---|
| `system-api` | Python | Public ingress (gRPC + selected REST) |
| `eigen-kernel` (QRTX) | Rust | Orchestration, scheduling, lifecycle |
| `eigen-compiler` | Python | Compilation to AQO/QASM |
| `driver-manager` | Python | Backend execution and normalization |

---

### 9.2 Mandatory communication paths

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

Runtime flow:

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

## 10. Key data models

### 10.1 JobSpec (`job.yaml`)

Canonical user workload descriptor.

Contract version (JobSpec API version):

```yaml
apiVersion: eigen.os/v1
kind: QuantumJob
```

JobSpec defines:

- program source (file/inline/URI – per contract),
- target backend/routing policy,
- compiler options,
- runtime parameters,
- observability and security policy,
- artifact retention rules.

Authoritative contract: `reference/jobspec.md`.

---

### 10.2 CircuitPayload

Execution-ready transport wrapper between kernel and driver.

Contains:

- payload format enum (AQO JSON / AQO protobuf / QASM where supported),
- payload bytes or references,
- shots and execution options,
- metadata and provenance identifiers.

---

### 10.3 ExecutionResult

Normalized backend output.

Canonical contents:

- counts (canonical bit ordering),
- execution timing,
- backend identifiers,
- structured metadata.

---

### 10.4 JobResults

User-facing result envelope.

May contain:

- normalized results,
- QFS references to artifacts (AQO/QASM/results/logs),
- manifests and checksums,
- durable error references when failed.

---

## 11. Observability architecture

### 11.1 Trace propagation

Eigen OS uses W3C TraceContext.

Propagation header/key:

```text
traceparent
```

Trace context propagates through:

```text
Client
→ System API
→ Kernel
→ Compiler
→ Driver Manager
→ Backend (where supported)
```

---

### 11.2 Metrics

All services expose Prometheus metrics via `/metrics`.

Primary telemetry stack:

| Component | Technology |
|---|---|
| Metrics | Prometheus |
| Dashboards | Grafana |
| Tracing | OpenTelemetry |
| Logs | Structured JSON |

Observability contracts are versioned and maintained as stable public operational surfaces (see the observability contract documents in `docs/reference/`).

---

### 11.3 Correlation requirements

Logs and traces MUST include:

- `trace_id`,
- `job_id`,
- `service_name`.

When applicable:

- `device_id` / `backend_id`.

Metrics MUST obey bounded-cardinality rules (no `job_id`/`trace_id` labels).

---

## 12. Security model

### 12.1 Public boundary

Only `system-api` is externally reachable. Internal services are network-restricted and communicate over authenticated channels.

### 12.2 Transport security

- All external and internal RPC/HTTP calls MUST use TLS 1.3.
- Internal service-to-service communication SHOULD use mutual TLS (mTLS) and service identity propagation.

### 12.3 Authentication and authorization

- External clients authenticate via OAuth2/JWT tokens (or client mTLS where applicable).
- System API enforces authz (scopes/RBAC) per method.
- Identity and tenant context is propagated to internal services via metadata.

### 12.4 Compilation safety

User code execution on the server is prohibited. The compiler:

- parses AST,
- validates allowlisted constructs,
- rejects unsafe imports and dynamic execution,
- applies resource limits where required.

---

## 13. Technology stack

| Area | Technology |
|---|---|
| Kernel | Rust |
| Runtime services | Python 3.12+ |
| RPC | gRPC + Protocol Buffers |
| REST | HTTP/JSON (selected endpoints) |
| Persistence | SQLite + MinIO/S3 |
| Serialization | JSON / Parquet |
| Observability | Prometheus / Grafana / OpenTelemetry |
| Containers | Docker / Kubernetes |
| Python packaging | Poetry |
| Rust packaging | Cargo |

---

## 14. MVP scope

The MVP guarantees:

- end-to-end job execution,
- deterministic AQO generation,
- simulator execution,
- artifact persistence via QFS,
- observability foundations (metrics/tracing/logging),
- stable public gRPC API (`eigen.api.v1`),
- kernel-managed runtime orchestration.

### MVP success criterion

```bash
eigen submit --job job.yaml
```

MUST execute an end-to-end workload on a simulator and return normalized results (and QFS artifact references).

---

## 15. Post-MVP extensions already reflected in architecture/contracts

The architecture includes forward-compatible contracts and/or partial implementations for:

- Knowledge Base APIs,
- dispatch rationale and explainability,
- device details and reservation,
- intelligent scheduling hooks,
- distributed orchestration and multi-device split/merge,
- optimizer integration hooks,
- benchmark execution contracts,
- cluster runtime observability contracts.

These extensions are additive and do not invalidate MVP contracts.

---

## 16. Architectural invariants

The following invariants are mandatory:

1. **Abstraction:** Programs execute across compatible backends without source modification.
2. **Safety:** User code is never executed server-side.
3. **Determinism:** Compilation outputs are deterministic.
4. **Observability:** Runtime flows expose metrics, logs, and traces with correlation IDs.
5. **Security:** System API is the sole public ingress; internal comms are secured.
6. **Extensibility:** Drivers and services can be added without modifying kernel core logic.
7. **Contract governance:** Public API and format contracts evolve under SemVer discipline.

---

## 17. Acceptance criteria

The architecture is considered MVP-complete when:

| Criterion | Target |
|---|---|
| End-to-end execution | Functional |
| Deterministic AQO | Enforced |
| Simulator support | Functional |
| Public gRPC API | Stable |
| Observability foundations | Functional |
| Artifact persistence (QFS) | Functional |
| Runtime orchestration | Functional |

---

## 18. Compatibility policy

### 18.1 API compatibility

Breaking changes require:

- new package version (`eigen.api.v2`, etc.),
- parallel support window (where feasible),
- migration documentation.

### 18.2 Protobuf governance

Proto contracts MUST pass:

```text
buf lint
buf breaking
```

before merge.

---

## 19. Final architectural position

Eigen OS MVP is:

- a deterministic hybrid quantum runtime,
- based on stable service contracts,
- with strict orchestration boundaries,
- simulator-first execution,
- extensible backend abstraction,
- artifact persistence (QFS),
- observable runtime execution,
- future-compatible distributed architecture.

This document is the authoritative architectural baseline for implementation alignment and future extension governance.
