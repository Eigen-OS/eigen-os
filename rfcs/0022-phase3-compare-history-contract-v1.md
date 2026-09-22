# RFC 0022: Phase-3 Comparison Methodology and History Contract v1

- **Status**: Implemented
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-27
- **Accepted on**: 2026-04-27
- **Implemented on**: 2026-04-27
- **Target Milestone**: Phase 3
- **Tracking Issue**: #220
- **Replaces / Related**: docs/development/phase-3-issue-pack.md (P3-04, P3-05, P3-09), docs/development/phase-3-benchmarking-platform.md

## Summary

This RFC defines the first stable comparison and history contracts for Phase-3 benchmarking. It standardizes comparison payload semantics, methodology metadata requirements, deterministic regression signaling, and history pagination/ordering guarantees.

## Motivation

Benchmark comparisons and trends are only actionable when computed under stable, versioned semantics. Contract-level guarantees are required so clients can trust regression decisions and historical analyses across releases.

## Goals

- Define stable compare output semantics with explicit methodology metadata.
- Define stable history query and pagination/ordering guarantees.
- Require explicit version markers on compare outputs and history entries.
- Define SemVer policy for compare/history contract evolution.

## Non-Goals

- Benchmark run lifecycle semantics (RFC 0020).
- Dataset manifest ingestion semantics (RFC 0021).
- Product-level threshold tuning policy governance.

## Guide-level Explanation

Comparison evaluates two benchmark slices (`baseline` vs `candidate`) and returns deterministic deltas and regression flags for identical inputs. History endpoints provide filterable trends with stable ordering and deterministic pagination cursors.

## Reference-level Design

### Mandatory version markers

- `comparison_version: "1.0.0"` in compare outputs.
- `methodology_version: "1.0.0"` in compare outputs.
- `history_contract_version: "1.0.0"` in history responses and entries.

### Compare contract semantics (v1)

- Inputs identify baseline/candidate run cohorts.
- Output includes metric deltas (`absolute_delta`, `relative_delta`) and optional confidence metadata.
- Regression flag semantics are deterministic for identical inputs and thresholds.

### History contract semantics (v1)

- Filter support: dataset/backend/runtime/version/time-range.
- Stable ordering guarantee: `created_at DESC, run_id ASC`.
- Deterministic cursor-based pagination via `page_token`.

### Error model

Structured errors include `code`, `field`, `message`.

Baseline codes:

- `BENCHMARK_COMPARE_INVALID_REQUEST`
- `BENCHMARK_HISTORY_INVALID_FILTER`
- `BENCHMARK_HISTORY_PAGE_TOKEN_INVALID`

## Interfaces / APIs

- Compare endpoint: `/benchmarks/compare`
- History endpoint: `/benchmarks/history`

## Data Models

`BenchmarkComparison` includes:

- `comparison_version`
- `methodology_version`
- baseline/candidate descriptors
- per-metric deltas and regression flags

`BenchmarkHistoryEntry` includes:

- `history_contract_version`
- run identity and timestamp fields
- dataset/backend/runtime descriptors
- summary metrics

## Security and Privacy

- History and compare payloads exclude secrets and raw credentials.
- Methodology metadata improves auditability of regression decisions.

## Observability

Implementations should expose:

- compare request count/latency/error metrics
- history request count/latency/error metrics
- regression flag frequency metrics by policy key

## Performance

- Compare complexity scales with number of compared metrics.
- History query complexity scales with filter selectivity and page size.

## Benchmarking/Test Plan

- Contract fixtures for compare request/response compatibility.
- Regression fixture coverage for deterministic flag behavior.
- Contract fixtures for history response envelopes.
- Pagination determinism tests across repeated identical queries.
- Ordering invariance tests for `created_at DESC, run_id ASC`.

## Implementation / Migration

- Initial implementation ships in `benchmark-service` package version `0.8.0`.
- Contract baselines are `comparison_version: 1.0.0`, `methodology_version: 1.0.0`, `history_contract_version: 1.0.0`.
- Incompatible semantics or ordering changes require `2.0.0` and migration notes.

## Compatibility and Versioning

- **Version impact:** MINOR governance uplift; compare/history contracts remain stable at `1.0.0`.
- **Compatibility:** Backward compatible with existing `/benchmarks/compare` and `/benchmarks/history` clients.
- **Migration notes:** No mandatory migration. Consumers should pin to explicit version fields and stable ordering assumptions.

## Considered Alternatives

- Leaving methodology metadata optional: rejected because it weakens reproducibility.
- Offset pagination only: rejected due to instability under concurrent inserts.

## Open Questions

- Future MINOR may add optional non-parametric statistical descriptors.
