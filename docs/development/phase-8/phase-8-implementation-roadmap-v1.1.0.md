# Phase-8+: Implementation Roadmap for TZ v1.1.0 (Data-Driven Architecture)

- **Status:** Proposed for execution planning
- **Date:** 2026-05-16
- **Input baseline:** Technical specification `Eigen OS v1.1.0` + current repository state after Phase-7 closure
- **Primary objective:** convert architectural target into sequenced implementation streams with measurable exit criteria

## 1) Current baseline after Phase-7 (what is already strong)

The repository already has a mature governance and contract backbone:

- Accepted RFC/ADR discipline with compatibility and deprecation policy.
- Public and internal protobuf contracts, conformance checks, migration-note gates.
- Implemented slices of system-api, compiler stubs, benchmark service, distributed runtime contracts, observability scaffolding.
- Phase-7 closure artifacts and CI policy hardening.

This allows Phase-8 to focus on **capability implementation**, not process bootstrapping.

## 2) Gap map relative to TZ v1.1.0

### 2.1 Missing/partial runtime capabilities
- QRTX as a full hardware-aware DAG scheduler is still fragmented across contracts and partial runtime components.
- QFS levels are uneven: artifact-level storage exists conceptually, but QFS-L2 (state checkpoint/restore semantics) is not productionized.
- Live Qubit Manager abstractions (allocation/isolation/feed-forward) are not formalized as executable contracts.

### 2.2 Missing/partial data-centric intelligence loop
- Knowledge Base exists mostly as architecture intent; no fully locked service contract + performance envelope.
- Neuro-symbolic compiler path is not yet a complete Eigen-DPDA production pipeline.
- GNN optimizer contract and artifact lifecycle are still TODO-level in architecture docs.
- Continuous learning orchestration (trigger/retrain/promotion/rollback) is not yet shipped end-to-end.

### 2.3 Missing/partial platform capabilities
- Dataset Pipeline as universal HF/S3/local loader with strong QSBench validation and KB registration is incomplete.
- Cloud hardware drivers (IBM/AWS) need hardened official support matrix.
- Acceptance SLOs from TZ (latency/search throughput/queue scale/retrain cadence) are not represented as enforceable release gates.

## 3) Delivery model (execution tracks)

To reduce coupling, implementation is split into 6 parallel tracks with strict contract boundaries.

1. **Track A — Runtime Core (QRTX + lifecycle orchestration)**
2. **Track B — Data Fabric (QFS-L3 hardening + QFS-L2 introduction)**
3. **Track C — Intelligence Runtime (Eigen-DPDA + GNN optimizer)**
4. **Track D — Knowledge & Datasets (KB + Dataset Pipeline + QSBench alignment)**
5. **Track E — Hardware Enablement (QDriver v1.0 + provider drivers)**
6. **Track F — SRE/Release Gates (SLOs, observability, reliability, upgrade safety)**

## 4) Phased roadmap

## Phase-8A (4-6 weeks): Contract Lock + Vertical Slice MVP

### Goals
- Freeze missing v1 contracts for runtime intelligence/data loop.
- Deliver one **end-to-end vertical slice**: `Eigen-Lang -> compile -> optimize -> execute on simulator -> persist artifacts + dataset metadata -> queryable record in KB`.

### Work packages
- RFC package:
  - Knowledge Base API v1 (query model, indexing requirements, error model).
  - GNN optimizer service contract v1 (input AQO/topology, output mapped AQO + score).
  - Continuous learning control-plane contract v1 (train/evaluate/promote/rollback).
  - QFS-L2 checkpoint envelope v1.
- Implement minimal production services with feature flags.
- Define canonical performance fixtures for TZ acceptance probes.

### Exit criteria
- One deterministic integration test proving full vertical path.
- Versioned schemas published in `proto/` + docs reference sync.
- No unresolved contract TODO markers in critical component docs.

## Phase-8B (6-8 weeks): Runtime and Data Fabric Hardening

### Goals
- Make scheduler and storage production-ready for research loads.
- Achieve first measurable compliance with queue/latency SLO envelopes.

### Work packages
- QRTX:
  - full DAG dependency resolver,
  - priority + quota policy,
  - topology/noise-aware dispatch hooks,
  - idempotent replay-safe lifecycle transitions.
- QFS-L3:
  - strict artifact layout, retention policy, metadata indexing.
- QFS-L2:
  - checkpoint/restore API and cost guardrails.
- Observability:
  - job lifecycle spans + hardware telemetry join model,
  - alerts for queue pressure, compiler regressions, driver degradation.

### Exit criteria
- Load tests: queue >= 10,000 jobs in synthetic mode.
- Scheduling enqueue latency target trend <= 100 ms p95 in benchmark environment.
- Artifact and checkpoint integrity tests passing.

## Phase-8C (6-8 weeks): Intelligence and Self-Learning Loop

### Goals
- Move from static heuristics to measurable adaptive optimization.
- Close loop: production traces -> KB -> retraining -> safe model rollout.

### Work packages
- Eigen-DPDA v1:
  - deterministic fallback path,
  - model-assisted transition selection,
  - traceable decision logs for explainability.
- GNN optimizer v1:
  - topology-aware placement/routing baseline,
  - offline and online evaluation harness.
- Continuous Learning Pipeline:
  - trigger policy (e.g., every 1000 new circuits),
  - shadow validation + canary promotion,
  - automated rollback on regression.

### Exit criteria
- Automated model version creation on threshold event.
- Demonstrated non-regression policy in canary runs.
- Reproducible benchmark report for optimization gain vs baseline heuristic.

## Phase-8D (4-6 weeks): Hardware and Externalization

### Goals
- Make abstraction promise real across simulator and at least two providers.
- Prepare ecosystem-facing release package.

### Work packages
- QDriver API v1.0 finalization and conformance kit.
- Official drivers:
  - IBM Quantum,
  - AWS Braket,
  - simulator parity profile.
- System API readiness:
  - REST parity for key paths,
  - compatibility matrix publication.
- Developer surfaces:
  - initial Web dashboard,
  - VS Code/Jupyter integration skeletons.

### Exit criteria
- Same Eigen-Lang workload runs unchanged on simulator + 2 provider targets (within documented tolerance).
- Driver conformance suite green for official matrix.
- Operator runbook for incidents and rollback approved.

## 5) Cross-cutting NFR gates mapped to TZ acceptance criteria

For each release candidate, enforce these gates:

- **Compilation latency gate:** `<1s` for simple circuits (<1000 qubits) in reference environment.
- **Queueing gate:** `<100ms` scheduling+enqueue target (p95 reference profile).
- **Dataset ingestion gate:** up to 150k rows in <=30s for approved source profiles.
- **KB query gate:** `<100ms` for indexed dimensions (entanglement/noise/qubit count).
- **Monitoring freshness gate:** metrics latency <30s.
- **Continuous learning gate:** automatic model versioning every 1000 new circuits.

Any gate failure blocks minor release promotion.

## 6) Recommended issue/milestone structure (GitHub)

- **Milestone M8A:** Contracts + vertical slice
- **Milestone M8B:** Runtime/data hardening
- **Milestone M8C:** Adaptive intelligence loop
- **Milestone M8D:** Hardware externalization

Each issue template must include:
- contract references (RFC/ADR/proto),
- backward-compatibility impact,
- observability impact,
- acceptance test IDs,
- rollout/rollback plan.

## 7) Key risks and mitigation

1. **Model-driven nondeterminism risk**  
   Mitigation: deterministic fallback path, seed policy, replay harness.
2. **Provider API drift risk**  
   Mitigation: version-pinned adapters + nightly conformance smoke.
3. **Data quality drift risk (QSBench + user traces)**  
   Mitigation: schema registry + quarantine pipeline for invalid batches.
4. **Performance regression risk under mixed workloads**  
   Mitigation: mandatory p95 trend gate on PR and release branches.

## 8) Immediate next 14-day action plan

1. Open RFCs for KB API, GNN optimizer API, QFS-L2 envelope, learning control plane.
2. Add `phase-8` milestone board and map existing TODOs from architecture component docs.
3. Implement minimal vertical slice behind feature flags (`kb_v1`, `optimizer_v1`, `learning_pipeline_v1`).
4. Add first acceptance-gate CI job bundle for latency/throughput probes.
5. Publish weekly architecture delta report (planned vs implemented).

## 9) Definition of done for "TZ v1.1.0 implementation baseline"

The implementation baseline can be marked complete when:

- all critical contracts are versioned and accepted,
- vertical slice runs across simulator and at least one cloud backend,
- core TZ acceptance SLO gates are executable in CI/pre-release,
- continuous learning loop produces and safely promotes model versions,
- operator/developer docs are synchronized with real behavior.
