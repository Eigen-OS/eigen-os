# ADR 0016 — Phase-5 distributed tracing and execution topology contract v1

- **Status**: Accepted
- **Date**: 2026-04-28
- **Deciders**: Eigen OS maintainers
- **Supersedes / Related**: RFC 0028, ADR 0014, ADR 0015

## Context

Distributed execution introduces cross-node failure modes and latency variance that are difficult to diagnose without stable lineage metadata. RFC 0028 is implemented and defines mandatory trace propagation, topology envelope fields, and fallback trace reconstruction semantics.

## Decision

1. Adopt distributed tracing and topology contract baseline `1.0.0`.
2. Require mandatory lineage markers in distributed status/result artifacts:
   - `topology_contract_version`
   - `trace_id`
   - `cluster_id`
   - `worker_id`
   - `queue_provider`
   - `attempt`
3. Freeze v1 propagation semantics:
   - trace context MUST flow submit → control plane → queue → worker → driver;
   - if incoming context is missing, runtime creates fallback context and sets `trace_reconstructed=true`.
4. Require topology continuity in user-visible metadata surfaces:
   - job status and results expose stable lineage envelope fields;
   - observability assets MUST include queue-to-worker handoff and trace continuity signals.
5. Govern topology/tracing contract evolution with SemVer:
   - incompatible required lineage field/semantic changes => `MAJOR`
   - additive optional lineage metadata => `MINOR`
   - fixes that preserve public topology semantics => `PATCH`

## Consequences

### Positive

- Cross-node incident triage gets a single stable lineage vocabulary.
- SLO operations can correlate queue, worker, and execution latency without ad-hoc parsing.
- Explainability surfaces can reference deterministic execution topology identifiers.

### Trade-offs

- Distributed flows carry additional metadata and tracing overhead.
- Teams must keep topology contracts synchronized across control plane, queue, and worker services.

## Evidence package

- RFC: `rfcs/0028-phase5-distributed-tracing-and-execution-topology-contract-v1.md`
- Implementation:
  - `src/rust/crates/eigen-kernel/src/trace_propagation.rs`
  - `src/services/system-api/app/observability/topology_metadata.py`
  - `src/services/system-api/tests/test_distributed_topology_contract.py`

## Rollout / governance

- This ADR is the normative implementation record for Phase-5 topology/tracing contract closure.
- Any incompatible topology/tracing semantic change requires synchronized RFC+ADR updates and MAJOR planning.
- Phase-5 release sign-off depends on this ADR plus compatibility report and release-readiness checklist.
