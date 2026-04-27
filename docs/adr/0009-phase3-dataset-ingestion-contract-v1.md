# ADR 0009 — Phase-3 dataset ingestion contract v1

- **Status**: Accepted
- **Date**: 2026-04-27
- **Deciders**: Eigen OS maintainers
- **Supersedes / Related**: RFC 0021, ADR 0008

## Context

Phase-3 benchmarking reproducibility depends on deterministic, auditable dataset ingestion. RFC 0021 is implemented and defines normative requirements for manifest validation, checksum/provenance verification, immutable dataset version identity, and SemVer governance.

## Decision

1. Adopt dataset ingestion contract version `1.0.0` as the Phase-3 stable baseline.
2. Require explicit version markers:
   - `manifest_schema_version`
   - `ingestion_contract_version`
3. Enforce immutable dataset identity semantics:
   - `(dataset_id, dataset_version)` uniquely identifies a dataset release.
   - Duplicate ingestion of identical content is idempotent.
   - Re-ingestion with checksum mismatch for existing identity is rejected.
4. Require structured ingestion errors with stable fields:
   - `code`
   - `field`
   - `message`
5. Govern evolution with SemVer:
   - Breaking manifest or ingestion semantics change => `MAJOR`
   - Backward-compatible optional metadata => `MINOR`
   - Non-semantic fixes only => `PATCH`

## Consequences

### Positive

- Dataset inputs for benchmarks become reproducible and independently auditable.
- Contracted error semantics simplify client validation and remediation workflows.
- Versioned ingestion artifacts support compatibility gating during release readiness.

### Trade-offs

- Producers must always supply complete provenance/checksum metadata.
- Contract evolution requires explicit version governance, changelog discipline, and migration notes when applicable.

## Evidence package

- RFC: `rfcs/0021-phase3-dataset-ingestion-contract-v1.md`
- Implementation:
  - `src/services/benchmark-service/src/benchmark_service/dataset_ingestion.py`
  - `src/services/benchmark-service/tests/test_dataset_ingestion.py`

## Rollout / governance

- This ADR is the normative implementation record for P3-02/P3-09 dataset ingestion outcomes.
- Phase-3 release readiness requires dataset ingestion compatibility to be signed in `docs/development/phase-3-compatibility-report.md`.
- Any incompatible ingestion contract update requires RFC+ADR synchronization before release gate approval.
