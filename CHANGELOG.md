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

- Phase-2 orchestration documentation baseline: execution plan and a ready-to-copy GitHub issue pack for scheduler/device-aware/multi-device/batch workstreams.

### Changed

- Phase-1 is marked complete in roadmap and development planning docs with explicit closure date (**2026-04-27**).
- Product/service package versions advanced from `0.1.0` to `0.2.0` for post-Phase-1 release line.

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
