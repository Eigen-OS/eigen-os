# Eigen-OS Post-MVP Open-Source Roadmap

> Canonical roadmap: [`../roadmap.md`](../roadmap.md)

This document mirrors the current post-MVP plan and keeps implementation-focused wording for contributors.

## Current State

Completed:

- MVP-1: Core services and contracts
- MVP-2: Compilation pipeline
- MVP-3: Execution and results retrieval
- Phase-1: Production runtime
- Phase-2: Orchestration layer

Capabilities in place:

- JobSpec-based execution model
- Compiler pipeline (AST → IR → execution artifacts)
- QRTX kernel lifecycle management
- DriverManager + simulator execution
- Device-aware scheduling baseline
- Observability (metrics + tracing)
- Local developer environment

## Strategic Direction

Eigen-OS evolves across three axes:

1. Execution → Orchestration → Intelligence
2. Local → Distributed → Cloud-native
3. Runtime → Benchmarking → Optimization

## Phase-3: Benchmarking Platform

Goal: transform Eigen-OS into a reproducible benchmarking and analytics platform.

Deliverables:

- `benchmark-service`
- dataset ingestion pipeline (QSBench-compatible)
- CLI:
  - `eigen benchmark run`
  - `eigen benchmark compare`
- APIs:
  - `/benchmarks/run`
  - `/benchmarks/compare`
  - `/benchmarks/history`

## Phase-4: Intelligent Runtime (OSS Scope)

Goal: data-driven and explainable runtime decisions without opaque proprietary ML.

Deliverables:

- backend scoring module
- configurable scheduling policy engine
- explanation APIs:
  - `/explain/backend-selection`
  - `/explain/execution`

## Phase-5: Distributed Execution (OSS)

Goal: transition from single-node runtime to distributed cluster execution.

Deliverables:

- cluster mode (`--cluster`)
- worker node service
- pluggable queue layer
- distributed tracing support

## Phase-6: Plugin Ecosystem

Goal: make Eigen-OS a platform.

Deliverables:

- plugin API specification
- plugin loading system
- validation and compatibility checks

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

1. Implement minimal benchmark pipeline
2. Integrate first QSBench dataset
3. Add run tracking and comparison
4. Expose benchmark API and CLI
5. Prepare demo-ready workflow
