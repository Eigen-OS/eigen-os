# Eigen-OS Roadmap

## Overview

Eigen-OS is a cloud-native runtime and orchestration platform for hybrid quantum-classical workloads.

The open-source roadmap focuses on:

- execution
- orchestration
- benchmarking
- distributed runtime infrastructure
- explainable runtime intelligence
- extensibility
- developer experience

Eigen-OS evolves as:

> Runtime → Benchmarking → Intelligent Orchestration → Distributed Platform

---

## 1. Current State

### Completed

- MVP-1: Core services and contracts
- MVP-2: Compilation pipeline
- MVP-3: Execution and results retrieval
- Phase-1: Production runtime
- Phase-2: Orchestration layer
- Phase-3: Benchmarking platform
- Phase-4: Intelligent runtime
- Phase-5: Distributed execution
- Phase-6: Plugin ecosystem baseline
- Phase-7: Stability and developer experience baseline
- Phase-8A: Knowledge/optimizer/learning/checkpoint contract baseline
- Phase-8B: Runtime and data-fabric hardening

### Capabilities Today

- JobSpec-based execution model
- Deterministic compilation pipeline (AST → IR → execution artifacts)
- QRTX kernel lifecycle management
- DriverManager + simulator execution
- Baseline device-aware scheduling
- Benchmark run/compare/history APIs and CLI flow
- Observability (metrics + tracing)
- Local developer environment

---

## 2. Eigen-Lang Track

Eigen-Lang is a first-class component of Eigen-OS.

The language layer evolves in parallel with runtime and orchestration.

### Current State

- Python-based DSL
- deterministic AST-based compilation
- AQO mapping
- language versioning policy
- restricted and validated execution model

### Focus Areas

- compiler stability
- language ergonomics
- tooling
- explainability
- reusable workflow abstractions

### Guiding Rules

- RFC-first evolution
- deterministic compilation
- compatibility-aware versioning
- conformance-driven implementation

---

## 3. Phase-4: Intelligent Runtime (Completed)

### Goal

Introduce data-driven and explainable runtime decisions without opaque proprietary ML.

### Runtime Deliverables

- backend scoring module
- configurable scheduling policy engine
- explanation APIs:
  - `/explain/backend-selection`
  - `/explain/execution`

### Eigen-Lang Integrations

#### Goals

Make runtime intelligence visible and explainable at the language level.

#### Deliverables

- compile-time diagnostics
- runtime-aware compiler hints
- explainable backend selection metadata
- execution annotations in Eigen-Lang workflows
- deterministic optimization recommendations

#### Example

```python
@hybrid_program(
    target="auto",
    optimization_profile="latency"
)
def workflow():
    ...
```

Compiler/runtime may explain:

- why a backend was selected
- why scheduling changed
- why execution latency increased
- why transpilation strategy was chosen

---

## 4. Phase-5: Distributed Execution (Completed)

### Goal

Transition from single-node runtime to distributed cluster execution.

### Runtime Deliverables

- cluster mode (`--cluster`)
- worker node service
- pluggable queue layer
- distributed tracing support
- Phase-5 distributed contract RFC package: [`RFC 0026`](../rfcs/0026-phase5-cluster-runtime-control-plane-contract-v1.md), [`RFC 0027`](../rfcs/0027-phase5-distributed-queue-and-delivery-semantics-v1.md), [`RFC 0028`](../rfcs/0028-phase5-distributed-tracing-and-execution-topology-contract-v1.md)

### Eigen-Lang Integration

#### Goals

Enable distributed execution semantics inside workflows.

#### Deliverables

- distributed execution metadata
- remote execution targets
- workload partitioning support
- execution topology annotations
- cluster-aware execution policies

#### Example

```python
@hybrid_program(
    execution_mode="distributed"
)
def workflow():
    ...
```

Future support:

- distributed parameter sweeps
- multi-backend orchestration
- federated execution patterns

---

## 5. Phase-6: Plugin Ecosystem (Completed)

### Goal

Make Eigen-OS a platform.

### Runtime Deliverables

- plugin API specification
- plugin loading system
- validation and compatibility checks
- Sigstore/Cosign default trust stack (keyless Fulcio + Rekor for public/community plugins)
- mandatory out-of-process OCI sandbox via gVisor (`runsc`)
- Phase-6 GA plugin types: `driver`, `compiler_backend`, `optimizer`
- Phase-6 plugin contract RFC package: [`RFC 0029`](../rfcs/0029-phase6-plugin-sdk-and-manifest-contract-v1.md), [`RFC 0030`](../rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md), [`RFC 0031`](../rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md)

### Eigen-Lang Integration

#### Goals

Allow ecosystem extensions at the language level.

#### Deliverables

- pluggable standard library extensions
- custom workflow primitives
- backend-specific DSL modules
- plugin-based compiler passes
- external optimizer integration

#### Example

```python
from eigen_lang_plugins.qaoa import QAOAAnsatz
```

---

## 6. Phase-7: Stability & Developer Experience (Completed)

### Goal

Make adoption and contribution easier.

### Runtime Deliverables

- API/versioning policy
- compatibility guarantees
- improved docs/tutorials
- example workloads
- stronger test and CI coverage

### Eigen-Lang Integration

#### Goals

Make Eigen-Lang production-grade for developers and researchers.

#### Deliverables

- stable language specification
- language compatibility policy
- formatter and linting support
- language server support (future)
- improved tutorials and examples
- conformance test suite
- migration documentation

---

## 7. Phase-8A and Phase-8B: Runtime Intelligence/Data Hardening (Completed)

### Phase-8A baseline

Phase-8A established accepted contracts and ADRs for the Knowledge Base API, GNN optimizer service, continuous learning control plane, and QFS-L2 checkpoint envelope. See [`RFC 0034`](../rfcs/0034-phase8a-knowledge-base-api-contract-v1.md) through [`RFC 0037`](../rfcs/0037-phase8a-qfs-l2-checkpoint-envelope-contract-v1.md) and ADR 0020 through ADR 0023.

### Phase-8B baseline

Phase-8B closed runtime/data-fabric hardening with accepted contracts and ADRs for:

- deterministic QRTX scheduling and lifecycle hardening ([`RFC 0038`](../rfcs/0038-phase8b-qrtx-scheduling-and-lifecycle-hardening-contract-v1.md), ADR 0024);
- QFS-L2/L3 artifact, retention, indexing, and checkpoint/restore hardening ([`RFC 0039`](../rfcs/0039-phase8b-qfs-l2-l3-data-fabric-hardening-contract-v1.md), ADR 0025);
- runtime/data telemetry correlation, alerting, and SLO gates ([`RFC 0040`](../rfcs/0040-phase8b-runtime-data-observability-and-slo-gates-v1.md), ADR 0026).

Closure evidence is tracked in [`docs/development/phase-8b/phase-8b-exit-evidence-bundle.md`](development/phase-8b/phase-8b-exit-evidence-bundle.md).

## 8. Long-Term Eigen-Lang Vision

Eigen-Lang evolves into:

- a deterministic hybrid workflow language
- a reproducible quantum orchestration DSL
- an explainable runtime interface
- a portable workload specification format

The language must remain:

- deterministic
- auditable
- reproducible
- backend-agnostic

---

## 9. Guiding Principles

- contracts-first architecture
- reproducibility over magic
- explainability over opacity
- modularity over monolith
- developer-first experience

---

## 10. Immediate Next Steps

1. Keep Phase-8B SLO gates green in required CI.
2. Monitor runtime/data alert packs for queue pressure, compiler regression, and driver degradation signals.
3. Treat any runtime lifecycle, QFS envelope, or telemetry-contract breakage as RFC/ADR-governed work with migration notes.
4. Plan the next milestone from the Phase-8+ implementation roadmap after Phase-8B closure evidence is reviewed.

---

## 11. Strategic Direction

Eigen-OS evolves across multiple layers:

| Layer | Direction |
| --- | --- |
| Runtime | Execution → Orchestration → Distributed Infrastructure |
| Intelligence | Benchmarking → Explainable Runtime Decisions |
| Language | DSL → Stable Workflow Language |
| Ecosystem | Core System → Extensible Platform |
| DX | Research Prototype → Production-Ready OSS |

---

## 12. Long-Term Vision

Eigen-OS becomes:

- a standard runtime for hybrid quantum workloads
- a reproducible benchmarking platform
- an explainable orchestration system
- a distributed execution layer
- a programmable ecosystem centered around Eigen-Lang

## 13. Documentation Alignment Track (New)

### Goal
Bring component documentation to strict implementation parity and explicitly separate current MVP behavior from target architecture.

### Not completed yet (planned)
- Rewrite component docs with dual sections: **Implemented now** vs **Planned target**.
- Reconcile major drift for: System API, Eigen Compiler, Resource Manager, QFS, Security/Isolation, Observability.
- Add dedicated architecture component page for Benchmark Service.
- Introduce docs drift CI check for present-tense implementation claims.
- Add component status badges (`implemented` / `partial` / `target`).

### Delivery plan
- **Phase-7 (current)**: complete doc normalization and add CI drift gate.
- **Phase-8 (future)**: generate architecture pages from contract metadata and test fixtures to minimize manual drift.
