# RFC 0030: Phase-6 Plugin Lifecycle and Runtime Isolation Contract v1

- **Status**: Draft
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-28
- **Target Milestone**: Phase 6
- **Tracking Issue**: P6-08 (docs/development/phase-6-issue-pack.md)
- **Replaces / Related**: docs/development/phase-6-plugin-ecosystem.md

## Summary

This RFC specifies deterministic plugin lifecycle semantics (discovery, registration, validation, activation, deactivation, rollback) and runtime isolation requirements for safe third-party plugin execution.

## Motivation

A plugin ecosystem requires predictable load behavior and strict isolation controls. Without a formal lifecycle and security boundaries, plugin failures can destabilize startup and expand attack surface.

## Goals

- Define lifecycle state machine and transition invariants.
- Define deterministic load-order and conflict handling semantics.
- Define isolation requirements and capability enforcement gates.

## Non-Goals

- Hot patching running plugin code in production.
- Multi-tenant billing/quotas for plugin resources.
- Cross-cluster plugin orchestration protocols.

## Guide-level Explanation

At startup, Eigen-OS discovers plugin artifacts, validates manifests/signatures/compatibility, computes deterministic load order, and activates eligible plugins. Failed plugins are isolated with explicit reason codes while core runtime remains healthy.

## Reference-level Design

### Lifecycle states

`DISCOVERED -> REGISTERED -> VALIDATED -> ACTIVE -> (DEACTIVATED | ERROR | QUARANTINED)`

Required behavior:

- `VALIDATED` requires successful schema + trust + compatibility checks.
- `ACTIVE` requires capability grant resolution.
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

### Isolation contract

- Plugin execution profile must restrict filesystem/network/process privileges according to declared capabilities.
- Runtime must enforce per-plugin timeout and memory budget defaults.
- Plugin panic/exception isolation must not crash core orchestration loop.

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
- Security violations produce immutable event records.

## Observability

Required metrics:

- `plugin_activation_total`
- `plugin_activation_failures_total`
- `plugin_quarantine_total`
- `plugin_activation_latency_ms`

Required trace attributes:

- `plugin.id`
- `plugin.version`
- `plugin.lifecycle_state`

## Performance

- Startup plugin activation budget target: `p95 < 1s` per plugin.
- Plugin failure isolation overhead target: negligible impact to non-plugin request path.

## Benchmarking/Test Plan

- State-machine conformance tests for legal/illegal transitions.
- Failure injection tests (timeout/crash/policy violations).
- Determinism tests for load ordering and conflict resolution.

## Implementation / Migration

1. Implement lifecycle state machine + persistence.
2. Implement isolation profile executor and capability checker.
3. Integrate with plugin loader and operator CLI diagnostics.
4. Add regression fixtures for lifecycle and security reason codes.

## Compatibility and Versioning

- **Version impact:** Introduces plugin lifecycle contract `1.0.0`.
- **Compatibility:** Core runtime behavior remains unchanged when plugins are disabled.
- **Migration notes:** Existing extension bootstrap logic should map to lifecycle state transitions.

## Considered Alternatives

- Best-effort activation without quarantine state: rejected for weak security posture.
- Non-deterministic parallel activation by default: rejected due to startup reproducibility risks.

## Open Questions

- Preferred sandbox implementation per runtime (Python subprocess, WASI, or container profile).
- Default policy for network access in `observability_exporter` plugin type.
