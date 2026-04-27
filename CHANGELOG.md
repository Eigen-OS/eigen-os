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

- Placeholder for upcoming changes.

## [0.3.0] - 2026-04-27

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
