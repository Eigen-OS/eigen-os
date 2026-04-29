# RFC 0031: Phase-6 Plugin Compatibility and Trust Policy Contract v1

- **Status**: Draft
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-28
- **Target Milestone**: Phase 6
- **Tracking Issue**: P6-08 (docs/development/phase-6-issue-pack.md)
- **Replaces / Related**: docs/development/phase-6-plugin-ecosystem.md

## Summary

This RFC defines the load-time compatibility policy and trust-evaluation contract for plugins, including version matrix rules, signature policy profiles, and deterministic failure diagnostics.

## Motivation

Plugin ecosystems fail in production when version compatibility and trust checks are ad hoc. A formal contract is required to prevent unsafe or incompatible plugins from loading silently.

## Goals

- Define compatibility matrix semantics for core/plugin/language versions.
- Define trust-policy profiles and signature verification requirements.
- Define deterministic rejection reason codes and operator remediation paths.

## Non-Goals

- Public key infrastructure ownership decisions.
- End-user marketplace trust ratings.
- Commercial/legal plugin vetting workflows.

## Guide-level Explanation

Before activation, each plugin is evaluated against two gates:

1. **Compatibility gate:** confirms plugin API and Eigen-OS/Eigen-Lang version constraints.
2. **Trust gate:** confirms signature and policy profile requirements.

If either gate fails, plugin is blocked with a stable reason code and recommended remediation.

## Reference-level Design

### Compatibility matrix contract

Inputs:

- `core_version`
- `plugin_api_version`
- `eigen_lang_version` (if relevant)
- plugin-declared constraints (`>=`, `<`, compatible ranges)

Output:

- `SUPPORTED`
- `SUPPORTED_WITH_WARNINGS`
- `UNSUPPORTED`

### Trust policy profiles

- `prod`: signed plugins only, allowlist required for privileged capabilities.
- `staging`: signed preferred, explicit override allowed.
- `dev`: unsigned local plugins allowed with CLI flag and warning.

### Rejection reason code families

- `COMPAT_VERSION_MISMATCH`
- `COMPAT_UNSUPPORTED_PLUGIN_API`
- `TRUST_SIGNATURE_MISSING`
- `TRUST_SIGNATURE_INVALID`
- `TRUST_POLICY_DENIED`

## Interfaces / APIs

- Internal compatibility evaluator:
  - `evaluate_plugin_compatibility(plugin_manifest, runtime_versions)`
- Internal trust evaluator:
  - `evaluate_plugin_trust(plugin_manifest, policy_profile)`
- Operator CLI diagnostics:
  - `eigen plugin doctor --verbose`

## Data Models

- `PluginCompatibilityReportV1`
- `PluginTrustEvaluationV1`
- `PluginRejectionReasonCodeV1`

Versioning:

- Reason code set is append-only in `MINOR`; removals/semantic changes require `MAJOR`.

## Security and Privacy

- Signature verification uses configured trust roots and immutable audit logs.
- Policy overrides require explicit operator identity and timestamp.
- Trust decisions must be reproducible from logged inputs.

## Observability

Required metrics:

- `plugin_compatibility_reject_total`
- `plugin_trust_reject_total`
- `plugin_signature_verification_latency_ms`

Required logs:

- plugin ID/version
- evaluated profile
- compatibility/trust outcome
- rejection reason code

## Performance

- Compatibility gate target: `p95 < 50ms` per plugin.
- Trust gate target: `p95 < 100ms` per plugin (excluding remote key-fetch operations).

## Benchmarking/Test Plan

- Matrix fixtures for supported/unsupported version combinations.
- Signature verification success/failure test suite.
- Deterministic snapshot tests for reason-code outputs.

## Implementation / Migration

1. Introduce compatibility evaluator with fixture-driven tests.
2. Introduce trust-policy evaluator with profile-based behavior.
3. Add operator CLI diagnostics and remediation hints.
4. Integrate gates into plugin loader activation path.

## Compatibility and Versioning

- **Version impact:** Introduces policy contract baseline at `1.0.0`.
- **Compatibility:** Non-plugin runtime remains unaffected.
- **Migration notes:** Existing ad hoc extension trust checks should be replaced by policy profiles.

## Considered Alternatives

- Warning-only compatibility policy: rejected due to production safety risk.
- Implicit trust via local filesystem ownership only: rejected due to supply-chain risk.

## Open Questions

- Final signing stack choice for official releases.
- Policy for offline signature verification when trust-root refresh fails.
