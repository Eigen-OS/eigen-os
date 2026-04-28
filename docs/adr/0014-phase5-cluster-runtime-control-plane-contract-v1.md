# ADR 0014 — Phase-5 cluster runtime control-plane contract v1

- **Status**: Accepted
- **Date**: 2026-04-28
- **Deciders**: Eigen OS maintainers
- **Supersedes / Related**: RFC 0026, ADR 0013

## Context

Phase-5 distributed execution requires a deterministic cluster control plane that replaces single-node dispatch assumptions with explicit worker lifecycle and assignment lineage contracts. RFC 0026 is implemented and defines cluster bootstrap behavior, worker registration/heartbeat transitions, and deterministic assignment artifact rules.

## Decision

1. Adopt cluster control-plane contract baseline `1.0.0` for distributed execution.
2. Require mandatory assignment lineage markers in every cluster assignment artifact:
   - `cluster_contract_version`
   - `cluster_id`
   - `assignment_id`
   - `selected_worker_id`
   - `assignment_trace`
3. Freeze v1 deterministic assignment semantics:
   - worker filtering order is fixed (`hard constraints` → `capability fitness` → `load tie-break`);
   - the same candidate set and scoring snapshot MUST produce the same selected worker.
4. Enforce worker lifecycle governance:
   - canonical states are `REGISTERING -> READY -> DEGRADED -> DRAINING -> OFFLINE`;
   - `DRAINING` and `OFFLINE` workers MUST not receive new assignments.
5. Govern control-plane contract evolution with SemVer:
   - incompatible assignment/lifecycle semantic changes => `MAJOR`
   - additive optional lineage metadata => `MINOR`
   - implementation fixes without semantic drift => `PATCH`

## Consequences

### Positive

- Multi-node assignment behavior is reproducible and auditable.
- Compatibility reporting can lock explicit assignment lineage markers.
- Incident triage can reliably reconstruct worker-selection decisions.

### Trade-offs

- Assignment strategy changes now require strict contract/version governance.
- Cluster operators must monitor additional lifecycle transitions and artifacts.

## Evidence package

- RFC: `rfcs/0026-phase5-cluster-runtime-control-plane-contract-v1.md`
- Implementation:
  - `src/rust/crates/resource-manager/src/cluster/control_plane.rs`
  - `src/rust/crates/resource-manager/src/cluster/assignment.rs`
  - `src/rust/crates/resource-manager/tests/cluster_control_plane_contract_tests.rs`

## Rollout / governance

- This ADR is the normative implementation record for Phase-5 cluster control-plane closure.
- Any incompatible control-plane semantic change requires synchronized RFC+ADR update and MAJOR planning.
- Phase-5 release sign-off depends on this ADR plus compatibility report and release-readiness checklist.
