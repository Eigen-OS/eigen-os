# RFC 0030: Phase-6 Plugin Lifecycle and Runtime Isolation Contract v1

- **Status**: Draft
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-28
- **Target Milestone**: Phase 6
- **Tracking Issue**: P6-03 (docs/development/phase-6-issue-pack.md)
- **Replaces / Related**: docs/development/phase-6-plugin-ecosystem.md

## Summary

This RFC specifies deterministic plugin lifecycle semantics (discovery, registration, validation, activation, deactivation, rollback) and runtime isolation requirements for safe third-party plugin execution.

## Motivation

A plugin ecosystem requires predictable load behavior and strict isolation controls. Without a formal lifecycle and security boundaries, plugin failures can destabilize startup and expand attack surface.

## Goals

- Define lifecycle state machine and transition invariants.
- Define deterministic load-order and conflict handling semantics.
- Define mandatory sandbox boundary for GA: out-of-process OCI plugins under gVisor `runsc`.

## Non-Goals

- In-process Python/Rust plugin imports in GA.
- Hot patching running plugin code in production.
- Multi-tenant billing/quotas for plugin resources.
- Cross-cluster plugin orchestration protocols.

## Guide-level Explanation

At startup, Eigen-OS discovers OCI plugin artifacts, validates manifests/signatures/compatibility, computes deterministic load order, and activates eligible plugins in isolated gVisor sandboxes. Failed plugins are isolated with explicit reason codes while core runtime remains healthy.

## Reference-level Design

### Lifecycle states

`DISCOVERED -> REGISTERED -> VALIDATED -> ACTIVE -> (DEACTIVATED | ERROR | QUARANTINED)`

Required behavior:

- `VALIDATED` requires successful schema + trust + compatibility checks.
- `ACTIVE` requires capability grant resolution and sandbox profile validation.
- `ERROR` plugins cannot execute hooks until explicit operator action.
- `QUARANTINED` is mandatory for security-policy violations.

### Deterministic load ordering

Sort key:

1. `priority` (ascending),
2. `dependency depth`,
3. `plugin_id` lexical order.

Conflicts:

- unresolved capability conflicts fail closed;
- optional override policy must be explicit and auditable.

### Isolation contract (mandatory GA profile)

- Only OCI artifacts are loadable plugin runtime units.
- Runtime boundary is mandatory: gVisor `runsc`.
- Any activation request that resolves to an in-process runtime is rejected with reason code `PLUGIN_RUNTIME_IN_PROCESS_FORBIDDEN`.
- Baseline sandbox profile:
  - rootless execution,
  - read-only filesystem,
  - network disabled by default,
  - dropped capabilities,
  - explicit CPU/memory/pid limits.
- Plugin panic/exception isolation must not crash core orchestration loop.

### Activation policy enforcement (GA hard requirement)

Activation is fail-closed and MUST enforce runtime boundary before hook execution:

1. Resolve artifact type; non-OCI artifacts are rejected with `PLUGIN_ARTIFACT_TYPE_UNSUPPORTED`.
2. Resolve runtime implementation; any runtime other than `runsc` is rejected with `PLUGIN_RUNTIME_BOUNDARY_REQUIRED`.
3. Validate sandbox profile; profile violations are rejected with `PLUGIN_SANDBOX_PROFILE_VIOLATION`.
4. Emit structured audit event + metrics for every rejection.
5. Transition plugin lifecycle state to `QUARANTINED` for security-policy violations.

## Interfaces / APIs

- Internal loader interfaces:
  - `discover_plugins()`
  - `validate_plugin(plugin_id)`
  - `activate_plugin(plugin_id)`
  - `deactivate_plugin(plugin_id)`
  - `quarantine_plugin(plugin_id, reason)`
- Operator surface:
  - `eigen plugin list`
  - `eigen plugin doctor`

## Data Models

- `PluginLifecycleEventV1`
- `PluginActivationRecordV1`
- `PluginIsolationProfileV1`

Versioning:

- Lifecycle event schema and reason codes are SemVer-governed.

## Security and Privacy

- Deny-by-default capability model.
- Mandatory audit logs for activation, deactivation, quarantine, and override actions.
- Sandbox policy violations produce immutable event records.

## Observability

Required metrics:

- `plugin_activation_total`
- `plugin_activation_failures_total`
- `plugin_quarantine_total`
- `plugin_activation_latency_ms`
- `plugin_sandbox_policy_reject_total`
- `plugin_runtime_boundary_reject_total`
- `plugin_in_process_reject_total`

Required trace attributes:

- `plugin.id`
- `plugin.version`
- `plugin.lifecycle_state`
- `plugin.runtime`
- `plugin.reject_reason`

## Performance

- Startup plugin activation budget target: `p95 < 1s` per plugin.
- Plugin failure isolation overhead target: negligible impact to non-plugin request path.

## Benchmarking/Test Plan

- State-machine conformance tests for legal/illegal transitions.
- Failure injection tests (timeout/crash/policy violations).
- Determinism tests for load ordering and conflict resolution.
- Sandbox profile conformance tests against baseline hardening policy.

## Implementation / Migration

1. Implement lifecycle state machine + persistence.
2. Implement OCI runtime executor on `runsc` and baseline sandbox profile.
3. Integrate with plugin loader and operator CLI diagnostics.
4. Add regression fixtures for lifecycle and security reason codes.

## Compatibility and Versioning

- **Version impact:** Introduces sandbox-boundary enforcement update for plugin lifecycle contract `2.0.0`.
- **Compatibility:** Core runtime behavior remains unchanged when plugins are disabled.
- **Migration notes:** Existing extension bootstrap logic must remove in-process loading paths and package all loadable plugins as OCI artifacts runnable under `runsc`.

## Considered Alternatives

- In-process imports: rejected due to isolation risk.
- Best-effort activation without quarantine state: rejected for weak security posture.
- Non-deterministic parallel activation by default: rejected due to startup reproducibility risks.

## Open Questions

- Exact default resource limits per plugin type for GA environments.
