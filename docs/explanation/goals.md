# Goals

## Overview

TThe primary goal of **Eigen OS** is to become the **contract-first abstraction and orchestration layer** that transforms heterogeneous quantum hardware resources into a unified, predictable, and auditable hybrid quantum-classical execution environment.

Eigen OS is not “just a scheduler”. It is the system boundary that provides:

- stable public APIs (System API),
- deterministic compilation (Eigen Compiler),
- normalized execution across heterogeneous backends (Driver Manager + QDriver),
- durable artifact persistence and lineage (QFS),
- orchestration and lifecycle semantics (Kernel/QRTX),
- security and isolation controls (Security & Isolation),
- observability by default (metrics/logs/traces),
- forward-compatible foundations for adaptive optimization (HWE / GNN Optimizer / Knowledge Base / Neuro-Symbolic Core).

A core invariant across all goals: **baseline execution remains deterministic and replay-safe**, and adaptive/intelligent layers are strictly **advisory** unless explicitly enabled by policy.

---

## Level 1: Fundamental Goals

These goals address fragmentation, safety, determinism, and basic operability.

### 1. Unify access to heterogeneous quantum backends

- **Problem:** Vendors and simulators expose different APIs, topologies, capabilities, and error models.
- **Solution:** Provide a unified, versioned **Driver Manager + QDriver API** boundary so that the runtime executes via a stable internal contract, independent of vendor specifics.
- **Key requirements:**
    - backend capability discovery via a normalized schema,
    - deterministic backend naming and selection rules (with stable fallback behavior),
    - normalized error mapping and result envelopes.

**Analogy:** Like device drivers in a classical OS: applications rely on stable interfaces, not vendor details.

### 2. Deterministic, auditable orchestration of hybrid workflows

- **Problem:** Hybrid algorithms (VQE/QAOA/QML) require repeated orchestration across quantum and classical steps with robust failure handling.
- **Solution:** Provide Kernel/QRTX orchestration and lifecycle semantics (async job model) with durable artifacts and observability.
- **Key requirements:**
    - canonical lifecycle states: `PENDING → COMPILING → QUEUED → RUNNING → DONE | ERROR | CANCELLED`,
    - deterministic compilation outputs (no server-side user code execution),
    - durable artifacts and references via QFS,
    - normalized error model and replay-safe audit artifacts.

> Note: **General DAG scheduling and fully kernel-managed hybrid loops are post-MVP targets**. MVP guarantees a stable async job lifecycle and supports external orchestration loops.

---

## Level 2: Optimization Goals

These goals aim to maximize useful output from scarce and unstable quantum resources without breaking determinism and auditability.

### 3. Policy-driven scheduling and resource governance

- **Problem:** Capacity is limited; fairness, quotas, and placement policies are required for production behavior.
- **Solution:** Introduce deterministic, policy-driven orchestration primitives:
    - queue visibility and scheduling telemetry,
    - quota/fairness enforcement,
    - reservation and allocation lifecycle (Resource Manager),
    - replay-safe scheduling decisions with audit trails.

**Contract requirement:** scheduling/placement decisions must remain **deterministic under identical inputs**, and all decisions must be **auditable**.

### 4. 4. End-to-end optimization from program → IR → hardware mapping (advisory-by-default)

- **Problem:** Compiler-only optimization is insufficient; execution quality depends on topology, calibration, and routing.
- **Solution:** Provide an **advisory optimization stack**:
    - deterministic compiler baseline (AST-only → AQO),
    - optional Knowledge Base reuse (deterministic, versioned),
    - optional GNN-based placement/routing (with deterministic fallback),
    - hardware workflow orchestration and adaptation (HWE).

**Hard constraint:** intelligent layers MUST NOT override correctness, safety, or determinism guarantees. They must degrade to deterministic baseline behavior when unavailable or low-confidence.

---

## Level 3: Strategic Goals

These goals define the long-term platform direction.

### 5. Make “quantum execution” a first-class managed runtime capability

- **Goal:** Provide process-like operational control for quantum execution where technically feasible:
    - structured execution sessions,
    - robust cancellation and retry semantics,
    - replay evidence and lineage,
    - future: checkpointing / state persistence (QFS Level-2/Level-1 concepts) where hardware supports it.

**Clarification:** Full suspend/resume and migration of *live quantum state* is not an MVP promise and may be hardware-limited.

### 6. Establish a standardized ecosystem and contract topology

- **Goal:** Become for quantum/hybrid workloads what stable OS contracts are for classical systems:
    - stable public API namespace (`eigen.api.v1`),
    - stable internal contracts (`eigen.internal.v1`),
    - strong compatibility discipline (SemVer-style),
    - vendor drivers integrated behind stable abstractions,
    - repeatable operational practices (dashboards, alerts, runbooks, CI conformance).

---

## How these goals map to Eigen OS components

| **Goal** | **Primary modules** | **Example Functionality** |
|-------------------|-------------------|-------------------|
| 1. Unify access | Driver Manager, QDriver, DeviceService | `ExecuteCircuit` normalized across simulator/QPU backends |
| 2. Deterministic orchestration | Kernel/QRTX, System API, QFS, Compiler | async lifecycle + deterministic compilation + durable artifacts |
| 3. Governance & scheduling | Resource Manager, Scheduler/QRTX, Orchestration Observability | quotas/fairness + queue health + replay-safe decisions |
| 4. End-to-end optimization | Compiler, HWE, GNN Optimizer, Knowledge Base, NSC | advisory placement/routing + deterministic fallback + explainability |
| 5. First-class execution | QRTX, QFS L2/L1 (future), Security module | session control, replay evidence, future stateful runtime concepts |
| 6. Ecosystem | Public APIs & SDKs, contracts, CI conformance | stable SDK/CLI, contract-map, dashboards/alerts, compatibility gates |

## Evolution path

### Phase 0 / MVP (baseline contract)

MVP focuses on a complete, stable, deterministic pipeline:

- **E2E job execution** (Submit → Compile → Execute → Persist → Retrieve).
- **Unified API:** stable gRPC for job/device management (REST parity is a target, not an MVP guarantee).
- **Deterministic compilation:** Eigen-Lang subset compiled via AST-only processing into AQO (no user code execution server-side).
- **Hardware abstraction:** Driver Manager + simulator backend(s); plugin-friendly architecture for future QPU drivers.
- **Security baseline:** authentication + coarse RBAC + payload limits + validated inputs.
- **Observability baseline:** metrics + structured logs + trace propagation.
- **Artifacts & lineage:** QFS references for compiled artifacts and results.

#### Measurable MVP success criterion:

```bash
eigen-cli submit --job job.yaml
```

must result in a successful async job lifecycle and a retrievable persisted result artifact.

---

### Phase 1 (hardening + orchestration maturity)

- resource allocation semantics (reservation lifecycle, queue visibility),
- orchestration observability contract completion (alerts/dashboards/CI),
- standardized metadata schemas across drivers,
- multi-device execution foundations (split/merge artifacts, retry-safe shard semantics),
- deterministic replay bundles and lineage indexing foundations.

---

### Phase 2+ (adaptive intelligence, advisory-by-default)

- HWE as a centralized hardware workflow engine,
- GNN optimizer serving + deterministic fallbacks,
- Knowledge Base retrieval and replay-safe reuse,
- Neuro-Symbolic Core (bounded intelligence) with explainability and governance,
- hardware telemetry standardization (calibration/noise/topology snapshots) with policy control.

---

## MVP goals and non-goals

### MVP goals (Phase 0)

- **E2E async runtime:** submit/status/results with stable lifecycle semantics.
- **Deterministic compilation:** Eigen-Lang → AQO without executing user code.
- **Backend abstraction:** normalized execution via Driver Manager with at least one simulator backend.
- **Durable artifacts:** QFS persistence and references for compiled artifacts and results.
- **Security baseline:** auth + RBAC + input validation + payload limits.
- **Observability baseline:** metrics, logs, and trace propagation across core services.

---

### MVP non-goals (explicit)

- advanced noise-adaptive scheduling and real-time topology-aware rerouting,
- production multi-tenant quotas/fairness with full reservation enforcement,
- generalized kernel-managed hybrid DAG execution,
- live qubit/session lifecycle (QFS Level-1) and state persistence (QFS Level-2),
- high availability / multi-region replication guarantees,
- full OIDC federation and complex enterprise auth flows (beyond baseline modes),
- production GNN optimizer/NSC/Knowledge Base in the execution path.

---

## Core thesis

Eigen OS aims to make quantum/hybrid execution as routine and operable as managed classical compute:

A user submits a workload via stable APIs; the system deterministically compiles, orchestrates, executes on heterogeneous backends through normalized drivers, persists auditable artifacts, and exposes observable, replay-safe operational behavior—while allowing future adaptive intelligence as a strictly governed, explainable, policy-controlled extension.
