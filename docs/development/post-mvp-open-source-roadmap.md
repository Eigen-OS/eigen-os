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
- Phase-4: Intelligent runtime
- Phase-5: Distributed execution

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

Planning artifacts (completed):

- [phase-5-distributed-execution.md](phase-5-distributed-execution.md)
- [phase-5-issue-pack.md](phase-5-issue-pack.md)
- [phase-5-rfc-adr-gap-analysis.md](phase-5-rfc-adr-gap-analysis.md)

## Phase-6: Plugin Ecosystem

Goal: make Eigen-OS a platform.

Runtime deliverables:

- plugin API specification
- plugin loading system
- validation and compatibility checks
- Sigstore/Cosign default trust stack (keyless Fulcio + Rekor for public/community plugins)
- mandatory out-of-process OCI sandbox via gVisor (`runsc`)

Eigen-Lang deliverables:

- GA plugin type set: `driver`, `compiler_backend`, `optimizer`
- scheduler policies stay core-configurable (not a GA plugin type in Phase-6)
- improved tutorials/examples
- conformance test suite
- migration documentation

Planning artifacts:

- [phase-6-plugin-ecosystem.md](phase-6-plugin-ecosystem.md)
- [phase-6-issue-pack.md](phase-6-issue-pack.md)
- [phase-6-rfc-adr-gap-analysis.md](phase-6-rfc-adr-gap-analysis.md)
- [../../rfcs/0029-phase6-plugin-sdk-and-manifest-contract-v1.md](../../rfcs/0029-phase6-plugin-sdk-and-manifest-contract-v1.md)
- [../../rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md](../../rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md)
- [../../rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md](../../rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md)

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

1. Finalize default issuer/subject policy templates for Sigstore keyless verification
2. Land manifest schema validator and plugin SDK scaffolding commands
3. Implement lifecycle state machine with deterministic activation ordering
4. Enforce `runsc` sandbox profile + compatibility/trust load-time gates
5. Publish Phase-6 release-readiness and compatibility closure artifacts
