# RFC 0037: Phase-8A QFS-L2 Checkpoint Envelope Contract v1

- **Status**: Accepted
- **Authors**: Eigen OS maintainers
- **Created**: 2026-05-16
- **Target Milestone**: Phase 8A
- **Tracking Issue**: M8A-04

## Summary

Defines a versioned QFS-L2 checkpoint envelope for runtime state snapshot/restore with integrity, provenance, and cost-guard metadata.

## Goals

- Standardize checkpoint payload and metadata across runtime components.
- Guarantee restore safety through schema and integrity checks.
- Provide cost/size guardrails required for production operation.

## Non-goals

- Physical storage backend selection.
- Long-term archival policy.

## Reference-level design

### Envelope structure

- Header: `checkpoint_id`, `job_id`, `created_at`, `runtime_version`, `schema_version`.
- Payload refs: state segments, memory graph refs, execution cursor.
- Integrity: checksum set + signature reference.
- Provenance: compiler/optimizer/model versions, backend profile, seed.
- Guardrails: declared byte size, estimated restore cost, TTL class.

### API semantics

- `CreateCheckpoint` is idempotent by `(job_id, execution_cursor)`.
- `RestoreCheckpoint` must verify checksum/schema compatibility before execution resume.
- Incompatible schema returns explicit migration-required error.

### Error model

- `QFSL2_INVALID_ENVELOPE`
- `QFSL2_CHECKSUM_MISMATCH`
- `QFSL2_SCHEMA_INCOMPATIBLE`
- `QFSL2_COST_GUARD_BLOCKED`
- `QFSL2_INTERNAL`

## Observability

- checkpoint create/restore latency;
- integrity failure counts;
- envelope size distribution;
- restore success ratio.

## Test plan

- Envelope schema validation fixtures.
- Tamper/integrity negative tests.
- Restore replay test with deterministic continuation.

## Compatibility and versioning

- **Version impact:** QFS-L2 envelope contract `1.0.0`.
- **Compatibility:** additive optional metadata is `MINOR`; required header/payload semantic changes are `MAJOR`.

## Open questions

- Compression policy defaults by workload tier.
- Encryption-at-rest key-rotation interface boundary.
