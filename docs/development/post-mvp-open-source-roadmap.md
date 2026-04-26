# Eigen-OS Post-MVP Open-Source Development Plan

## 1. Vision

Eigen-OS is positioned as the execution and orchestration layer between quantum SDKs (for example, Qiskit and Cirq) and compute backends (simulators and quantum hardware).

In the modern quantum software stack, responsibilities are already split into layers:

- SDK / programming layer
- Compiler
- Execution/runtime
- Hardware

Eigen-OS targets the runtime + orchestration + execution layer.

A useful analogy:

- Kubernetes for container orchestration
- Ray for distributed task orchestration

In the quantum context, orchestration is critical because hybrid quantum-classical workloads require strong coordination, scheduling, and observability.

## 2. Current State (MVP)

MVP is complete and delivers end-to-end execution flow on a simulator backend.

Implemented capabilities:

- Contract-first architecture (gRPC + protobuf)
- Kernel (QRTX) with lifecycle handling
- Compiler pipeline (AST -> IR)
- DriverManager + SimulatorDriver
- QFS storage layer
- CLI
- Observability baseline (metrics + tracing)
- E2E job execution through simulator

## 3. Strategic Direction

Primary direction: evolve Eigen-OS into a cloud-native runtime for hybrid quantum-classical workloads.

Why this path is strong:

- Cloud execution is a dominant operational model in quantum platforms
- Runtime abstraction reduces direct backend complexity for application teams
- Orchestration is still an underdeveloped layer in the ecosystem

## 4. Roadmap Overview

- **Phase 1: Production Runtime** — deliver practical utility beyond simulation-only workflows
- **Phase 2: Orchestration Layer** — introduce robust resource and execution management
- **Phase 3: Benchmarking Platform** — add strong analytical and research capabilities
- **Phase 4: Intelligent Runtime** — introduce data-driven runtime optimization

## 5. Phase 1 — Production Runtime

Goal: make Eigen-OS suitable for real-world usage and hardware-connected execution.

Implementation plan: [`phase-1-production-runtime.md`](phase-1-production-runtime.md) and RFC [`../../rfcs/0019-phase1-production-runtime-plan.md`](../../rfcs/0019-phase1-production-runtime-plan.md).

Key workstreams:

1. **Hardware drivers**
   - Integrate with Qiskit Runtime / IBM backends
   - Support external backend connectivity through a stable driver interface
2. **Fault tolerance**
   - Expand retry policy coverage
   - Implement timeout handling and cancellation hygiene
   - Harden behavior for backend-side errors and transient failures
3. **Storage upgrade**
   - Move from local QFS assumptions toward object-storage-compatible design (S3-like)
   - Add result versioning and durable artifact conventions
4. **Observability v2**
   - Per-job timeline visibility
   - Latency breakdown by pipeline stage
   - Better tracing visualization and correlation

Expected outcome:

- Real quantum job execution support
- Production-ready execution path
- First practical open-source utility for external users

## 6. Phase 2 — Orchestration Layer

Goal: turn Eigen-OS into a full workload orchestrator.

Key workstreams:

1. **Scheduler core**
   - Priority queue support
   - Quotas and basic fairness policies
2. **Device-aware execution**
   - Backend selection based on qubit availability, latency, and device availability
3. **Multi-device execution**
   - Execute one logical workload across multiple backends where appropriate
4. **Batch execution**
   - Group compatible jobs
   - Improve throughput and backend utilization

Expected outcome:

- Eigen-OS becomes a Kubernetes-like orchestrator for quantum workloads

## 7. Phase 3 — Benchmarking Platform

Goal: add reproducible analytics and research value.

Key workstreams:

1. **Benchmark system**
   - Integrate QSBench-style datasets
   - Compare backend behavior with reproducible methodology
2. **Experiment tracking**
   - Execution history and metadata registry
   - Side-by-side run/result comparison
3. **Compiler optimization loop**
   - Circuit optimization improvements
   - Strategy-level transpilation analysis

Expected outcome:

- Eigen-OS becomes a research and benchmarking platform in addition to runtime infrastructure

## 8. Phase 4 — Intelligent Runtime

Goal: introduce an intelligent orchestration and optimization layer.

Key workstreams:

1. **Automatic backend selection**
   - ML-based backend choice from historical and live signals
2. **Adaptive scheduling**
   - Learning-based scheduling policies
3. **Optimization models**
   - Use benchmark datasets to predict latency and fidelity outcomes

Expected outcome:

- AI-assisted quantum runtime behavior with data-informed decisions

## 9. Open-Source Strategy

Core open components:

- Execution engine
- Scheduler (baseline)
- Driver interface
- CLI

Plugin-oriented extension areas:

- Hardware drivers
- Compiler backends
- Optimizers

Guiding principle: keep the execution/orchestration core modular, transparent, and contribution-friendly, while enabling extension through well-defined interfaces.

## 10. Key Risks and Mitigations

1. **Limited early adoption**
   - Mitigation: prioritize developer experience, quickstart reliability, and real backend demos
2. **Premature intelligence layer complexity**
   - Mitigation: defer advanced ML/runtime intelligence until benchmark and telemetry foundations are mature
3. **System complexity growth**
   - Mitigation: preserve a simple UX contract and stable APIs while adding orchestration depth incrementally

## 11. Immediate Open-Source Next Steps

- Add Qiskit driver integration path
- Validate end-to-end execution on a real backend
- Introduce baseline scheduler capabilities
- Improve observability depth (timeline + stage latency visibility)

## 12. Long-Term Positioning

Eigen-OS is positioned as the execution and orchestration layer for quantum computing workloads.
