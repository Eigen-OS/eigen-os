# P9C-06 — Plugin SDK Policy Templates + Conformance Harness Update

## Contract versions

- Plugin manifest schema: `2.1.0` (MINOR from `2.0.0`)
- Plugin API version: `2.1.0` (MINOR from `2.0.0`)

## One-command policy-plugin workflow

```bash
eigen plugin scaffold ./my-policy policy && eigen plugin validate ./my-policy/plugin.toml
```

## Mandatory policy plugin manifest fields

Policy plugins are validated with additional required policy envelope fields:

- `[policy].reason_codes` (non-empty, `POLICY_*` reason-code taxonomy)
- `[policy].timeout_ms` (deterministic timeout budget, `10..=5000`)
- `[policy].fallback_mode` (`deterministic_kernel` or `deterministic_core`)

These checks are fail-closed and required for Stage-9C plugin conformance.

## Core vs extension hooks (SDK documentation split)

### Mandatory core interfaces

- Core scheduler determinism and fair-queueing baseline remain in kernel scope.
- Deterministic fallback path remains kernel-owned.

### Optional extension hooks

- Advanced policy behavior (tenant heuristics, backfill/preemption scoring)
  is plugin-owned via `plugin_type = "policy"` extension manifests.

## CI required gates

CI includes policy-plugin conformance checks as part of the CLI conformance job:

- `plugin_ga_types_contract_fixtures_are_accepted`
- `policy_manifest_requires_policy_contract_fields`
