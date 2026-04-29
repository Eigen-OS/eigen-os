# RFC 0029: Phase-6 Plugin SDK and Manifest Contract v1

- **Status**: Draft
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
- Standardize SDK developer workflows and contract fixtures.

## Non-Goals

- Hosted plugin marketplace.
- Dynamic remote plugin distribution protocol.
- Commercial licensing/subscription workflows.

## Guide-level Explanation

A plugin author runs `eigen plugin scaffold`, fills `plugin.toml`, implements extension hooks, and validates/package artifacts. At install/load time, Eigen-OS validates manifest schema + compatibility + trust policy before registration.

## Reference-level Design

### Package layout v1

```text
my-plugin/
  plugin.toml
  README.md
  LICENSE
  plugin/
    __init__.py
    hooks.py
  metadata/
    capabilities.json
```

### Required manifest fields

- `plugin_id` (reverse-DNS style)
- `name`
- `version` (SemVer)
- `plugin_api_version`
- `eigen_os_compatibility`
- `eigen_lang_compatibility` (optional but recommended)
- `capabilities` (explicit declared permissions)
- `entrypoints` (hook registration map)
- `signature` (required in trusted profiles)

### Plugin types (v1)

- `compiler_pass`
- `runtime_backend_adapter`
- `observability_exporter`
- `eigen_lang_extension`

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
- Plugin package hash and signature verification are evaluated before activation.
- Manifest must not include secrets; use runtime-managed secret stores.

## Observability

Required metrics:

- `plugin_manifest_validation_total`
- `plugin_manifest_validation_failures_total`
- `plugin_package_hash_mismatch_total`

Required logs:

- plugin ID/version
- validation outcome
- explicit reason codes for failures

## Performance

- Manifest validation target: `p95 < 20ms` per plugin.
- Bulk validation target: `p95 < 200ms` for 100 plugins.

## Benchmarking/Test Plan

- Schema fixture tests (positive + negative).
- Backward/forward compatibility tests for manifest versions.
- CLI golden tests for scaffold/validate/package workflow.

## Implementation / Migration

1. Publish `PluginManifestV1` schema and validator.
2. Add CLI/SDK commands for scaffold/validate/package.
3. Add CI contract fixtures for supported plugin types.
4. Document migration from built-in extension configs.

## Compatibility and Versioning

- **Version impact:** Introduces new plugin API baseline at `1.0.0`.
- **Compatibility:** Does not break non-plugin deployments.
- **Migration notes:** Existing bespoke extension configs should be translated into `plugin.toml`.

## Considered Alternatives

- Unstructured YAML manifests: rejected due to schema drift risk.
- Code-only registration without manifest: rejected due to weak governance and auditability.

## Open Questions

- Final manifest format choice (`TOML` vs `YAML`) if toolchain constraints arise.
- Minimum required metadata for security scanning integration.
