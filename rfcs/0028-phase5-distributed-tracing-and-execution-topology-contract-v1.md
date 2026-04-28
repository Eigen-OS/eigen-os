# RFC 0028: Phase-5 Distributed Tracing and Execution Topology Contract v1

- **Status**: Draft
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-28
- **Target Milestone**: Phase 5
- **Tracking Issue**: P5-08 (docs/development/phase-5-issue-pack.md)
- **Replaces / Related**: RFC 0026, RFC 0027, docs/development/phase-5-distributed-execution.md

## Summary

This RFC defines the v1 topology lineage and tracing propagation contract for distributed execution, ensuring trace continuity and stable metadata across control plane, queue, workers, and result surfaces.

## Motivation

Distributed failures are difficult to diagnose without cross-node lineage. A stable topology envelope and trace propagation contract are required for debugging, SLO operations, and auditability.

## Goals

- Standardize topology lineage fields embedded in runtime artifacts.
- Define mandatory trace context propagation across distributed hops.
- Align observability contracts with job status/results and explainability surfaces.

## Non-Goals

- Full distributed tracing backend selection guidance.
- Long-term trace storage architecture.
- Automated remediation based on traces.

## Guide-level Explanation

A job receives a trace context at submit time. Each distributed hop carries the context forward and appends topology metadata. Operators can reconstruct control-plane, queue, and worker critical paths from a single lineage envelope.

## Reference-level Design

### Topology envelope (v1)

- `topology_contract_version: "1.0.0"`
- `trace_id`
- `span_id`
- `cluster_id`
- `control_plane_instance_id`
- `worker_id`
- `queue_provider`
- `partition_id` (optional)
- `attempt`
- `lineage_timestamp`

### Propagation rules

1. Submit edge creates root span if none is present.
2. Control plane propagates context into queue task envelope.
3. Worker runtime starts child span on lease acquisition.
4. Driver execution inherits worker span context.
5. Status/results surfaces expose stable topology envelope fields.

### Failure semantics

- Missing trace context must not fail execution.
- If context is missing, runtime creates fallback trace and marks `trace_reconstructed=true`.
- Topology envelope version must still be emitted.

## Interfaces / APIs

- Internal execution metadata interfaces.
- Public status/results metadata extension fields.
- Explainability payload references to distributed lineage identifiers.

## Data Models

- `DistributedTopologyEnvelope`
- `TracePropagationRecord`
- `ExecutionLineageArtifact`

## Security and Privacy

- Topology metadata must not include sensitive tenant payload fields.
- Trace IDs should be opaque and non-guessable.
- Cross-tenant trace mixing must be prevented via tenant boundary tags.

## Observability

Required metrics:

- `trace_context_propagation_failures_total`
- `distributed_span_link_break_total`
- `execution_topology_events_total`
- `queue_to_worker_handoff_latency_ms`

Required traces/logs:

- root submit span
- control-plane assignment span
- queue lease span
- worker execution span

## Performance

- Trace propagation overhead target: `< 5%` additional latency on assignment path.
- Topology metadata serialization should remain bounded and constant-size in v1.

## Benchmarking/Test Plan

- End-to-end trace continuity integration tests.
- Metadata compatibility fixtures for status/results payloads.
- Fault injection tests for missing/invalid trace context.

## Implementation / Migration

1. Add topology envelope schema and validators.
2. Instrument queue and worker hops for propagation.
3. Expose topology fields in status/results APIs.
4. Add dashboards/alerts for context breakage.

Migration notes:

- Existing single-node traces are mapped to `cluster_id=local` profile.

## Compatibility and Versioning

- **Version impact:** New topology/tracing metadata contract at `1.0.0`.
- **Compatibility:** Existing consumers can ignore additive topology fields.
- **Migration notes:** Consumers parsing status/results should tolerate unknown metadata fields.

## Considered Alternatives

- Best-effort unstructured metadata tags: rejected due to compatibility drift.
- Provider-specific trace propagation only: rejected for portability limitations.

## Open Questions

- Required retention window for distributed topology artifacts in OSS defaults.
