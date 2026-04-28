# Eigen-OS Post-MVP Open-Source Roadmap

> Canonical roadmap: [`../roadmap.md`](../roadmap.md)

This document mirrors the current post-MVP plan for contributors.

## Current State

Completed:

- MVP-1: Core services and contracts
- MVP-2: Compilation pipeline
- MVP-3: Execution and results retrieval
- Phase-1: Production runtime
- Phase-2: Orchestration layer
- Phase-3: Benchmarking platform

## Eigen-Lang Track

Eigen-Lang is a first-class layer that evolves in parallel with runtime/orchestration.

Current status:

- Python DSL
- deterministic AST-based compilation
- AQO mapping
- versioning policy
- restricted/validated execution model

Guidance:

- RFC-first evolution
- deterministic compilation
- compatibility-aware versioning
- conformance-driven implementation

## Phase-4: Intelligent Runtime (OSS Scope)

Goal: data-driven and explainable runtime decisions without opaque proprietary ML.

Runtime deliverables:

- backend scoring module
- configurable scheduling policy engine
- explanation APIs:
  - `/explain/backend-selection`
  - `/explain/execution`

Eigen-Lang deliverables:

- compile-time diagnostics
- runtime-aware compiler hints
- explainable backend-selection metadata
- execution annotations
- deterministic optimization recommendations

## Phase-5: Distributed Execution (OSS)

Goal: transition from single-node runtime to distributed cluster execution.

Runtime deliverables:

- cluster mode (`--cluster`)
- worker node service
- pluggable queue layer
- distributed tracing support

Eigen-Lang deliverables:

- distributed execution metadata
- remote execution targets
- workload partitioning support
- topology annotations
- cluster-aware execution policies

Planning artifacts:

- [phase-5-distributed-execution.md](phase-5-distributed-execution.md)
- [phase-5-issue-pack.md](phase-5-issue-pack.md)
- [phase-5-rfc-adr-gap-analysis.md](phase-5-rfc-adr-gap-analysis.md)

## Phase-6: Plugin Ecosystem

Goal: make Eigen-OS a platform.

Runtime deliverables:

- plugin API specification
- plugin loading system
- validation and compatibility checks

Eigen-Lang deliverables:

- stable language specification
- compatibility policy
- formatter/linting support
- language server support (future)
- improved tutorials/examples
- conformance test suite
- migration documentation

## Phase-7: Stability & Developer Experience

Goal: make adoption and contribution easier.

Deliverables:

- API/versioning policy
- compatibility guarantees
- improved docs/tutorials
- example workloads
- stronger test and CI coverage

## Guiding Principles

- contracts-first architecture
- reproducibility over magic
- explainability over opacity
- modularity over monolith
- developer-first experience

## Immediate Next Steps

1. Kick off Phase-5 cluster control-plane implementation
2. Add worker service registration/heartbeat/cancellation flows
3. Introduce pluggable queue abstraction and delivery semantics gates
4. Implement distributed topology metadata and trace continuity checks
5. Prepare distributed submit/watch/results demo in cluster mode
