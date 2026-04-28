# RFC 0026: Phase-5 Cluster Runtime Control-Plane Contract v1

- **Status**: Draft
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-28
- **Target Milestone**: Phase 5
- **Tracking Issue**: P5-08 (docs/development/phase-5-issue-pack.md)
- **Replaces / Related**: docs/development/phase-5-distributed-execution.md

## Summary

This RFC defines the v1 control-plane contract for distributed cluster execution: cluster bootstrap lifecycle, worker registration/heartbeat semantics, and deterministic assignment output envelope.

## Motivation

Phase-5 introduces multi-node execution. Without a formal control-plane contract, worker coordination and assignment behavior can drift and become non-debuggable.

## Goals

- Define cluster bootstrap and health lifecycle.
- Standardize worker registration and capability handshake schema.
- Define deterministic assignment artifact with explicit lineage/version markers.

## Non-Goals

- Multi-region federation and WAN failover.
- Proprietary optimizer-managed control planes.
- Dynamic auto-scaling policy engine design (future phase).

## Guide-level Explanation

The control plane accepts jobs, discovers eligible workers, applies deterministic assignment, and emits a versioned assignment artifact consumed by queue and worker runtimes.

## Reference-level Design

### Contract envelope (v1)

- `cluster_contract_version: "1.0.0"`
- `cluster_id`
- `control_plane_instance_id`
- `assignment_id`
- `job_id`
- `candidate_workers[]`
- `selected_worker_id`
- `assignment_trace[]`
- `created_at`

### Deterministic assignment sequence

1. Filter workers by hard constraints (backend/type/security/tenant).
2. Rank by capability fitness score.
3. Apply load tie-break policy.
4. Emit assignment artifact with deterministic ordering.

### Worker lifecycle states

`REGISTERING -> READY -> DEGRADED -> DRAINING -> OFFLINE`

Required transitions:

- missed heartbeats beyond timeout move worker to `DEGRADED`;
- drained workers must not receive new assignments;
- `OFFLINE` workers are excluded from candidate set.

## Interfaces / APIs

- Internal control-plane API:
  - `RegisterWorker`
  - `HeartbeatWorker`
  - `AssignJob`
  - `DrainWorker`

## Data Models

- `WorkerDescriptor`
- `WorkerHealthSnapshot`
- `AssignmentArtifact`

## Security and Privacy

- Worker registration requires authenticated identity.
- Capability claims must be validated against policy restrictions.
- Assignment artifacts must avoid embedding sensitive payload data.

## Observability

Required metrics:

- `cluster_workers_registered_total`
- `cluster_worker_heartbeat_timeout_total`
- `cluster_assignment_latency_ms`
- `cluster_assignment_failures_total`

Required trace attributes:

- `cluster.id`
- `worker.id`
- `assignment.id`

## Performance

- Assignment target: `p95 < 200ms`, `p99 < 400ms`.
- Worker registration overhead should remain negligible relative to heartbeat interval.

## Benchmarking/Test Plan

- Integration fixtures for worker lifecycle transitions.
- Determinism suite for assignment replay.
- Chaos tests for worker-loss during assignment.

## Implementation / Migration

1. Introduce control-plane DTO schema + validators.
2. Add worker state machine and registry.
3. Implement deterministic assignment path.
4. Wire assignment artifact into queue adapter contract.

Migration notes:

- Single-node mode maps to implicit single-worker cluster profile.

## Compatibility and Versioning

- **Version impact:** New contract surface with `1.0.0` baseline.
- **Compatibility:** Existing non-cluster execution remains supported.
- **Migration notes:** Cluster deployers must configure heartbeat timeout and worker identity provider.

## Considered Alternatives

- Best-effort non-deterministic assignment: rejected due to reproducibility risk.
- Worker-selected pull-only execution: deferred to later phase due to fairness/queue governance gaps.

## Open Questions

- Default fairness strategy across tenants in shared clusters.
