# Eigen-OS Roadmap

## Overview

This document defines the open-source development roadmap for Eigen-OS.

Eigen-OS is positioned as:
> A cloud-native runtime and orchestration layer for hybrid quantum-classical workloads

The open-source version focuses on:

- execution
- orchestration
- reproducibility
- benchmarking
- developer experience

---

## 1. Current State

### Completed

- MVP-1: Core services and contracts
- MVP-2: Compilation pipeline
- MVP-3: Execution and results retrieval
- Phase-1: Production runtime
- Phase-2: Orchestration layer

### Capabilities Today

- JobSpec-based execution model
- Compiler pipeline (AST → IR → execution artifacts)
- QRTX kernel lifecycle management
- DriverManager + simulator execution
- Device-aware scheduling (baseline)
- Observability (metrics + tracing)
- Local development environment

---

## 2. Strategic Direction

Eigen-OS evolves along three axes:

1. **Execution → Orchestration → Intelligence**
2. **Local → Distributed → Cloud-native**
3. **Runtime → Benchmarking → Optimization**

---

## 3. Phase-3: Benchmarking Platform

### Goal

Transform Eigen-OS into a **reproducible benchmarking and analytics platform**.

### Why This Matters

Quantum execution today is:
- hard to evaluate
- non-reproducible
- opaque

Eigen-OS will provide:
> measurable, comparable, and explainable execution results

### Key Features

#### 1) Dataset Integration

- QSBench-compatible datasets
- Support for:
  - circuit datasets
  - noise models
  - backend configurations

#### 2) Benchmark Execution

- standardized benchmark runs
- reproducible execution pipelines
- deterministic configuration snapshots

#### 3) Experiment Tracking

- run registry:
  - job metadata
  - backend
  - parameters
  - execution results
- persistent storage of runs

#### 4) Comparison Engine

- side-by-side comparison:
  - backend A vs backend B
  - noise vs no-noise
  - transpilation strategies

#### 5) Metrics

Core metrics:
- latency
- execution time breakdown
- success rate
- fidelity / expectation deviation
- circuit characteristics

### Contract governance status (updated 2026-04-27)

- Stable Phase-3 benchmark contracts are now backed by accepted/implemented RFCs:
  - run lifecycle: `RFC 0020`
  - dataset ingestion: `RFC 0021`
  - compare/history methodology: `RFC 0022`
- No Phase-3 benchmark contract is considered stable without an accepted RFC.

### Deliverables

- `benchmark-service`
- dataset ingestion pipeline
- CLI:
  - `eigen benchmark run`
  - `eigen benchmark compare`
- API endpoints:
  - `/benchmarks/run`
  - `/benchmarks/compare`
  - `/benchmarks/history`

### Outcome

Eigen-OS becomes:
- a benchmarking standard
- a research tool
- a validation layer for runtime behavior

---

## 4. Phase-4: Intelligent Runtime (Open Source Scope)

### Goal

Introduce **data-driven and explainable runtime decisions**.

Important:
> This phase avoids heavy proprietary ML and focuses on transparency

### Key Features

#### 1) Backend Scoring

- scoring based on:
  - latency
  - availability
  - historical performance
  - error characteristics
- deterministic + statistical approach

#### 2) Adaptive Scheduling

- improved scheduling policies:
  - priority + fairness
  - device-aware routing
  - queue optimization
- rule-based and configurable

#### 3) Compilation Optimization (Baseline)

- rule-based circuit optimizations
- transpilation strategy selection
- pattern-based improvements

#### 4) Explainability

System must provide:

- "why this backend was selected"
- "why this execution took longer"
- "where errors likely occurred"

### Deliverables

- scoring module
- scheduling policy engine (configurable)
- explanation API:
  - `/explain/backend-selection`
  - `/explain/execution`

### Outcome

Eigen-OS becomes:
- predictable
- debuggable
- explainable

---

## 5. Phase-5: Distributed Execution (OSS)

### Goal

Move from single-node runtime to **distributed cluster execution**.

### Key Features

#### 1) Multi-node Execution

- distributed job execution
- worker nodes with driver access

#### 2) Control Plane Separation

- scheduler as control plane
- execution nodes as workers

#### 3) Queue-Based Architecture

- async job execution
- message-based communication

#### 4) Fault Tolerance

- retries
- node failure handling
- job rescheduling

### Deliverables

- cluster mode (`--cluster`)
- worker node service
- queue layer (pluggable)
- distributed tracing support

### Outcome

Eigen-OS becomes:
- scalable
- resilient
- suitable for real workloads

---

## 6. Phase-6: Plugin Ecosystem

### Goal

Turn Eigen-OS into a **platform, not just a system**.

### Key Features

#### 1) Driver Plugins

- hardware connectors
- simulator extensions

#### 2) Compiler Plugins

- alternative backends
- optimization strategies

#### 3) Scheduler Plugins

- custom scheduling policies
- research algorithms

### Deliverables

- plugin API specification
- plugin loading system
- validation and compatibility checks

### Outcome

- community contributions
- extensibility
- ecosystem growth

---

## 7. Phase-7: Stability & Developer Experience

### Goal

Make Eigen-OS easy to adopt and use.

### Key Features

- stable APIs and versioning
- improved documentation
- reproducible local setup
- better CLI UX
- test coverage and CI improvements

### Deliverables

- versioning policy
- compatibility guarantees
- improved docs and tutorials
- example workloads

### Outcome

- lower adoption barrier
- better developer onboarding
- increased community usage

---

## 8. Long-Term Vision

Eigen-OS (open source) becomes:

- the standard runtime layer for quantum workloads
- a reproducible benchmarking platform
- an extensible orchestration system
- a foundation for research and experimentation

---

## 9. Guiding Principles

- contracts-first architecture remains core
- reproducibility over "magic"
- explainability over opaque intelligence
- modularity over monolith
- developer-first experience

---

## 10. Immediate Next Steps

1. Implement minimal benchmark pipeline
2. Integrate first QSBench dataset
3. Add run tracking and comparison
4. Expose benchmark API and CLI
5. Prepare demo-ready workflow
