# RFC 0029: Phase-6 Plugin SDK and Manifest Contract v1

- **Status**: Accepted
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-28
- **Target Milestone**: Phase 6
- **Tracking Issue**: P6-08 (docs/development/phase-6-issue-pack.md)
- **Replaces / Related**: docs/development/phase-6-plugin-ecosystem.md

## Summary

This RFC defines a stable v1 plugin authoring contract for Eigen-OS, including plugin package layout, manifest schema, declared capabilities, and SDK workflows for scaffold/validate/package.

## Motivation

Phase-6 introduces extension points beyond built-in runtime/compiler functionality. Without a clear plugin artifact and manifest contract, ecosystem growth will be fragile, incompatible across versions, and difficult to validate in CI.

## Goals

- Define canonical plugin package format and required manifest fields.
- Define plugin capability declaration model and schema validation.
- Fix Phase-6 GA plugin type set to `driver`, `compiler_backend`, `optimizer`.
- Standardize SDK developer workflows and contract fixtures.

## Non-Goals

- Hosted plugin marketplace.
- Dynamic remote plugin distribution protocol.
- Commercial licensing/subscription workflows.
- Additional GA plugin type families in Phase-6.

## Guide-level Explanation

A plugin author runs `eigen plugin scaffold`, fills `plugin.toml`, implements extension hooks, and validates/package artifacts. At install/load time, Eigen-OS validates manifest schema + compatibility + trust policy before registration.

## Reference-level Design

### Package layout v1

```text
my-plugin/
  plugin.toml
  README.md
  LICENSE
  plugin.oci.image.reference
  metadata/
    capabilities.json
```

### Required manifest fields

- `plugin_id` (reverse-DNS style)
- `name`
- `version` (SemVer)
- `plugin_type` (`driver | compiler_backend | optimizer`)
- `plugin_api_version`
- `eigen_os_compatibility`
- `eigen_lang_compatibility` (optional)
- `capabilities` (explicit declared permissions)
- `entrypoints` (hook registration map)
- `artifact_digest` (mandatory immutable digest)
- `signature_bundle_ref` (Cosign/Sigstore verification payload reference)

### Plugin types (Phase-6 GA)

- `driver` — simulators and hardware adapters.
- `compiler_backend` — transpilation/IR backends.
- `optimizer` — circuit/backend optimization passes.

`plugin_type` values outside this set are invalid for Phase-6.

## Interfaces / APIs

- CLI surface:
  - `eigen plugin scaffold`
  - `eigen plugin validate`
  - `eigen plugin package`
- SDK surface:
  - manifest schema validator
  - capability linter
  - contract fixture generator

## Data Models

- `PluginManifestV1`
- `PluginCapabilityDescriptorV1`
- `PluginEntrypointMapV1`

Versioning strategy:

- Manifest schema follows SemVer.
- Required-field removals/renames are `MAJOR`.
- Optional additive metadata is `MINOR`.

## Security and Privacy

- Capabilities are deny-by-default.
- Plugin package digest and Cosign/Sigstore verification payload are evaluated before activation.
- Manifest must not include secrets; use runtime-managed secret stores.

## Observability

Required metrics:

- `plugin_manifest_validation_total`
- `plugin_manifest_validation_failures_total`
- `plugin_package_hash_mismatch_total`

Required logs:

- plugin ID/version/type
- validation outcome
- explicit reason codes for failures

## Performance

- Manifest validation target: `p95 < 20ms` per plugin.
- Bulk validation target: `p95 < 200ms` for 100 plugins.

## Benchmarking/Test Plan

- Schema fixture tests (positive + negative).
- Backward/forward compatibility tests for manifest versions.
- CLI golden tests for scaffold/validate/package workflow.
- Type-enum conformance tests for GA type set.

## Implementation / Migration

1. Publish `PluginManifestV1` schema and validator.
2. Add CLI/SDK commands for scaffold/validate/package.
3. Add CI contract fixtures for each GA plugin type.
4. Document migration from built-in extension configs.

## Compatibility and Versioning

- **Version impact:** Contract baseline is `1.0.0` (stable) for Phase-6 plugin SDK/manifest artifacts.
- **Compatibility:** Required-field removals/renames require `MAJOR`; additive optional metadata and extension points use `MINOR`; bugfix clarifications only use `PATCH`.
- **Migration notes:** Existing bespoke extension configs should be translated into `plugin.toml`; every plugin artifact must include `plugin_api_version` and `eigen_os_compatibility`.

## Considered Alternatives

- Unstructured YAML manifests: rejected due to schema drift risk.
- Code-only registration without manifest: rejected due to weak governance and auditability.
- Broad plugin type surface in Phase-6: rejected to keep GA contract small and stable.

## Open Questions

- Exact mandatory/optional capability groups per GA plugin type.
