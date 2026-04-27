# RFC 0020: Phase-3 Benchmark Run Lifecycle Contract v1

- **Status**: Implemented
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-27
- **Accepted on**: 2026-04-27
- **Implemented on**: 2026-04-27
- **Target Milestone**: Phase 3
- **Tracking Issue**: #212
- **Replaces / Related**: docs/development/phase-3-issue-pack.md (P3-01), docs/development/phase-3-benchmarking-platform.md

## Summary

This RFC defines the first stable benchmark run lifecycle contract for Phase-3 benchmark service core. It standardizes the run state machine, idempotent start/retry behavior, and immutable deterministic run snapshot metadata.

## Motivation

Without a formal run lifecycle contract, benchmark executions are hard to reproduce and audit. P3-01 requires deterministic run metadata and retry-safe orchestration semantics.

## Goals

- Define lifecycle states and legal transitions for benchmark runs.
- Guarantee idempotent `start` and `retry` semantics.
- Require immutable run snapshot persistence with explicit version markers.
- Establish SemVer policy for lifecycle contract changes.

## Non-Goals

- Benchmark dataset ingestion schema (covered by future Phase-3 RFC).
- Compare/history APIs and statistical methodology (covered by future Phase-3 RFCs).
- Distributed queueing/storage implementation details.

## Guide-level Explanation

The benchmark service creates a run in `PENDING`, advances through preparation and execution, and ends in a terminal state. Duplicate start/retry requests do not produce duplicate runs.

State flow (v1):

- `PENDING -> PREPARING -> RUNNING -> SUCCEEDED|FAILED`
- `PENDING|PREPARING|RUNNING -> CANCELLED`
- Terminal states are immutable.

## Reference-level Design

### Lifecycle version marker

- `state_contract_version: "1.0.0"` is mandatory in every run record.

### Snapshot version marker

- `snapshot_version: "1.0.0"` is mandatory in execution snapshot artifacts.

### Idempotency rules

- `start_run(idempotency_key, config)` is idempotent by `idempotency_key`.
- `retry_run(run_id, retry_key)` is idempotent by `(run_id, retry_key)` and only legal from `FAILED|CANCELLED` source runs.

### Snapshot persistence rules

Each run stores immutable snapshot metadata:

- `run_id`
- `created_at`
- `request_hash`
- canonicalized payload (`sort_keys=true`)
- `contract_version`
- `snapshot_version`

## Interfaces / APIs

- Internal service API (initial implementation):
  - `start_run(idempotency_key, config)`
  - `retry_run(run_id, retry_key)`
  - `transition(run_id, new_state)`

Public HTTP/gRPC API work is deferred to P3-03.

## Data Models

`BenchmarkRun` includes:

- `run_id`
- `parent_run_id`
- `state`
- `state_contract_version`
- `idempotency_key`
- immutable `snapshot`

## Security and Privacy

- Snapshot payload must not include secrets in plaintext.
- Request hashing supports audit trails without exposing raw parameters in every index.

## Observability

Implementations must expose per-state counters and transition failures in future telemetry packs (P3-07).

## Performance

- Deterministic canonicalization and hashing are linear in payload size.
- Idempotency indexes are O(1) expected lookup.

## Testing Plan

- State machine transition tests.
- Duplicate `start` idempotency tests.
- Duplicate `retry` idempotency tests.
- Snapshot immutability and canonicalization tests.

## Implementation / Migration

- Initial implementation ships in `benchmark-service` package version `0.1.0`.
- Contract version is fixed at `1.0.0`.
- Future incompatible changes require `2.0.0` and migration notes.

## Compatibility and Versioning

- **Version impact:** MINOR platform capability addition (new service); benchmark lifecycle contract baseline introduced as `1.0.0`.
- **Compatibility:** Existing services are unaffected; contract is additive.
- **Migration notes:** No migration required for existing runtime clients.

## Considered Alternatives

- Reusing runtime job lifecycle directly: rejected because benchmark retries and snapshot guarantees require dedicated semantics.
- Allowing mutable snapshots: rejected due to audit/reproducibility risks.

## Open Questions

- Retry quotas and backoff policy are deferred.
- Terminal `TIMEOUT` state may be added in a backward-compatible way via MINOR if made optional.
