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

- Project health documentation baseline: `CONTRIBUTING.md`, `SECURITY.md`, and roadmap/project-health alignment.
- Phase-1 release readiness checklist with consolidated security/performance/docs/upgrade gates and locked contract version matrix.
- Contract compatibility runner script: `scripts/test/run-contract-compatibility-suite.sh`.

### Changed

- Documentation now explicitly freezes MVP public API contract version at `0.1`, while clarifying that protobuf `...v1` remains a package/namespace convention.
- Pull request template now requires `Version Impact`, `Affected Interfaces`, and `Migration Notes`.
- CI includes a dedicated Phase-1 contract compatibility suite job.
- AQO simulator driver now enforces mandatory top-level `version` field.
