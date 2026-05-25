# Multi-device Execution Contract (Split / Merge)

- **Status:** Stable runtime contract
- **Subsystem:** Distributed orchestration and execution coordination
- **Contract version:** `3.0.0`
- **Applies to:** Scheduler, Resource Manager, Runtime Workers, Merge Coordinator, QFS lineage layer
- **Last updated:** 2026-05-24

---

## 1. Purpose

This document defines the normative contract for multi-device execution in Eigen OS.

The contract governs:

- workload partitioning,
- shard planning,
- backend assignment,
- distributed execution,
- partial result collection,
- partial failure propagation,
- merge semantics,
- quorum policies,
- lineage consistency,
- retry-aware orchestration,
- deterministic replay behavior.

This contract applies to all runtime paths that execute a single logical job across multiple execution backends or workers.

Examples:

- multi-QPU execution,
- hybrid CPU/QPU execution,
- distributed simulation,
- batched backend execution,
- parallel optimization pipelines,
- federated runtime execution.

---

## 2. Design goals

The multi-device execution layer MUST provide:

1. Deterministic shard planning.
2. Stable execution lineage.
3. Replay-safe merge behavior.
4. Backend-independent execution semantics.
5. Failure-isolated shard execution.
6. Retry-safe partial execution.
7. Auditable orchestration artifacts.
8. Policy-driven merge completion.
9. Strong parent/shard consistency guarantees.
10. Eventually reproducible distributed execution outcomes.

---

## 3. Versioning and compatibility

### Contract version

```text
MULTI_DEVICE_EXECUTION_CONTRACT_VERSION = 3.0.0
```

All distributed orchestration artifacts MUST include:

```yaml
version: "3.0.0"
```

---

### SemVer policy

#### MAJOR

Required for:

- incompatible envelope changes,
- merge semantic changes,
- planner determinism changes,
- shard identity changes,
- lineage model changes.

#### MINOR

Used for:

- additive optional fields,
- new merge policies,
- additional metadata,
- new retry semantics,
- new orchestration hints.

#### PATCH

Used for:

- implementation fixes,
- deterministic bug fixes,
- documentation-only corrections.

---

## 4. Runtime architecture model

The distributed runtime pipeline is:

```text
Client
  ↓
Scheduler
  ↓
Split Planner
  ↓
Shard Manifests
  ↓
Distributed Runtime Workers
  ↓
Partial Results / Failures
  ↓
Merge Coordinator
  ↓
Final Result Artifact
```

Core components:

| **Component** | **Responsibility** |
|---|---|
| Split Planner | Creates deterministic shard plans |
| Scheduler | Assigns shards to execution backends |
| Runtime Worker | Executes shard payload |
| Resource Manager | Tracks leases/retries |
| Merge Coordinator | Validates and merges outcomes |
| QFS | Stores lineage and execution artifacts |

---

## 5. Split planner contract

### Function signature

```text
plan_split(
    parent_job_id,
    tasks,
    max_shards,
    policy
) -> Result<SplitPlanManifest, SplitPlanError>
```

---

## 6. Planner input contract

### Required input

`parent_job_id`

Stable parent execution identifier.

Requirements:

- non-empty,
- immutable,
- globally unique,
- replay-stable.

---

`tasks[]`

Each task MUST contain:

| **Field** | **Type** | **Required** |
|---|---|---|
| `task_id` | string | yes |
| `compatible_backends[]` | list<string> | yes |
| `estimated_cost` | int64 | no |
| `priority` | int32 | no |
| `affinity` | string | no |
| `resource_hints` | map<string,string> | no |

---

`max_shards`

Maximum allowed shard count.

Requirements:

- MUST be `> 0`,
- MUST remain within scheduler policy limits.

---

`policy`

Optional scheduler guidance:

```yaml
policy:
  placement_strategy: balanced|latency|throughput|cost
  retry_budget: 3
  affinity_mode: soft|hard
```

---

## 7. Split plan manifest

`SplitPlanManifest`

```yaml
version: "3.0.0"
parent_job_id: job-123
scheduler_decision_version: sched-v9
created_at_ms: 1716500000000

shard_plans:
  - version: "3.0.0"
    shard_id: job-123-shard-001
    backend_id: qpu-ionq
    task_ids:
      - task-a
      - task-b
```

---

### Required fields

| **Field** | **Description** |
|---|---|
| `version` | Contract version |
| `parent_job_id` | Parent execution ID |
| `scheduler_decision_version` | Scheduler snapshot identifier |
| `created_at_ms` | Manifest creation timestamp |
| `shard_plans[]` | Shard execution plans |

---

## 8. Shard plan contract

Each shard plan MUST contain:

| **Field** | **Description** |
|---|---|
| `version` | yes |
| `parent_job_id` | yes |
| `shard_id` | yes |
| `backend_id` | yes |
| `task_ids[]` | yes |
| `attempt` | yes |
| `lease_timeout_ms` | no |
| `resource_profile` | no |

---

## 9. Planner invariants

The planner MUST guarantee:

### Identity guarantees

1. Each shard has exactly one `shard_id`.
2. Each shard references exactly one `parent_job_id`.
3. Shard IDs are deterministic.

Canonical form:

```text
<parent>-shard-<NNN>
```

---

### Backend normalization

Backend identifiers MUST be:

- trimmed,
- normalized,
- deduplicated,
- lexically stable.

---

### Validation guarantees

Planner MUST reject:

- blank parent IDs,
- empty task sets,
- duplicate task IDs,
- tasks without valid backends,
- blank backend identifiers,
- invalid shard counts,
- plans exceeding `max_shards`.

---

### Determinism guarantees

Given identical:

- task ordering,
- scheduler inputs,
- backend topology,
- policy configuration,

the planner MUST produce identical manifests.

---

## 10. Backend selection semantics

Backend assignment MAY consider:

| **Signal** | **Supported** |
|---|---|
| Health score | yes |
| Capacity | yes |
| Latency | yes |
| Affinity | yes |
| Cost model | yes |
| Retry history | yes |
| Geographic locality | yes |

---

### Stable fallback behavior

If runtime intelligence is unavailable:

- deterministic lexical backend selection MUST be used.

This guarantees replay consistency.

---

## 11. Partial result envelope

`PartialResultEnvelope`

```yaml
version: "3.0.0"
parent_job_id: job-123
shard_id: job-123-shard-001
backend_id: qpu-ionq

attempt: 1
emitted_at_ms: 1716500000000

payload_ref: qfs://jobs/job-123/shards/001/result.bin
payload_checksum: sha256:abcd
trace_id: trace-xyz
```

---

## 12. Partial failure envelope

`PartialFailureEnvelope`

```yaml
version: "3.0.0"
parent_job_id: job-123
shard_id: job-123-shard-001
backend_id: qpu-ionq

attempt: 2
retryable: true

reason_code: BackendUnavailable
message: backend timeout

emitted_at_ms: 1716500000100
trace_id: trace-xyz
```

---

## 13. Standard failure reason codes

### Stable reason taxonomy

| **Reason code** | **Meaning** |
|---|---|
| `BackendUnavailable` | Backend unreachable |
| `ExecutionTimeout` | Runtime timeout |
| `ValidationFailed` | Invalid shard payload |
| `LeaseExpired` | Execution lease expired |
| `ResourceExhausted` | Capacity exhaustion |
| `DependencyFailure` | Upstream dependency failure |
| `InternalError` | Internal runtime failure |
| `ShardCancelled` | Scheduler cancellation |
| `ReplayRejected` | Determinism/replay mismatch |

---

## 14. Envelope invariants

The runtime MUST enforce:

### Parent consistency

All envelopes MUST match target parent_job_id.

--- 

### Uniqueness

shard_id MUST be unique across:

- result envelopes,
- failure envelopes,
- retry attempts.

### Version consistency

All envelopes MUST share identical contract version.

### Membership consistency

All shard IDs MUST belong to the expected manifest set.

Unexpected shard IDs MUST be rejected.

### Payload integrity

Checksums MUST match referenced payload artifacts.

---

## 15. Merge semantics

#### Function signature

```text
merge_partial_results(
    parent_job_id,
    expected_shard_ids,
    results,
    failures,
    policy
) -> MergeDecision
```

---

## 16. Merge validation stages

Before merge evaluation, the coordinator MUST validate:

### 1. Parent consistency

Reject mismatched parent IDs.

### 2. Envelope version consistency

Reject mixed-version envelopes.

### 3. Shard uniqueness

Reject duplicate shard IDs.

### 4. Membership validation

Reject unknown shard IDs.

### 5. Payload integrity

Verify checksums and artifact availability.

### 6. Coverage analysis

Compute:

- merged shards,
- failed shards,
- missing shards,
- retry-pending shards.

---

## 17. Merge policies

`AllShardsRequired`

Success requires:

```text
all expected shards completed successfully
```

Success reason:

```text
AllShardsMerged
```

Failure reasons:

- `MissingExpectedShards`
- `FailedShardsPresent`
- `MergeValidationFailed`

---

`Quorum`

Example:

```yaml
policy:
  type: quorum
  min_successful_shards: 3
```

Success reason:

```text
QuorumSatisfied
```

Failure reason:

```text
QuorumNotReached
```

---

`WeightedQuorum`

Optional advanced policy:

```yaml
policy:
  type: weighted_quorum
  minimum_weight: 0.75
```

Supports cost/priority-aware merges.

---

`BestEffort`

Allows merge with partial success.

Success reason:

```text
PartialMergeCompleted
```

---

## 18. Merge decision artifact

`MergeDecision`

```yaml
version: "3.0.0"

parent_job_id: job-123

reason_code: QuorumSatisfied

merged_shard_ids:
  - shard-001

failed_shard_ids:
  - shard-002

missing_shard_ids:
  - shard-003

retry_pending_shard_ids:
  - shard-004

failures:
  - reason_code: BackendUnavailable
```

---

## 19. Merge decision invariants

The merge coordinator MUST guarantee:

1. Deterministic merge outcome.
2. Stable reason-code mapping.
3. Replay-safe merge behavior.
4. Immutable lineage references.
5. Retry-safe shard accounting.
6. Audit-safe artifact preservation.

---

## 20. Retry and replay semantics

#### Retry behavior

Retries MUST preserve:

- `parent_job_id`,
- `shard_id`,
- lineage identity.

Only `attempt` increments.

---

### Replay guarantees

Replay MUST produce equivalent:

- shard topology,
- merge outcome,
- lineage graph,
- policy evaluation.

under identical scheduler conditions.

---

## 21. QFS lineage integration

The runtime MUST persist:

| **Artifact** | **Required** |
|---|---|
| Split manifest | yes |
| Partial results | yes |
| Partial failures | yes |
| Merge decisions | yes |
| Retry history | yes |
| Scheduler decisions | yes |

Canonical layout:

```text
qfs://jobs/<job_id>/
  split/
  shards/
  merge/
  lineage/
```

---

## 22. Observability integration

The distributed runtime SHOULD export:

| **Metric** | **Type** |
|---|---|
| `eigen_cluster_queue_backlog_depth` | gauge |
| `eigen_cluster_redeliveries_total` | counter |
| `eigen_cluster_dead_letter_total` | counter |
| `eigen_cluster_assignment_latency_ms` | histogram |
| `eigen_cluster_merge_failures_total` | counter |
| `eigen_cluster_shard_retries_total` | counter |

racing SHOULD preserve:

- `trace_id`,
- `parent_job_id`,
- `shard_id`,
- backend lineage.

---

## 23. Security and integrity

The runtime MUST support:

- signed manifests,
- lineage verification,
- checksum validation,
- immutable artifact references,
- replay tamper detection.

Future versions MAY add:

- shard attestation,
- backend trust scoring,
- cryptographic merge proofs.

---

## 24. Conformance requirements

An implementation is conformant only if it:

1. Produces deterministic shard plans.
2. Preserves parent/shard lineage.
3. Rejects invalid envelopes.
4. Enforces merge validation rules.
5. Preserves retry identity semantics.
6. Exports stable merge artifacts.
7. Maintains replay consistency.

---

## 25. Required test coverage

Conformance suites MUST validate:

- deterministic planner output,
- duplicate shard rejection,
- parent mismatch handling,
- unknown shard rejection,
- checksum validation,
- quorum semantics,
- retry lineage preservation,
- merge determinism,
- replay consistency,
- partial failure propagation.

---

## 26. Future evolution

Planned extensions include:

- adaptive shard balancing,
- dynamic shard resizing,
- speculative execution,
- runtime shard migration,
- weighted scheduling,
- federated orchestration,
- cryptographic lineage attestations,
- topology-aware merge policies.

---

## 27. Invariants

The following invariants are mandatory:

1. Every shard belongs to exactly one parent job.
2. Merge decisions are deterministic.
3. Retry attempts preserve lineage identity.
4. Unknown shards are rejected.
5. Duplicate shard envelopes are invalid.
6. Payload integrity violations invalidate merge eligibility.
7. Merge policies MUST be replay-safe.
8. Distributed execution MUST remain auditable.
