# RFC 0034: Phase-8A Knowledge Base API Contract v1

- **Status**: Accepted
- **Authors**: Eigen OS maintainers
- **Created**: 2026-05-16
- **Target Milestone**: Phase 8A
- **Tracking Issue**: M8A-01

## Summary

Defines the v1 service contract for the Knowledge Base (KB): ingesting execution intelligence records, indexing query dimensions, and providing bounded-latency retrieval for runtime and operator workflows.

## Goals

- Standardize KB write/read API used by runtime, dataset pipeline, and learning loop.
- Lock indexed query dimensions required by TZ v1.1.0 acceptance probes.
- Define a deterministic error model and compatibility expectations.

## Non-goals

- Full semantic search and free-form NLP interface.
- Multi-region replication strategy (deferred to later phases).

## Reference-level design

### Core entities

- `KnowledgeRecord` with stable `record_id`, `job_id`, `circuit_id`, `artifact_ref`, `dataset_ref`, `backend_profile`, `optimizer_version`, and `created_at`.
- `QueryFilter` with indexed fields: `qubit_count`, `entanglement_score`, `noise_profile_id`, `backend_class`, `optimizer_version`, time range.
- `RecordProvenance` linking compiler, optimizer, runtime, and checkpoint references.

### API surface (logical)

- `UpsertRecord(KnowledgeRecord) -> UpsertResult`
- `BatchUpsertRecords(stream KnowledgeRecord) -> BatchResult`
- `QueryRecords(QueryRequest) -> QueryResponse`
- `GetRecord(record_id) -> KnowledgeRecord`

### Performance envelope

- Indexed query p95 target: `<100ms` in reference profile.
- Upsert idempotency: same `record_id` must converge without duplication.

### Error model

- `KB_INVALID_ARGUMENT`
- `KB_NOT_FOUND`
- `KB_INDEX_UNAVAILABLE`
- `KB_RATE_LIMITED`
- `KB_INTERNAL`

## Observability

Emit metrics/traces for:
- ingest throughput and reject counts;
- query p50/p95 latency by filter class;
- index freshness lag;
- error-code cardinality.

## Test plan

- Conformance fixtures for all error classes.
- Deterministic replay fixture for repeated upsert of same record.
- Performance smoke fixture for indexed query contract.

## Compatibility and versioning

- **Version impact:** KB API contract `1.0.0`.
- **Compatibility:** additive fields are `MINOR`; required field changes or semantic drift are `MAJOR`.

## Open questions

- Retention/TTL defaults per record class.
- Partition strategy for mixed benchmark + production traces.
