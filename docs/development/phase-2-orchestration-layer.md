# Phase 2 — Orchestration Layer Plan

## Status

- **Phase**: 2 (Post-MVP)
- **Planning status**: Active
- **Started on**: 2026-04-27
- **Last updated**: 2026-04-27
- **Previous phase closure**: [`phase-1-production-runtime.md`](phase-1-production-runtime.md)
- **Execution backlog**: [`phase-2-issue-pack.md`](phase-2-issue-pack.md)

## Goal

Turn Eigen-OS from a production runtime into a workload orchestrator with predictable scheduling behavior, device-aware routing, and stronger multi-job throughput controls.

## Scope (in)

1. **Scheduler core**
   - Priority queues and starvation safeguards
   - Quota and fairness primitives (per tenant/project/backend class)
   - Deterministic admission + preemption policies

2. **Device-aware dispatch**
   - Device scoring model (latency, queue depth, calibration freshness, availability)
   - Route decisions with explainability fields for operators
   - Policy hooks for placement constraints

3. **Multi-device orchestration**
   - Split/route compatible workloads across multiple backends
   - Partial-result merge contract and failure compensation
   - Job affinity/anti-affinity controls

4. **Batch execution optimization**
   - Coalescing compatible jobs into execution batches
   - Throughput/latency trade-off policy controls
   - Safe fallback to single-job mode

5. **Operational guardrails**
   - Scheduler SLOs and queue-depth alerting
   - Rebalancing safety limits
   - Runbooks for hot partitions and capacity exhaustion

## Scope (out)

- Benchmarking datasets and experiment registry (Phase 3).
- ML-based scheduling/backend prediction (Phase 4).
- Enterprise multi-region HA policy layer (future phase).

## Exit criteria (Definition of Done)

1. Queueing + fairness policy behavior is deterministic and covered by conformance tests.
2. Device-aware routing is enabled by default with operator-visible routing rationale.
3. Batch execution improves throughput without violating job-level SLO objectives.
4. Multi-device execution has clear failure semantics and artifact consistency guarantees.
5. Phase-2 release checklist and compatibility report are complete.

## Versioning constraints

- Public scheduler policies and routing reason codes are versioned contracts.
- Breaking changes to queue semantics, reason codes, or batch/event contract require `MAJOR`.
- Backward-compatible policy extensions use `MINOR`.
- Documentation and operational tuning only uses `PATCH`.
