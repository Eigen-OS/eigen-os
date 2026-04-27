# Phase 3 — Benchmarking Platform Plan

## Status

- **Phase**: 3 (Post-MVP)
- **Planning status**: Active (RFC package landed)
- **Started on**: 2026-04-27
- **Last updated**: 2026-04-27
- **Previous phase closure**: [`phase-2-release-readiness-checklist.md`](phase-2-release-readiness-checklist.md)
- **Execution backlog**: [`phase-3-issue-pack.md`](phase-3-issue-pack.md)
- **RFC/ADR coverage check**: [`phase-3-rfc-adr-gap-analysis.md`](phase-3-rfc-adr-gap-analysis.md)

## Goal

Turn Eigen-OS into a reproducible benchmarking and comparative analytics platform that allows teams to run, track, and compare workload behavior across backends and configurations.

## Scope (in)

1. **Benchmark dataset pipeline**
   - QSBench-compatible dataset ingestion and normalization.
   - Versioned dataset manifests (dataset identity, provenance, checksum, schema).
   - Validation rules for malformed or incomplete benchmark bundles.

2. **Benchmark execution service**
   - `benchmark-service` orchestration for benchmark run jobs.
   - Deterministic execution snapshots (runtime, backend, compiler/runtime flags, seeds).
   - Retry-safe run lifecycle states.

3. **Experiment registry and history**
   - Persistent storage for benchmark runs, parameters, artifacts, and aggregated metrics.
   - Search/filter by dataset, backend, runtime version, and time range.
   - Immutable run records with explicit contract versions.

4. **Comparison and analytics API**
   - Side-by-side run comparison (`A vs B`, `noise vs no-noise`, strategy deltas).
   - Statistical summary fields and confidence metadata.
   - History endpoint for trend inspection and regression spotting.

5. **CLI and operator UX**
   - `eigen benchmark run`
   - `eigen benchmark compare`
   - Human-readable and machine-readable output modes.

6. **Benchmark observability pack**
   - Metrics for benchmark queue depth, run duration, success/failure reasons.
   - Dashboards for throughput, stability, and benchmark quality gates.
   - Runbook for stalled runs, ingestion failures, and regression triage.

## Scope (out)

- Autonomous ML-driven optimizer decisions (Phase 4).
- Multi-region distributed benchmark federation (future distributed phases).
- Proprietary dataset hosting requirements.

## Exit criteria (Definition of Done)

1. Benchmark runs are reproducible from recorded run snapshots.
2. Dataset ingestion rejects invalid bundles and emits actionable errors.
3. Comparison API returns stable, versioned contracts and supports historical trend queries.
4. CLI covers run + compare flows with compatibility-tested outputs.
5. Observability dashboards and alert rules are available for benchmark SLOs.
6. Phase-3 RFC/ADR minimum package is merged and linked in docs.

## Versioning constraints

- Benchmark API envelopes, comparison schemas, and run-history DTOs are SemVer contracts.
- Breaking changes to run/comparison/history payloads require `MAJOR`.
- Backward-compatible optional fields use `MINOR`.
- Pure bugfixes and clarifications use `PATCH`.
- Every persisted run artifact includes explicit contract version markers.

## API/CLI targets

- API:
  - `/benchmarks/run`
  - `/benchmarks/compare`
  - `/benchmarks/history`
- CLI:
  - `eigen benchmark run`
  - `eigen benchmark compare`

## Dependencies and prerequisites

- Stable runtime execution contracts from MVP-3 (`RFC 0016/0017/0018`, ADR-0007).
- Phase-2 scheduler stability and observability baseline.
- Contract-test harness for benchmark API and CLI outputs.

## Deliverables map

1. Planning + backlog: this document + [`phase-3-issue-pack.md`](phase-3-issue-pack.md).
2. Governance package: [`phase-3-rfc-adr-gap-analysis.md`](phase-3-rfc-adr-gap-analysis.md) + RFCs `0020/0021/0022` in `rfcs/`.
3. Implementation slices: benchmark service, dataset pipeline, compare/history APIs, CLI commands.
4. Release closure package:
   - [`phase-3-release-readiness-checklist.md`](phase-3-release-readiness-checklist.md)
   - [`phase-3-compatibility-report.md`](phase-3-compatibility-report.md)
