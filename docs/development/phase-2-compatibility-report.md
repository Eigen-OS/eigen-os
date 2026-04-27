# Phase-2 Compatibility Report

- **Status:** Required for marking Phase-2 release as Ready.
- **Last updated:** 2026-04-27
- **Owner:** Orchestration maintainers

## Contract version matrix

| Contract surface | Current version | Compatibility notes |
| --- | --- | --- |
| Scheduler decision DTOs | `2.1.0` | Breaking queue/dispatch semantics require MAJOR bump. |
| Device score dispatch DTOs | `2.1.0` | Reason-code additions are MINOR-only when backward compatible. |
| Rebalancing/preemption artifacts | `2.2.0` | Guardrail semantics and reason-codes follow SemVer policy. |
| Multi-device split/merge manifests | `2.0.0` | Parent-job/shard envelopes are stable and versioned. |

## Compatibility suite evidence

- Scheduler contract suite: `cargo test -p resource-manager --test scheduler_contract_compatibility`
- Runtime contract suite: `bash scripts/test/run-contract-compatibility-suite.sh`
- Golden fixture review gate: `golden-fixtures-approved` label required when fixture snapshots change.

## Migration policy

Every contract-affecting PR must include:

1. **Version Impact** (`MAJOR`/`MINOR`/`PATCH`/`NONE`)
2. **Compatibility** statement in the PR description
3. **Migration Notes** (actionable steps or explicit `None`)

## Release readiness

A Phase-2 release is **not Ready** until this report is reviewed and updated in the release PR.
