# Phase 6 — Plugin Ecosystem Plan

## Status

- **Phase**: 6 (Post-MVP)
- **Planning status**: In planning (security/runtime defaults fixed)
- **Started on**: 2026-04-28
- **Last updated**: 2026-04-29
- **Previous phase closure**: [`phase-5-release-readiness-checklist.md`](phase-5-release-readiness-checklist.md), [`phase-5-compatibility-report.md`](phase-5-compatibility-report.md)
- **Execution backlog**: [`phase-6-issue-pack.md`](phase-6-issue-pack.md)
- **RFC/ADR coverage check**: [`phase-6-rfc-adr-gap-analysis.md`](phase-6-rfc-adr-gap-analysis.md)
- **RFC package (Draft)**: [`RFC 0029`](../../rfcs/0029-phase6-plugin-sdk-and-manifest-contract-v1.md), [`RFC 0030`](../../rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md), [`RFC 0031`](../../rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md)

## Goal

Make Eigen-OS a stable extension platform by introducing a versioned plugin contract, strict runtime isolation, and deterministic compatibility/trust policy for GA plugin types.

## Scope (in)

1. **Plugin SDK and manifest contract**
   - Stable plugin manifest schema and capability model.
   - **Phase-6 GA plugin types (only):**
     - `driver` (simulators + hardware adapters),
     - `compiler_backend` (transpilation / IR backends),
     - `optimizer` (circuit / backend optimization passes).
   - Tooling contract for scaffold/validate/package commands.

2. **Plugin lifecycle and runtime isolation**
   - Discovery, registration, activation, deactivation, and rollback lifecycle.
   - **Only out-of-process OCI plugin runtime in gVisor (`runsc`) for GA**.
   - Deterministic plugin ordering and conflict-resolution semantics.

3. **Compatibility and trust governance**
   - Compatibility matrix for Eigen-OS core version, plugin API version, and Eigen-Lang version.
   - **Sigstore/Cosign as the single default signing and verification stack.**
   - Contract fixture suite to prevent silent plugin API drift.

4. **Operator and developer docs**
   - Authoring guide, operator runbook, and migration guidance from built-in extensions.
   - Release closure templates for plugin-ecosystem milestone.

## Scope (out)

- In-process Python/Rust plugin imports in GA.
- Remote plugin marketplace/recommendation service.
- Dynamic hot-reload in production without restart boundaries.
- Multi-tenant monetization, billing, or commercial plugin policies.
- Scheduler policy plugins in Phase-6 GA (remain core-configurable from Phase-4 baseline).

## Exit criteria (Definition of Done)

1. Plugin manifest v1 schema is versioned, validated in CI, and documented.
2. Plugin lifecycle state machine is implemented with deterministic ordering and rollback coverage.
3. Runtime isolation guardrails are enforced with mandatory `runsc` boundary.
4. Compatibility gate blocks unsupported plugin/core combinations at load time with actionable diagnostics.
5. Trust gate enforces Sigstore/Cosign verification (Fulcio/Rekor for public/community artifacts).
6. RFC package and issue pack are accepted and linked from roadmap/development indexes.

## Security and runtime defaults (locked for Phase-6 GA)

### 1) Signing and trust default

- **Default stack: Sigstore + Cosign only.**
- Public/community plugins use **keyless signing** via Fulcio certificates + Rekor transparency log entries.
- Signature identity must be verifiable and auditable from transparency evidence.
- Private/air-gapped deployments keep the same artifact format and verification contract, using self-hosted Sigstore or KMS/BYO PKI as trust root.

### 2) Sandbox default

- **Only out-of-process OCI plugins under gVisor (`runsc`) in GA.**
- Baseline hardening profile:
  - rootless container,
  - read-only filesystem,
  - no network by default,
  - dropped Linux capabilities,
  - explicit CPU/memory/pid limits.
- gVisor boundary is mandatory for untrusted plugin code.

### 3) GA plugin type baseline

- `driver`
- `compiler_backend`
- `optimizer`

Rationale: matches OSS roadmap extension areas (hardware drivers, compiler backends, optimizers) and keeps scheduler policy as core-configurable in Phase-6.

## Versioning constraints

- Plugin-facing contracts (manifest schema, lifecycle events, compatibility envelope) are SemVer-governed.
- Breaking changes to plugin API hooks or manifest required fields require `MAJOR`.
- Optional additive plugin metadata/capabilities use `MINOR`.
- `PATCH` releases are for bugfixes only and must not alter compatibility/trust semantics.
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
3. Implementation slices: SDK/manifest, lifecycle/isolation, compatibility/trust.
4. Release closure package (to publish during execution):
   - `phase-6-release-readiness-checklist.md`
   - `phase-6-compatibility-report.md`

## Open inputs still required from maintainers

1. Initial trusted identity issuers/subjects policy for keyless signatures.
2. Default OCI base image profile and allowed syscalls policy under `runsc`.
3. Admission policy for private/air-gapped trust roots (self-hosted Sigstore vs KMS/BYO PKI).
