# Mission & Philosophy

## Core thesis

**Eigen OS** is not merely a task scheduler. It is a **contract-first semantic bridge** between human intent and heterogeneous quantum execution substrates.

Its mission is to make quantum computing:

- **Programmable** — through a stable programming and API model.
- **Deterministic and auditable** — through replay-safe orchestration, lineage, and artifact persistence.
- **Accessible** — by hiding vendor instability behind stable interfaces.
- **Composable** — so workflows integrate into research and production automation systems.
- **Extensible** — so new backends and optimization capabilities can be added without breaking the core.

Eigen OS always preserves a **deterministic baseline execution path**. Adaptive or “intelligent” layers may recommend optimizations, but **must not override safety, correctness, or replay guarantees** unless explicitly enabled by policy, and must always degrade safely.

---

## Philosophy by audience

### For researchers

Describe your workload in a domain-oriented form (Eigen-Lang / JobSpec), submit it via stable APIs, and rely on Eigen OS to:

- compile deterministically,
- execute across compatible backends,
- return normalized results,
- persist artifacts for reproducibility.

---

### For hardware providers

Eigen OS acts as the normalization boundary that:

- abstracts vendor-specific transports and SDKs behind QDriver/Driver Manager,
- isolates failures from user-facing semantics,
- enables capability discovery and stable execution envelopes.

---

### For the community

Eigen OS is designed around explicit boundaries:

- stable public APIs,
- versioned internal contracts,
- modular drivers and services,
- contract-governed evolution.

---

## Architectural principles

### Hybrid-first execution

Eigen OS is designed for hybrid quantum-classical workflows (VQE/QAOA/QML) with:

- async orchestration semantics,
- durable artifacts and lineage,
- external-loop orchestration as the stable MVP path,
- forward-compatible foundations for kernel-managed loops.

---

### Abstraction through interfaces

Heterogeneous backends are unified through:

- **Driver Manager + QDriver** internal abstraction,
- stable public API surface (System API),
- contract-governed lifecycle and error semantics.

---

### Determinism and replay-safety by default

The system is designed so that:

- compilation is deterministic (AST-only; no server-side user code execution),
- orchestration decisions are auditable,
- artifacts and envelopes preserve replay evidence,
- intelligent/adaptive systems are bounded and policy-controlled.

---

### Bounded adaptivity through neuro-symbolic methods

Neuro-symbolic components (Neuro-Symbolic Core, GNN Optimizer, Knowledge Base, HWE) are **advisory unless enabled**, and must:

- produce explainability metadata,
- provide deterministic modes and fallbacks,
- never bypass symbolic validation or policy enforcement.

---

### Open modularity

Components are isolated by clear APIs and contracts. The system should be evolvable by:

- adding drivers without kernel rewrites,
- adding compiler targets and optimizer stages without changing the public API,
- extending telemetry/observability without breaking metric compatibility.

---

### Layered architecture

```text
Application & Client Layer
  ├─ CLI / SDKs
  └─ Automation/Integrations
        ↓
Public Gateway Layer
  └─ System API (eigen.api.v1)
        ↓
Kernel Orchestration Layer
  └─ QRTX / Kernel (job lifecycle, coordination)
        ↓
Runtime Services Layer
  ├─ Compiler (deterministic AST → AQO)
  ├─ Driver Manager (normalized execution boundary)
  ├─ QFS (artifact persistence + lineage)
  └─ (future) HWE / GNN Optimizer / KB / NSC
        ↓
Hardware Abstraction Layer
  └─ QDriver implementations → vendor runtimes/simulators/hardware
```

---

### Clarification vs earlier drafts

- MVP guarantees **gRPC as primary** ingress. **REST parity** is a target capability, not a required delivered MVP behavior.
- The kernel in MVP provides **async job orchestration**, not a fully generalized DAG scheduler.
- QFS Level-2/Level-1 concepts (state store / live qubits) are **post-MVP targets**.

---

### Execution model (MVP baseline)

Eigen OS MVP is built around an async job model with stable lifecycle semantics:

```text
PENDING → COMPILING → QUEUED → RUNNING → DONE | ERROR | CANCELLED
```

Key contract constraints:

- **System API** is the sole public ingress boundary.
- **Compiler** is deterministic and AST-only.
- **Driver Manager** is the only place that touches vendor SDKs.
- **QFS** persists artifacts and provides references for large payloads.
- **Observability** (metrics/logs/traces) is present by default with correlation IDs.

---

### Technology stack

| **Component** | **Technology** | **Rationale** |
|-------------------|-------------------|-------------------|
| Kernel/QRTX | Rust | Performance, safety, deterministic orchestration core |
| Runtime services | Python 3.12+ | Rapid iteration, ecosystem integration (tooling/ML) |
| Inter-service | gRPC/Protobuf | Typed contracts, stability, performance |
| Serialization | JSON + Parquet (as needed) | Human-readable artifacts + efficient analytics |
| Persistence | SQLite + MinIO/S3-compatible | Simple deploy + durable artifacts |
| Observability | Prometheus + Grafana + OpenTelemetry | Standard telemetry stack |
| Deployment | Docker + Kubernetes | Reproducible operations |
| License | Apache 2.0 | Broad adoption and commercial compatibility |

---

## MVP vs post-MVP

### MVP (Phase 0) — Foundation (normative baseline)

MVP focuses on deterministic, end-to-end execution:

- Stable public **gRPC** API: JobService, DeviceService.
- Basic auth/authz (baseline modes + RBAC categories), request validation, payload limits.
- Deterministic **AST-only** compilation (Eigen-Lang subset → AQO).
- Driver Manager + simulator backend(s) behind QDriver-style abstraction.
- Kernel orchestration of compile/execute/persist with stable lifecycle semantics.
- QFS artifact persistence and reference-based retrieval.
- Observability baseline: metrics, structured logs, trace propagation.

#### MVP success metric:

```text
eigen-cli submit --job job.yaml
```

executes a full pipeline (submit → compile → execute → persist → retrieve) and returns normalized results.

---

### Post-MVP (Phases 1+) — Evolution (targets)

- Scheduling maturity: quotas/fairness, reservation lifecycle, deterministic queue replay.
- Multi-device execution: split/merge semantics, retry-safe shard accounting, merge policies.
- HWE for hardware-aware adaptation and deterministic failover decisions.
- GNN optimizer for placement/routing with deterministic fallback chain.
- Knowledge Base for replay-safe optimization reuse and explainability.
- Neuro-Symbolic Core for bounded intelligence with DPDA symbolic constraints, provenance, and governance.
- QFS Level-2/Level-1 concepts where hardware semantics allow it.

---

## Next steps (repo/governance aligned)

1. **Contract discipline first:** keep contracts as the source of truth (public APIs, internal contracts, observability contracts).
2. **Conformance gates:** CI validates contract stability (buf breaking, metric catalogs, envelope invariants, replay invariants).
3. **Incremental evolution:** add post-MVP intelligence only as optional, policy-controlled layers with deterministic fallbacks.
4. **Community workflow:** RFC/ADR process to evolve interfaces without destabilizing MVP guarantees.

---

## Final vision

Eigen OS is a shift from imperative “vendor hardware management” to declarative, contract-governed “computation orchestration”.

A developer describes intent; Eigen OS deterministically compiles and orchestrates execution across heterogeneous backends, persists reproducible artifacts, and exposes observable, auditable behavior—while enabling future adaptive optimization as a strictly bounded, explainable, policy-controlled extension.
