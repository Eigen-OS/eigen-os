# Multi-device execution contract (Split/Merge)

**Status:** Phase-2 orchestration contract (runtime).

## Versioning

- **Artifact version field:** `version` is mandatory in split manifests, partial results, partial failures, and merge decisions.
- **Current contract version:** `2.0.0` (`MULTI_DEVICE_EXECUTION_CONTRACT_VERSION`).
- **Breaking rule:** any incompatible change to partial-result/failure envelopes or merge semantics requires a **MAJOR** bump.
- **Compatibility rule:** additive optional fields/capabilities are **MINOR**.
- **Fixes only:** behavioral fixes that do not alter public semantics are **PATCH**.

## Split planner contract

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

### Planner guarantees

1. Each shard artifact references both `parent_job_id` and unique `shard_id`.
2. Shard IDs are deterministic (`<parent>-shard-<NNN>`).
3. Planner rejects tasks without compatible backends.
4. Planner rejects splits exceeding `max_shards`.

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

## Merge semantics and consistency checks

`merge_partial_results(...)` performs these checks before final reason-code selection:

1. **Parent consistency:** every envelope must match target `parent_job_id`.
2. **Uniqueness:** duplicate `shard_id` in results/failures is invalid.
3. **Coverage:** computes missing shard IDs relative to expected shard set.

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

## Test coverage

Integration tests validate:

- split manifest generation + parent/shard references,
- planner validation failures,
- standardized partial-failure envelope mapping,
- merge consistency behavior for all-required and quorum policies.
