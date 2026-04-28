# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Versioning Policy (SemVer)

Eigen OS uses `MAJOR.MINOR.PATCH`:

- **MAJOR**: incompatible API/protocol or behavior changes
- **MINOR**: backward-compatible functionality additions
- **PATCH**: backward-compatible bug fixes and documentation-only corrections

Before `1.0.0`, breaking changes may occur in minor versions. After `1.0.0`, breaking changes require a MAJOR version increment.

## [Unreleased]

### Added

- Phase-4 P4-07 deterministic replay quality gate (`resource-manager` package `0.7.0`) with recorded decision-replay fixtures for scoring/policy/explain artifacts, drift-detection diagnostics, and CI gate script for deterministic runtime regression blocking.
- Phase-4 P4-06 intelligent runtime observability pack (`runtime-observability` assets `0.1.0`) with stable `eigen_runtime_*` metrics contract (`1.0.0`), decision-flow dashboard, Prometheus alerts, and triage/rollback runbook.
- Phase-4 P4-02 scheduling policy engine and policy bundles (`resource-manager` package `0.5.0`) with versioned `PolicyBundle` schema (`1.0.0`), deterministic precedence-based resolution, and safe fallback artifacts for missing/invalid policy inputs.
- Phase-4 P4-05 Eigen-Lang runtime-intelligence compile hints/diagnostics (`cli` in Rust workspace `0.6.0`) with deterministic unsupported-target/policy-conflict diagnostics, explicit hint metadata versions, and explainability-linked execution annotations in AQO metadata.
- Phase-3 P3-08 reproducibility and determinism quality gate (`benchmark-service` package `0.7.0`) with versioned reproducibility policy thresholds (`1.0.0`), deterministic snapshot consistency checks, bounded metric variance checks, and CI drift diagnostics.
- Phase-3 P3-07 benchmark observability pack (`benchmark-service` package `0.6.0`) with stable `eigen_bench_*` metrics contract (`1.0.0`), benchmark lifecycle dashboard, Prometheus alerts, and triage runbook.
- Phase-3 P3-06 CLI benchmark UX: `eigen benchmark run` and `eigen benchmark compare` (Rust CLI package `0.4.0`) with stable JSON/human output modes, explicit output version markers, and compatibility fixtures.
- Phase-3 P3-05 benchmark history API (`/benchmarks/history`) and trend queries (`benchmark-service` package `0.5.0`) with validated time-range filters, deterministic pagination, and stable ordering guarantees.
- Phase-3 P3-03 benchmark run API contract (`/benchmarks/run`) and compatibility fixtures (`benchmark-service` package `0.3.0`) with stable request/response/error envelopes and explicit artifact version markers.
- Phase-3 P3-01 benchmark-service core (`benchmark-service` package `0.1.0`) with run lifecycle state machine, idempotent start/retry semantics, and immutable deterministic snapshot metadata.
- RFC 0020 and ADR 0008 for benchmark run lifecycle contract governance.
- Phase-3 P3-09 RFC package for benchmark contracts (run lifecycle, dataset ingestion, compare/history) with explicit statuses and indexed docs links (RFC 0020/0021/0022).
- Phase-3 P3-02 QSBench-compatible dataset ingestion pipeline (`benchmark-service` package `0.2.0`) with manifest schema validation, checksum/provenance verification, and queryable dataset version catalog.

### Phase-3: RFC Package for Contracts (P3-09)

- **Version impact:** MINOR (governance package completion; benchmark-service package advanced to `0.8.0`).
- **Compatibility:** No payload or behavior break; stable contract baselines remain `1.0.0` for run (`state/snapshot`), dataset ingestion (`manifest/ingestion`), compare (`comparison/methodology`), and history (`history_contract_version`).
- **Migration notes:** No mandatory migration. Teams should pin and validate explicit version markers in run snapshots, ingestion artifacts, compare outputs, and history entries.

### Phase-4: Observability Pack for Intelligent Runtime (P4-06)

- **Version impact:** MINOR (adds new intelligent-runtime observability contract/assets; observability asset pack advanced to `0.1.0`).
- **Compatibility:** Additive; existing `eigen_orch_*`, `eigen_stage_*`, and `eigen_bench_*` contracts remain unchanged while `eigen_runtime_*` metrics are introduced with explicit marker `eigen_runtime_contract_info{version="1.0.0"}`.
- **Migration notes:** No mandatory migration. Operators should import `monitoring/dashboards/intelligent_runtime_dashboard.json`, load `monitoring/metrics/prometheus/intelligent-runtime-alerts.yaml`, and adopt `docs/howto/intelligent-runtime-observability-runbook.md`.

### Phase-4: Scheduling Policy Engine and Policy Bundles (P4-02)

- **Version impact:** MINOR (new scheduling policy contract surface; Rust workspace package advanced to `0.5.0`).
- **Compatibility:** Additive; existing scheduler admission/dispatch and backend scoring contracts remain unchanged.
- **Migration notes:** No mandatory migration for default behavior. Policy adopters should pin `policy_bundle_version` and consume `SCHEDULING_POLICY_*` version markers in decision artifacts.

### Phase-4: Eigen-Lang Runtime-Intelligence Hints and Diagnostics (P4-05)

- **Version impact:** MINOR (new compile metadata and diagnostics; Rust workspace package advanced to `0.6.0`).
- **Compatibility:** Additive; existing AQO core fields remain unchanged while runtime-intelligence metadata/annotations are added and diagnostics are deterministic.
- **Migration notes:** No mandatory migration. Consumers should pin `metadata.runtime_intelligence_hints.version`, `metadata.runtime_intelligence_hints.diagnostics_version`, and `metadata.execution_annotations.version`, and treat `RUNTIME_INTELLIGENCE_DIAGNOSTIC` as compile-time validation feedback.

### Phase-4: Determinism and Reproducibility Gate for Runtime Decisions (P4-07)

- **Version impact:** MINOR (new deterministic replay fixture suite + CI drift gate; Rust workspace package advanced to `0.7.0`).
- **Compatibility:** Additive quality gate only; scoring contract (`1.0.0`), policy bundle schema (`1.0.0`), policy-resolution artifact (`1.0.0`), and explain response/request envelopes (`1.0.0`) remain unchanged.
- **Migration notes:** No API migration required. CI pipelines should execute `scripts/ci/check-runtime-decision-determinism.sh` (or `scripts/test/run-scheduler-contract-compatibility-suite.sh`) to block uncontrolled decision drift and surface field-level diagnostics.

### Phase-3: Reproducibility and Determinism Gate (P3-08)

- **Version impact:** MINOR (adds reproducibility policy contract and CI quality gate; benchmark-service package advanced to `0.7.0`).
- **Compatibility:** Additive; existing `/benchmarks/run`, `/benchmarks/compare`, `/benchmarks/history`, and dataset ingestion contracts remain unchanged.
- **Migration notes:** No mandatory migration. CI should execute `scripts/ci/check-benchmark-reproducibility.sh`; operators can consume gate diagnostics (`code`, `field`, `message`) for drift triage.

### Phase-3: Benchmark Metrics, Dashboards, and Alerts Pack (P3-07)

- **Version impact:** MINOR (adds benchmark observability contract surface and operator assets; benchmark-service package advanced to `0.6.0`).
- **Compatibility:** Additive; existing `/benchmarks/run` (`1.0.0`), `/benchmarks/compare` (`1.0.0`), `/benchmarks/history` (`1.0.0`), and dataset ingestion (`1.0.0`) contracts remain unchanged.
- **Migration notes:** No mandatory migration. Operators should import `monitoring/dashboards/benchmark_dashboard.json`, load `monitoring/metrics/prometheus/benchmark-alerts.yaml`, and adopt `docs/howto/benchmark-observability-runbook.md`.

### Phase-3: CLI UX run/compare (P3-06)

- **Version impact:** MINOR (adds benchmark CLI surface and stable JSON contracts; Rust CLI package advanced to `0.4.0`).
- **Compatibility:** Additive; existing CLI commands and benchmark service API contracts remain unchanged.
- **Migration notes:** No mandatory migration. Automation consuming benchmark CLI output should pin to `contract_version`/`snapshot_version`/`comparison_version` and prefer `--output json` artifacts.

### Phase-3: History API and Trend Queries (P3-05)

- **Version impact:** MINOR (adds `/benchmarks/history` contract surface and trend query aggregates; package version advanced to `0.5.0`).
- **Compatibility:** Additive; existing `/benchmarks/run` (`1.0.0`), `/benchmarks/compare` (`1.0.0`), and dataset ingestion contracts remain unchanged.
- **Migration notes:** No mandatory migration. Consumers can adopt deterministic cursor pagination (`page_token`) and rely on stable ordering contract `created_at DESC, run_id ASC`.

### Phase-3: Benchmark Service Core v1 (P3-01)

- **Version impact:** MINOR (new service capability + new stable lifecycle contract `1.0.0`).
- **Compatibility:** Additive; no breaking changes to existing runtime services/APIs.
- **Migration notes:** No migration required for existing clients.

## [0.3.0]

### Phase-3: Benchmark Run API Contract Tests (P3-03)

- **Version impact:** MINOR (new `/benchmarks/run` contract surface and conformance fixtures).
- **Compatibility:** Additive; no breaking changes to existing benchmark lifecycle (`1.0.0`) or dataset ingestion (`1.0.0`) contracts.
- **Migration notes:** No mandatory migration. API consumers should validate against the new documented required request fields (`idempotency_key`, `config`) and rely on explicit response version markers.

### Phase-3: Dataset Ingestion Pipeline (P3-02)

- **Version impact:** MINOR (adds new dataset ingestion + catalog capability and stable manifest schema contract `1.0.0`).
- **Compatibility:** Additive; existing benchmark run lifecycle contract `1.0.0` is unchanged.
- **Migration notes:** No mandatory migration. Producers must include `manifest.json` with required provenance/checksum fields for ingestion.

### Added

- Phase-2 orchestration documentation baseline: execution plan and a ready-to-copy GitHub issue pack for scheduler/device-aware/multi-device/batch workstreams.
- Phase-2 release readiness checklist with locked orchestration contract version matrix and signed compatibility/migration package.
- Phase-2 migration notes and release notes template with mandatory `Version impact`, `Compatibility`, and `Migration notes` sections.

### Changed

- Phase-1 is marked complete in roadmap and development planning docs with explicit closure date (**2026-04-27**).
- Product/service package versions advanced from `0.2.0` to `0.3.0` for Phase-2 release closure.

### Added

- Project health documentation baseline: `CONTRIBUTING.md`, `SECURITY.md`, and roadmap/project-health alignment.
- Phase-1 release readiness checklist with consolidated security/performance/docs/upgrade gates and locked contract version matrix.
- Contract compatibility runner script: `scripts/test/run-contract-compatibility-suite.sh`.
- Observability v2 per-job timeline persisted to QFS (`qfs_job_timeline`) with explicit timeline schema version (`2.0.0`) and trace correlation metadata (`trace_id`, `trace_ref`).

### Changed

- Documentation now explicitly freezes MVP public API contract version at `0.1`, while clarifying that protobuf `...v1` remains a package/namespace convention.
- Pull request template now requires `Version Impact`, `Affected Interfaces`, and `Migration Notes`.
- CI includes a dedicated Phase-1 contract compatibility suite job.
- AQO simulator driver now enforces mandatory top-level `version` field.
- System API job lifecycle stream now emits detailed stages (`QUEUED` → `COMPILED` → `DISPATCHED` → `RUNNING` → `COMPLETED`) with timestamped event history and trace-aware event messages

### Phase-2: Dispatch Explainability API/CLI

- **Version impact:** MINOR (new backward-compatible RPC + CLI command + docs).
- **Compatibility:** Existing `JobService` methods and reason codes remain intact; dispatch explainability is additive.
- **Migration notes:** No migration required. Clients may optionally call `GetDispatchRationale` and CLI `eigen explain <job_id>`.

### Phase-2: Multi-device Execution Contract (Split/Merge)

- **Version impact:** MINOR (adds a new split/merge contract artifact family and integration coverage).
- **Compatibility:** Existing scheduler admission/dispatch DTOs are unchanged; split/merge envelopes are additive and independently versioned (`2.0.0`).
- **Migration notes:** No mandatory migration. Consumers may start reading `SplitPlanManifest`, `PartialResultEnvelope`, `PartialFailureEnvelope`, and `MergeDecision` artifacts with explicit `version`, `parent_job_id`, and `shard_id` fields.

### Phase-2: Rebalancing and Preemption Safety Rules

- **Version impact:** MINOR (adds rebalance/preemption policy artifacts and idempotent requeue behavior with explicit version marker `2.2.0`).
- **Compatibility:** Existing admission/dispatch reason codes remain intact; new preemption reason codes and metrics are additive. Terminal/preempted status semantics are unchanged.
- **Migration notes:** No mandatory migration. Integrations can optionally consume `RebalancePlan`/`PreemptionDecision` and the new scheduler metrics (`rebalance_trigger_total`, `preemption_attempted_total`, `preempted_total`, `requeued_total`, `requeue_idempotent_hits_total`).

### Phase-2: Orchestration Observability Pack

- **Version impact:** MINOR (adds a new stable observability metric family, orchestrator dashboard, alerts, and runbook).
- **Compatibility:** Existing stage observability metrics remain unchanged; new `eigen_orch_*` metrics are additive and version-marked via `eigen_orch_contract_info{version="2.3.0"}`.
- **Migration notes:** No mandatory migration. Operators should import `monitoring/dashboards/orchestration_dashboard.json`, load `monitoring/metrics/prometheus/orchestrator-alerts.yaml`, and wire orchestrator scrape target (`127.0.0.1:9094`).
