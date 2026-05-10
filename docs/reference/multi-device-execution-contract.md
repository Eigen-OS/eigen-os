# Multi-device execution contract (Split/Merge)

**Status:** Phase-2 orchestration contract (runtime).

This document fixes the **current implemented contract state** for multi-device execution and also records known gaps for future phases.

## Versioning

- **Artifact version field:** `version` is mandatory in split manifests, partial results, partial failures, and merge decisions.
- **Current contract version:** `2.0.0` (`MULTI_DEVICE_EXECUTION_CONTRACT_VERSION`).
- **Breaking rule:** any incompatible change to partial-result/failure envelopes or merge semantics requires a **MAJOR** bump.
- **Compatibility rule:** additive optional fields/capabilities are **MINOR**.
- **Fixes only:** behavioral fixes that do not alter public semantics are **PATCH**.

## Split planner contract

Function: `plan_split(parent_job_id, tasks, max_shards) -> Result<SplitPlanManifest, SplitPlanError>`.

### Input

- `parent_job_id` — parent execution/job ID.
- `tasks[]` with:
  - `task_id`
  - `compatible_backends[]`
- `max_shards` — upper bound for allowed shard count.

### Output: `SplitPlanManifest`

- `version`
- `parent_job_id`
- `scheduler_decision_version`
- `shard_plans[]`:
  - `version`
  - `parent_job_id`
  - `shard_id`
  - `backend_id`
  - `task_ids[]`

### Planner guarantees (implemented)

1. Each shard artifact references both `parent_job_id` and unique `shard_id`.
2. Shard IDs are deterministic (`<parent>-shard-<NNN>`).
3. Backends are normalized (`trim`, sort, dedup) before selection.
4. Planner rejects:
   - empty/blank `parent_job_id`;
   - empty task set;
   - tasks without compatible backends (including blank-only backend lists);
   - plans exceeding `max_shards`;
   - `max_shards == 0`.
5. Backend choice is deterministic and currently picks the first backend in normalized lexical order.

### Current limitations / gaps

- Planner does not yet consume runtime backend health/capacity when picking backend per task.
- Planner does not yet emit per-shard resource hints (memory/latency/affinity budget).
- Planner does not validate task ID uniqueness or non-empty task IDs.
- Planner does not verify cross-artifact lineage/signature constraints for split manifests.

## Partial-result and partial-failure envelopes

### `PartialResultEnvelope`

- `version`
- `parent_job_id`
- `shard_id`
- `backend_id`
- `payload_ref`
- `payload_checksum`

### `PartialFailureEnvelope`

- `version`
- `parent_job_id`
- `shard_id`
- `backend_id`
- `reason_code` (`BackendUnavailable | ExecutionTimeout | ValidationFailed | InternalError`)
- `retryable`
- `message`

### Envelope invariants (implemented)

- Merge path enforces `parent_job_id` consistency across all incoming result/failure envelopes.
- Merge path enforces envelope uniqueness by `shard_id` across both result and failure streams.

### Current limitations / gaps

- No explicit runtime validation for `version` equality in merge path.
- No runtime schema-level checks for blank `backend_id`, `payload_ref`, `payload_checksum`, or `message`.
- No first-class envelope timestamp/attempt metadata yet (e.g., `attempt`, `emitted_at_ms`).

## Merge semantics and consistency checks

Function:
`merge_partial_results(parent_job_id, expected_shard_ids, results, failures, policy) -> MergeDecision`.

Checks before policy decision:

1. **Parent consistency:** every envelope must match target `parent_job_id`, otherwise reason = `ParentJobMismatch`.
2. **Uniqueness:** duplicate `shard_id` in results/failures is invalid, otherwise reason = `DuplicateShardEnvelope`.
3. **Coverage:** computes `missing_shard_ids` relative to `expected_shard_ids`.м

### Merge policies

- `AllShardsRequired`
  - success reason: `AllShardsMerged`
  - otherwise: `MissingExpectedShards`
- `Quorum { min_successful_shards }`
  - success reason: `QuorumSatisfied`
  - otherwise: `QuorumNotReached`

### Merge decision artifact

`MergeDecision` includes:

- `version`
- `parent_job_id`
- `reason_code`
- `merged_shard_ids[]`
- `failed_shard_ids[]`
- `missing_shard_ids[]`
- `failures[]` (standardized failure envelopes)

### Current limitations / gaps

- `AllShardsRequired` currently maps any non-successful complete merge to `MissingExpectedShards` (including cases with explicit shard failures); there is no dedicated reason code for "failed shards present but no missing shards".
- Merge path does not currently verify that every observed shard belongs to `expected_shard_ids` (unexpected shard IDs are not rejected).
- Quorum policy is count-based only; it does not weight shards by priority/cost.
- No tie-in yet to retry orchestration/backoff strategy in merge artifact itself.

## Test coverage (current)

Integration tests validate:

- split manifest generation and parent/shard references,
- planner validation failures for empty backend compatibility,
- standardized partial-failure envelope mapping,
- merge consistency behavior for all-required and quorum policies.

Additional tests present in the codebase also validate parent mismatch and duplicate-shard envelope handling.

## What is missing to fully fix system state

To consider the split/merge contract production-hardened, these items are still missing:

1. **Strict envelope validation layer**
   - enforce contract `version` checks at merge input;
   - enforce non-empty critical fields.
2. **Expected-shard membership enforcement**
   - reject result/failure envelopes for shard IDs outside manifest-derived expected set.
3. **Richer merge reason taxonomy**
   - add explicit reason codes for mixed outcomes (e.g., failures without missing shards).
4. **Planner quality signals**
   - integrate backend health/capacity and scheduling hints into backend selection.
5. **Operational metadata**
   - add attempt/timestamp/provenance fields to partial envelopes and propagate into merge decision for audit.
