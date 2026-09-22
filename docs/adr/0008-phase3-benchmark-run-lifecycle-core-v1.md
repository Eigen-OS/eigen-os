# ADR 0008 — Phase-3 benchmark run lifecycle core v1

- **Status**: Accepted
- **Date**: 2026-04-27
- **Deciders**: Eigen OS maintainers
- **Supersedes / Related**: RFC 0020, ADR 0007

## Context

Phase-3 requires a dedicated benchmark service with reproducible run lifecycle semantics. P3-01 mandates state transition rules, idempotent duplicate handling, and immutable execution snapshots with explicit version markers.

## Decision

1. Adopt benchmark run lifecycle contract version `1.0.0` for benchmark-service core.
2. Freeze legal transitions for v1:
   - `PENDING -> PREPARING -> RUNNING -> SUCCEEDED|FAILED`
   - `PENDING|PREPARING|RUNNING -> CANCELLED`
3. Enforce idempotency:
   - Start keyed by `idempotency_key`.
   - Retry keyed by `(run_id, retry_key)` and permitted only from `FAILED|CANCELLED`.
4. Persist immutable deterministic snapshot metadata for each run with:
   - `contract_version`
   - `snapshot_version`
   - `request_hash`
   - canonicalized payload.
5. Treat lifecycle contract changes as SemVer-governed artifacts where incompatible behavior requires MAJOR increment.

## Consequences

### Positive

- Reproducible and auditable benchmark run records.
- Duplicate client requests are safe and deterministic.
- Contract-versioned artifacts support future compatibility gates.

### Trade-offs

- Lifecycle expansion now requires formal contract/version governance.
- Retry behavior is intentionally constrained in v1 (only terminal source runs).

## Evidence package

- RFC: `rfcs/0020-phase3-benchmark-run-lifecycle-contract-v1.md`
- Implementation:
  - `src/services/benchmark-service/src/benchmark_service/run_lifecycle.py`
  - `src/services/benchmark-service/tests/test_run_lifecycle.py`

## Rollout / governance

- This ADR is the normative implementation record for P3-01.
- Future lifecycle-semantic changes must update RFC/ADR and include migration notes.
