# Phase 5 — Distributed Execution Plan

## Status

- **Phase**: 5 (Post-MVP)
- **Planning status**: Active (RFC package accepted and indexed)
- **Started on**: 2026-04-28
- **Last updated**: 2026-04-28
- **Previous phase closure**: [`phase-4-release-readiness-checklist.md`](phase-4-release-readiness-checklist.md)
- **Execution backlog**: [`phase-5-issue-pack.md`](phase-5-issue-pack.md)
- **RFC/ADR coverage check**: [`phase-5-rfc-adr-gap-analysis.md`](phase-5-rfc-adr-gap-analysis.md)

## Goal

Transition Eigen-OS from single-node execution to deterministic, observable, and operable distributed cluster execution with clear delivery semantics.

## Scope (in)

1. **Cluster runtime control plane**
   - Cluster mode entrypoint (`--cluster`) and cluster bootstrap lifecycle.
   - Worker registration/health contract and capability handshake.
   - Deterministic job-to-worker assignment baseline.

2. **Worker node service**
   - Worker execution API and heartbeat model.
   - Runtime artifact/materialization contract on worker nodes.
   - Safe retry and cancellation behavior for remote tasks.

3. **Pluggable queue and delivery layer**
   - Queue abstraction for in-memory and external queue providers.
   - Delivery semantics baseline (at-least-once with idempotency keys).
   - Lease/visibility timeout model with dead-letter handling.

4. **Distributed tracing and execution topology**
   - End-to-end trace context propagation across control plane, queue, workers, and drivers.
   - Topology-aware execution lineage (`cluster_id`, `worker_id`, `partition_id`, `attempt`).
   - Cross-node latency decomposition for root-cause analysis.

5. **Eigen-Lang distributed integrations**
   - Distributed execution metadata in compile outputs.
   - Remote execution target selection hints and constraints.
   - Workload partition and topology annotations for explainability.

## Scope (out)

- Multi-region geo-replication and active-active failover.
- Global consistency protocols across independent clusters.
- Autonomous cross-cluster optimization loops.

## Exit criteria (Definition of Done)

1. Cluster mode can run submit/watch/results flow with at least one control-plane node and multiple workers.
2. Worker registration, lease, retry, and cancellation flows are deterministic and fixture-tested.
3. Queue abstraction supports at least one local provider and one production-like provider via common contract.
4. End-to-end traces and metrics expose cross-node critical path and failure domain.
5. Eigen-Lang distributed metadata and topology annotations are documented and conformance-tested.
6. Phase-5 RFC package and issue pack are published and cross-linked.

## Versioning constraints

- Cluster control-plane, queue contract, and topology/tracing envelopes are SemVer-governed contracts.
- Breaking changes to assignment, delivery semantics, or topology fields require `MAJOR`.
- Backward-compatible additions (optional metadata/metrics fields) use `MINOR`.
- `PATCH` releases must not alter delivery guarantees or lineage semantics.
- Every distributed execution artifact includes explicit contract-version markers.

## API/CLI targets

- CLI:
  - `eigen submit --cluster`
  - `eigen cluster workers ls` (planned)
  - `eigen cluster topology` (planned)
- APIs (internal + public metadata surface):
  - worker registration/heartbeat endpoints (internal)
  - queue lease/ack/requeue adapter API (internal)
  - execution topology metadata in job status/results (public)

## Dependencies and prerequisites

- Phase-4 deterministic runtime baselines and explainability artifacts.
- Stable idempotency semantics in system API.
- Existing observability stack (OpenTelemetry + Prometheus + dashboards).

## Deliverables map

1. Planning + backlog: this document + [`phase-5-issue-pack.md`](phase-5-issue-pack.md).
2. Governance package: [`phase-5-rfc-adr-gap-analysis.md`](phase-5-rfc-adr-gap-analysis.md) + accepted RFCs [`0026`](../../rfcs/0026-phase5-cluster-runtime-control-plane-contract-v1.md), [`0027`](../../rfcs/0027-phase5-distributed-queue-and-delivery-semantics-v1.md), [`0028`](../../rfcs/0028-phase5-distributed-tracing-and-execution-topology-contract-v1.md).
3. Implementation slices: control plane, worker service, queue abstraction, topology/tracing contract.
4. Release closure package (to be completed during execution):
   - `phase-5-release-readiness-checklist.md`
   - `phase-5-compatibility-report.md`

## Phase-5 default decisions (locked for v1)

### 1) Delivery semantics baseline

- Queue delivery guarantee: **at-least-once**.
- Idempotency key is mandatory for all distributed task execution requests.
- A task lease expiration may re-deliver work; duplicate execution must be safe.

### 2) Assignment and retry policy baseline

- Assignment order: hard constraints -> capability fitness -> load tie-break.
- Retry strategy: bounded exponential backoff with attempt cap and deterministic jitter seed.
- Cancellation is best-effort but must persist terminal cancellation intent.
- Node-loss fallback (v1): exclude lost/offline/draining workers, retry deterministic selection on remaining `READY|DEGRADED` workers, and record explicit fallback reason in assignment artifact metadata.

### 3) Topology lineage baseline

Every execution attempt must include:

- `cluster_contract_version`
- `cluster_id`
- `worker_id`
- `queue_provider`
- `partition_id` (if partitioned)
- `attempt`
- `trace_id`

### 4) Operational baseline targets (v1)

- Worker heartbeat timeout default: `30s`
- Lease visibility timeout default: `60s`
- Retry max attempts default: `3`
- Scheduler assignment p95 budget: `< 200ms`
- Queue-to-start latency p95 target: `< 2s`
