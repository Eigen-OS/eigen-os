# Phase-2 Migration Notes (`0.3.0`)

- **Status:** Signed migration package
- **Last updated:** 2026-04-27

## Summary

Phase-2 introduces scheduler/orchestration extensions while preserving compatibility for existing MVP/Phase-1 clients.

## Required actions

- **Mandatory migration:** None.

## Optional adoption actions

1. Consume dispatch explainability payloads (API/CLI) when needed for ops/debug.
2. Consume split/merge artifacts for multi-device workflows (`2.0.0` contract family).
3. Add monitoring for new orchestration metrics, including contract marker `eigen_orch_contract_info{version="2.3.0"}`.
4. If you use preemption analytics, ingest rebalancing/preemption artifacts (`2.2.0`) and counters.

## Compatibility statement

- Existing submit/status/results flows remain backward-compatible.
- Phase-2 additions are additive and version-marked.
- Breaking changes to scheduler semantics remain prohibited without MAJOR bump.

## Rollback guidance

If issues are observed after upgrade to `0.3.0`:

1. Disable optional orchestrator policy toggles (batch/rebalancing) in staged order.
2. Revert deployment to `0.2.x` line.
3. Keep compatibility fixtures and manifests for root-cause diff.
