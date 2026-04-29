# Phase 6 — Plugin Ecosystem Plan

## Status

- **Phase**: 6 (Post-MVP)
- **Planning status**: In planning (documentation baseline prepared)
- **Started on**: 2026-04-28
- **Last updated**: 2026-04-28
- **Previous phase closure**: [`phase-5-release-readiness-checklist.md`](phase-5-release-readiness-checklist.md), [`phase-5-compatibility-report.md`](phase-5-compatibility-report.md)
- **Execution backlog**: [`phase-6-issue-pack.md`](phase-6-issue-pack.md)
- **RFC/ADR coverage check**: [`phase-6-rfc-adr-gap-analysis.md`](phase-6-rfc-adr-gap-analysis.md)
- **RFC package (Draft)**: [`RFC 0029`](../../rfcs/0029-phase6-plugin-sdk-and-manifest-contract-v1.md), [`RFC 0030`](../../rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md), [`RFC 0031`](../../rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md)

## Goal

Make Eigen-OS a stable extension platform by introducing a versioned plugin contract, secure plugin lifecycle, and deterministic compatibility policy across runtime and Eigen-Lang surfaces.

## Scope (in)

1. **Plugin SDK and manifest contract**
   - Stable plugin manifest schema and capability model.
   - Plugin types: compiler pass, runtime backend adapter, observability exporter, and Eigen-Lang extension module.
   - Tooling contract for scaffold/validate/package commands.

2. **Plugin lifecycle and runtime isolation**
   - Discovery, registration, activation, deactivation, and rollback lifecycle.
   - Runtime isolation model for untrusted/third-party plugins.
   - Deterministic plugin ordering and conflict-resolution semantics.

3. **Compatibility and trust governance**
   - Compatibility matrix for Eigen-OS core version, plugin API version, and Eigen-Lang version.
   - Trust policy profile (signed/unsigned plugins, allowlists, policy gates).
   - Contract fixture suite to prevent silent plugin API drift.

4. **Eigen-Lang extension points**
   - Pluggable standard-library modules.
   - Custom workflow primitives registration contract.
   - Compiler hook contract for plugin-based analysis/transforms.

5. **Operator and developer docs**
   - Authoring guide, operator runbook, and migration guidance from built-in extensions.
   - Release closure templates for plugin-ecosystem milestone.

## Scope (out)

- Remote plugin marketplace/recommendation service.
- Dynamic hot-reload in production without restart boundaries.
- Multi-tenant monetization, billing, or commercial plugin policies.

## Exit criteria (Definition of Done)

1. Plugin manifest v1 schema is versioned, validated in CI, and documented.
2. Plugin lifecycle state machine is implemented with deterministic ordering and rollback coverage.
3. Runtime isolation guardrails (sandbox profile + capability checks) are enforced for third-party plugins.
4. Compatibility gate blocks unsupported plugin/core combinations at load time with actionable diagnostics.
5. Eigen-Lang extension hooks are documented and covered by conformance fixtures.
6. RFC package and issue pack are accepted and linked from roadmap/development indexes.

## Versioning constraints

- Plugin-facing contracts (manifest schema, lifecycle events, compatibility envelope) are SemVer-governed.
- Breaking changes to plugin API hooks or manifest required fields require `MAJOR`.
- Optional additive plugin metadata/capabilities use `MINOR`.
- `PATCH` releases are for bugfixes only and must not alter plugin compatibility semantics.
- Every loadable plugin artifact must include explicit `plugin_api_version` and `eigen_os_compatibility` markers.

## API/CLI targets

- CLI:
  - `eigen plugin scaffold`
  - `eigen plugin validate`
  - `eigen plugin package`
  - `eigen plugin install`
  - `eigen plugin list`
  - `eigen plugin doctor`
- APIs (internal + metadata surface):
  - plugin registry and loader interfaces
  - lifecycle event hooks
  - compatibility and trust evaluation API

## Dependencies and prerequisites

- Phase-5 distributed execution baseline and topology metadata.
- Existing release governance (RFC + ADR + compatibility reports).
- Security module policy enforcement primitives.

## Deliverables map

1. Planning + backlog: this document + [`phase-6-issue-pack.md`](phase-6-issue-pack.md).
2. Governance package: [`phase-6-rfc-adr-gap-analysis.md`](phase-6-rfc-adr-gap-analysis.md) + draft RFCs [`0029`](../../rfcs/0029-phase6-plugin-sdk-and-manifest-contract-v1.md), [`0030`](../../rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md), [`0031`](../../rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md).
3. Implementation slices: SDK/manifest, lifecycle/isolation, compatibility/trust, Eigen-Lang extensions.
4. Release closure package (to publish during execution):
   - `phase-6-release-readiness-checklist.md`
   - `phase-6-compatibility-report.md`

## Phase-6 default decisions (proposal baseline)

### 1) Packaging baseline

- Canonical artifact type: signed archive with `plugin.toml` manifest.
- Deterministic package hash is mandatory for install/verification flow.
- Plugin capabilities are declared explicitly and validated pre-load.

### 2) Load and conflict policy baseline

- Load order is deterministic by explicit priority, then plugin ID.
- Capability conflicts fail closed unless an explicit override policy is configured.
- Failed plugin activation cannot block core runtime bootstrap by default; plugin is isolated and marked `ERROR`.

### 3) Trust baseline

- Default policy profile in production: signed plugins only.
- Development profile may allow unsigned local plugins with explicit CLI flag.
- Trust evaluation output is persisted in structured logs for auditability.

### 4) Operational baseline targets (v1)

- Plugin discovery latency p95 target: `< 200ms` for up to 100 installed plugins.
- Plugin activation latency p95 target: `< 1s` for typical plugin type.
- Compatibility-check latency p95 target: `< 50ms` per plugin.

## Open inputs required from maintainers

To finalize implementation planning, maintainers still need to provide:

1. Preferred signing mechanism (`sigstore/cosign`, GPG, or internal CA).
2. Final sandbox strategy for plugin runtime isolation per language/runtime (Python/Rust).
3. Initial list of officially supported plugin types for Phase-6 GA (strict minimum set).
