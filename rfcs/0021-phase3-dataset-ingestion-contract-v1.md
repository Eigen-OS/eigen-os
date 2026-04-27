# RFC 0021: Phase-3 Dataset Ingestion Contract v1

- **Status**: Implemented
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-27
- **Accepted on**: 2026-04-27
- **Implemented on**: 2026-04-27
- **Target Milestone**: Phase 3
- **Tracking Issue**: #220
- **Replaces / Related**: docs/development/phase-3-issue-pack.md (P3-02, P3-09), docs/development/phase-3-benchmarking-platform.md

## Summary

This RFC defines the first stable dataset ingestion contract for the Phase-3 benchmarking platform. It standardizes bundle manifest requirements, checksum/provenance verification, registry versioning behavior, and structured error semantics.

## Motivation

Benchmarking outcomes are only reproducible when dataset inputs are validated, versioned, and traceable. Without a formal ingestion contract, teams can ingest inconsistent bundles and produce non-comparable results.

## Goals

- Define a stable QSBench-compatible ingestion bundle contract.
- Require manifest schema version markers and provenance fields.
- Enforce deterministic checksum validation for dataset assets.
- Standardize structured validation and integrity errors.
- Establish SemVer rules for ingestion contract evolution.

## Non-Goals

- Benchmark run lifecycle state machine semantics (RFC 0020).
- Comparison and history methodology semantics (RFC 0022).
- External artifact distribution/storage replication policies.

## Guide-level Explanation

A dataset producer submits a dataset bundle containing `manifest.json` and declared artifacts. The service validates schema and checksums, then registers an immutable dataset version record.

High-level flow:

1. Parse and validate `manifest.json`.
2. Validate required metadata (`dataset_id`, `dataset_version`, provenance, schema).
3. Verify artifact checksums against the manifest.
4. Persist dataset version metadata in the catalog.
5. Return structured success or structured validation/integrity error.

## Reference-level Design

### Contract version markers

- `manifest_schema_version: "1.0.0"` is mandatory in the dataset manifest.
- `ingestion_contract_version: "1.0.0"` is mandatory in ingestion API responses and catalog entries.

### Required manifest fields (v1)

- `dataset_id`
- `dataset_version` (SemVer)
- `manifest_schema_version`
- `created_at`
- `source`
- `artifacts[]` with `path`, `sha256`, and content descriptor metadata

### Ingestion semantics

- `dataset_id + dataset_version` identifies an immutable dataset release.
- Duplicate ingestion of identical bundles is idempotent.
- Re-ingestion with mismatched checksums for an existing release is rejected.

### Error model

Structured errors include:

- `code` (stable machine-readable identifier)
- `field` (manifest field or artifact path)
- `message` (human-readable explanation)

Baseline codes:

- `DATASET_MANIFEST_INVALID`
- `DATASET_CHECKSUM_MISMATCH`
- `DATASET_VERSION_CONFLICT`

## Interfaces / APIs

- Internal ingestion API: `ingest_dataset_bundle(bundle_path)`
- Internal catalog API: `list_dataset_versions(dataset_id)`

Public API exposure is tracked independently but must preserve this contract.

## Data Models

`DatasetCatalogEntry` includes:

- `dataset_id`
- `dataset_version`
- `manifest_schema_version`
- `ingestion_contract_version`
- `created_at`
- `source`
- immutable artifact descriptors + checksums

## Security and Privacy

- Provenance metadata is mandatory for auditability.
- Integrity verification uses cryptographic checksums.
- Manifests must not include secrets or credentials.

## Observability

Implementations should expose:

- ingestion attempts/success/failure counters
- validation failure reason counters by stable `code`
- ingestion duration histogram

## Performance

- Manifest validation is linear in field/artifact count.
- Checksum validation is linear in artifact byte size.

## Benchmarking/Test Plan

- Positive fixture ingestion for valid QSBench-compatible bundle.
- Negative fixtures for missing required fields.
- Negative fixtures for checksum mismatch.
- Idempotent re-ingestion tests for identical bundles.
- Version conflict tests for same `(dataset_id, dataset_version)` with different content.

## Implementation / Migration

- Initial implementation ships in `benchmark-service` package version `0.8.0`.
- Contract baseline is `ingestion_contract_version: 1.0.0` and `manifest_schema_version: 1.0.0`.
- Incompatible schema or semantics changes require `2.0.0` and migration guidance.

## Compatibility and Versioning

- **Version impact:** MINOR capability governance uplift; stable dataset ingestion contract remains `1.0.0`.
- **Compatibility:** Backward compatible with current Phase-3 ingestion behavior.
- **Migration notes:** No mandatory migration. Producers should continue publishing explicit `manifest_schema_version` and checksum metadata.

## Considered Alternatives

- Allowing unversioned manifests: rejected due to reproducibility and audit risks.
- Treating checksum mismatch as warning: rejected because integrity is contractual.

## Open Questions

- Optional support for detached signature verification may be added in a future MINOR release.
