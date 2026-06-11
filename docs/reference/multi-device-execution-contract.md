# Multi-device Execution Contract (Split / Merge)

- **Status:** Stable runtime contract
- **Subsystem:** Distributed orchestration and execution coordination
- **Contract version:** `3.1.0`
- **Applies to:** Scheduler, Resource Manager, Runtime Workers, Merge Coordinator, QFS lineage layer, Explainability subsystem, Observability exporters
- **Last updated:** 2026-05-27

---

# 1. Purpose

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
- deterministic replay behavior,
- observability semantics,
- explainability lineage,
- runtime trace propagation,
- backend normalization.

This contract applies to all runtime paths that execute a single logical job across multiple execution backends or workers.

Examples:

- multi-QPU execution,
- hybrid CPU/QPU execution,
- distributed simulation,
- batched backend execution,
- parallel optimization pipelines,
- federated runtime execution,
- heterogeneous accelerator orchestration,
- speculative distributed execution.

---

# 2. Design Goals

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
11. Stable runtime observability.
12. Deterministic error semantics.
13. Explainable scheduling decisions.
14. Trace-safe distributed coordination.
15. Cross-service conformance consistency.

---

# 3. Versioning and Compatibility

## 3.1 Contract Version

```text
MULTI_DEVICE_EXECUTION_CONTRACT_VERSION = 3.1.0
```

All distributed orchestration artifacts MUST include:

```yaml
version: "3.1.0"
```

---

## 3.2 SemVer Policy

### MAJOR

Required for:

- incompatible envelope changes,
- merge semantic changes,
- planner determinism changes,
- shard identity changes,
- lineage model changes,
- replay semantic changes.

### MINOR

Used for:

- additive optional fields,
- new merge policies,
- additional metadata,
- new retry semantics,
- new orchestration hints,
- additive observability fields.

### PATCH

Used for:

- implementation fixes,
- deterministic bug fixes,
- documentation-only corrections,
- telemetry corrections without semantic changes.

---

# 4. Runtime Architecture Model

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
| Explainability Layer | Produces execution rationale |
| Telemetry Exporter | Emits runtime metrics and traces |

---

# 5. Core Execution Model

A distributed execution consists of:

1. parent job definition,
2. deterministic split planning,
3. backend assignment,
4. shard execution,
5. partial result collection,
6. merge coordination,
7. lineage persistence,
8. replay-safe artifact preservation.

A parent execution MUST remain logically immutable once planning begins.

---

# 6. Split Planner Contract

## 6.1 Function Signature

```text
plan_split(
    parent_job_id,
    tasks,
    max_shards,
    policy
) -> Result<SplitPlanManifest, SplitPlanError>
```

---

# 7. Planner Input Contract

## 7.1 Required Input

### `parent_job_id`

Stable parent execution identifier.

Requirements:

- non-empty,
- immutable,
- globally unique,
- replay-stable,
- trace-correlatable.

---

### `tasks[]`

Each task MUST contain:

| **Field** | **Type** | **Required** |
|---|---|---|
| `task_id` | string | yes |
| `compatible_backends[]` | list<string> | yes |
| `estimated_cost` | int64 | no |
| `priority` | int32 | no |
| `affinity` | string | no |
| `resource_hints` | map<string,string> | no |
| `deterministic_hash` | string | no |
| `retry_policy` | object | no |

---

### `max_shards`

Maximum allowed shard count.

Requirements:

- MUST be `> 0`,
- MUST remain within scheduler policy limits,
- MUST remain replay-stable.

---

### `policy`

Optional scheduler guidance:

```yaml
policy:
  placement_strategy: balanced|latency|throughput|cost
  retry_budget: 3
  affinity_mode: soft|hard
  merge_policy: all|required|quorum|weighted_quorum|best_effort
```

---

# 8. Split Plan Manifest

`SplitPlanManifest`

```yaml
version: "3.1.0"
parent_job_id: job-123
scheduler_decision_version: sched-v9
created_at_ms: 1716500000000
trace_id: trace-xyz

shard_plans:
  - version: "3.1.0"
    parent_job_id: job-123
    shard_id: job-123-shard-001
    backend_id: qpu-ionq
    task_ids:
      - task-a
      - task-b
    attempt: 1
    lease_timeout_ms: null
    resource_profile: null
    trace_id: trace-xyz
    lineage_ref: qfs://jobs/job-123/lineage/job-123-shard-001.json
```

---

## 8.1 Required Fields

| **Field** | **Description** |
|---|---|
| `version` | Contract version |
| `parent_job_id` | Parent execution ID |
| `scheduler_decision_version` | Scheduler snapshot identifier |
| `created_at_ms` | Manifest creation timestamp |
| `trace_id` | Distributed trace correlation |
| `shard_plans[]` | Shard execution plans |

---

# 9. Shard Plan Contract

Each shard plan MUST contain:

| **Field** | **Required** |
|---|---|
| `version` | yes |
| `parent_job_id` | yes |
| `shard_id` | yes |
| `backend_id` | yes |
| `task_ids[]` | yes |
| `attempt` | yes |
| `lease_timeout_ms` | no |
| `resource_profile` | no |
| `trace_id` | yes |
| `lineage_ref` | no |

---

# 10. Planner Invariants

The planner MUST guarantee:

## 10.1 Identity Guarantees

1. Each shard has exactly one `shard_id`.
2. Each shard references exactly one `parent_job_id`.
3. Shard IDs are deterministic.
4. Parent lineage remains immutable.

Canonical form:

```text
<parent>-shard-<NNN>
```

---

## 10.2 Backend Normalization

Backend identifiers MUST be:

- trimmed,
- normalized,
- deduplicated,
- lexically stable.

Provider-native identifiers MUST NOT leak directly into public orchestration APIs.

---

## 10.3 Validation Guarantees

Planner MUST reject:

- blank parent IDs,
- empty task sets,
- duplicate task IDs,
- tasks without valid backends,
- blank backend identifiers,
- invalid shard counts,
- plans exceeding `max_shards`,
- invalid affinity modes,
- incompatible replay metadata.

Validation failures MUST map to:

```text
INVALID_ARGUMENT
```

---

## 10.4 Determinism Guarantees

Given identical:

- task ordering,
- scheduler inputs,
- backend topology,
- policy configuration,
- runtime contract version,

the planner MUST produce identical manifests.

---

# 11. Backend Selection Semantics

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
| Compliance restrictions | yes |
| Explainability policy | yes |

---

## 11.1 Stable Fallback Behavior

If runtime intelligence is unavailable:

- deterministic lexical backend selection MUST be used.

This guarantees replay consistency.

Fallback decisions MUST remain observable.

---

# 12. Partial Result Envelope

`PartialResultEnvelope`

```yaml
version: "3.1.0"
parent_job_id: job-123
shard_id: job-123-shard-001
backend_id: qpu-ionq

attempt: 1
emitted_at_ms: 1716500000000

payload_ref: qfs://jobs/job-123/shards/001/result.bin
payload_checksum: sha256:abcd
trace_id: trace-xyz
correlation_id: corr-123
```

---

## 12.1 Required Fields

| **Field** | **Required** |
|---|---|
| `version` | yes |
| `parent_job_id` | yes |
| `shard_id` | yes |
| `backend_id` | yes |
| `attempt` | yes |
| `payload_ref` | yes |
| `payload_checksum` | yes |
| `trace_id` | yes |
| `correlation_id` | yes |

---

# 13. Partial Failure Envelope

`PartialFailureEnvelope`

```yaml
version: "3.1.0"
parent_job_id: job-123
shard_id: job-123-shard-001
backend_id: qpu-ionq

attempt: 2
retryable: true

reason_code: EIGEN_BACKEND_UNAVAILABLE
message: backend timeout

emitted_at_ms: 1716500000100
trace_id: trace-xyz
correlation_id: corr-123
```

---

## 13.1 Failure Envelope Requirements

Failure envelopes MUST:

- preserve lineage identity,
- expose stable machine-readable reason codes,
- expose retryability semantics,
- preserve trace continuity,
- remain replay-safe.

---

# 16. Compatibility Guidance

## 16.1 Single-device compatibility path

Implementations MAY represent a single-device or placeholder execution path as a
single-shard split plan, but that path MUST still emit the same versioned split
manifest, shard lineage, and merge validation metadata as multi-shard runs.

## 16.2 Replay-safe manifest rules

- `created_at_ms` MUST be provided by the caller that creates the plan and MUST

  - be treated as part of the replayed manifest identity.
  - `trace_id` MUST be preserved across split, partial result, and merge records.
  - `attempt` MUST begin at 1 for the initial shard execution record.
  - `lineage_ref` SHOULD point at a QFS path or equivalent durable lineage ref.

## 16.3 Final aggregation

`MergeDecision` is the canonical merge-validation record. Final result material
must be written through the runtime persistence layer using the same shard
ordering and lineage references that produced the merge decision.

---

# 17. Standard Failure Reason Codes

## 17.1 Stable Reason Taxonomy

| **Reason code** | **Meaning** |
|---|---|
| `EIGEN_BACKEND_UNAVAILABLE` | Backend unreachable |
| `EIGEN_BACKEND_TIMEOUT` | Runtime timeout |
| `EIGEN_VALIDATION_FAILED` | Invalid shard payload |
| `EIGEN_LEASE_EXPIRED` | Execution lease expired |
| `EIGEN_RESOURCE_EXHAUSTED` | Capacity exhaustion |
| `EIGEN_DEPENDENCY_FAILURE` | Upstream dependency failure |
| `EIGEN_INTERNAL` | Internal runtime failure |
| `EIGEN_SHARD_CANCELLED` | Scheduler cancellation |
| `EIGEN_REPLAY_REJECTED` | Determinism/replay mismatch |
| `EIGEN_MERGE_VALIDATION_FAILED` | Merge validation failure |

Reason codes MUST remain stable within MAJOR versions.

---

# 18. Canonical Error Mapping

| **Condition** | **Canonical Status** |
|---|---|
| Invalid shard manifest | `INVALID_ARGUMENT` |
| Lease conflict | `ABORTED` |
| Lease ownership invalid | `FAILED_PRECONDITION` |
| Backend unavailable | `UNAVAILABLE` |
| Backend timeout | `DEADLINE_EXCEEDED` |
| Capacity exhausted | `RESOURCE_EXHAUSTED` |
| Missing shard | `NOT_FOUND` |
| Merge quorum not satisfied | `FAILED_PRECONDITION` |
| Duplicate shard envelope | `INVALID_ARGUMENT` |
| Internal runtime violation | `INTERNAL` |
| Explicit cancellation | `CANCELLED` |

Retryable failures SHOULD include:

```text
google.rpc.RetryInfo
```

---

# 19. Envelope Invariants

The runtime MUST enforce:

## 19.1 Parent Consistency

All envelopes MUST match target `parent_job_id`.

---

## 19.2 Uniqueness

`shard_id` MUST be unique across:

- result envelopes,
- failure envelopes,
- retry attempts.

---

## 19.3 Version Consistency

All envelopes MUST share identical contract version.

---

## 19.4 Membership Consistency

All shard IDs MUST belong to the expected manifest set.

Unexpected shard IDs MUST be rejected.

---

## 19.5 Payload Integrity

Checksums MUST match referenced payload artifacts.

---

## 19.6 Trace Continuity

Distributed trace propagation MUST remain continuous across:

- scheduler,
- worker,
- merge coordinator,
- artifact storage,
- replay systems.

---

# 20. Merge Semantics

## 20.1 Function Signature

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

# 21. Merge Validation Stages

Before merge evaluation, the coordinator MUST validate:

## 1. Parent consistency

Reject mismatched parent IDs.

## 2. Envelope version consistency

Reject mixed-version envelopes.

## 3. Shard uniqueness

Reject duplicate shard IDs.

## 4. Membership validation

Reject unknown shard IDs.

## 5. Payload integrity

Verify checksums and artifact availability.

## 6. Coverage analysis

Compute:

- merged shards,
- failed shards,
- missing shards,
- retry-pending shards.

## 7. Traceability validation

Verify:

- trace continuity,
- lineage references,
- replay metadata consistency.

---

# 22. Merge Policies

## 22.1 AllShardsRequired

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

## 22.2 Quorum

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

## 22.3 WeightedQuorum

Optional advanced policy:

```yaml
policy:
  type: weighted_quorum
  minimum_weight: 0.75
```

Supports cost/priority-aware merges.

---

## 22.4 BestEffort

Allows merge with partial success.

Success reason:

```text
PartialMergeCompleted
```

---

# 23. Merge Decision Artifact

`MergeDecision`

```yaml
version: "3.1.0"

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
  - reason_code: EIGEN_BACKEND_UNAVAILABLE

trace_id: trace-xyz
correlation_id: corr-123
```

---

# 24. Merge Decision Invariants

The merge coordinator MUST guarantee:

1. Deterministic merge outcome.
2. Stable reason-code mapping.
3. Replay-safe merge behavior.
4. Immutable lineage references.
5. Retry-safe shard accounting.
6. Audit-safe artifact preservation.
7. Stable trace correlation.
8. Deterministic failure normalization.

---

# 25. Retry and Replay Semantics

## 25.1 Retry Behavior

Retries MUST preserve:

- `parent_job_id`,
- `shard_id`,
- lineage identity,
- trace continuity.

Only `attempt` increments.

---

## 25.2 Replay Guarantees

Replay MUST produce equivalent:

- shard topology,
- merge outcome,
- lineage graph,
- policy evaluation,
- scheduler decisions,
- observability semantics.

under identical scheduler conditions.

---

# 26. QFS Lineage Integration

The runtime MUST persist:

| **Artifact** | **Required** |
|---|---|
| Split manifest | yes |
| Partial results | yes |
| Partial failures | yes |
| Merge decisions | yes |
| Retry history | yes |
| Scheduler decisions | yes |
| Explainability snapshots | yes |
| Trace references | yes |

Canonical layout:

```text
qfs://jobs/<job_id>/
  split/
  shards/
  merge/
  lineage/
  traces/
  explain/
```

Artifacts SHOULD remain durable after runtime completion.

---

# 27. Observability Integration

The distributed runtime SHOULD export:

| **Metric** | **Type** |
|---|---|
| `eigen_cluster_queue_backlog_depth` | gauge |
| `eigen_cluster_redeliveries_total` | counter |
| `eigen_cluster_dead_letter_total` | counter |
| `eigen_cluster_assignment_latency_ms` | histogram |
| `eigen_cluster_merge_failures_total` | counter |
| `eigen_cluster_shard_retries_total` | counter |
| `eigen_cluster_replay_failures_total` | counter |
| `eigen_cluster_trace_breakage_total` | counter |

Tracing SHOULD preserve:

- `trace_id`,
- `parent_job_id`,
- `shard_id`,
- backend lineage,
- merge correlation.

Metric labels MUST remain bounded.

Labels MUST NOT include:

- raw payloads,
- user identifiers,
- freeform backend messages,
- arbitrary dynamic metadata.

---

# 28. Explainability Integration

Distributed execution SHOULD expose explainability artifacts for:

- backend assignment,
- fallback selection,
- merge policy decisions,
- shard retries,
- degraded execution paths.

Supported explainability levels:

```text
L1_USER
L2_OPERATOR
L3_FORENSIC
```

Explainability semantics MUST remain aligned with runtime behavior.

---

# 29. Security and Integrity

The runtime MUST support:

- signed manifests,
- lineage verification,
- checksum validation,
- immutable artifact references,
- replay tamper detection,
- trace integrity validation.

Future versions MAY add:

- shard attestation,
- backend trust scoring,
- cryptographic merge proofs,
- hardware-backed lineage signatures.

---

# 30. Conformance Requirements

An implementation is conformant only if it:

1. Produces deterministic shard plans.
2. Preserves parent/shard lineage.
3. Rejects invalid envelopes.
4. Enforces merge validation rules.
5. Preserves retry identity semantics.
6. Exports stable merge artifacts.
7. Maintains replay consistency.
8. Preserves trace continuity.
9. Emits required observability metrics.
10. Uses deterministic canonical error mapping.

---

# 31. Required Test Coverage

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
- partial failure propagation,
- trace continuity preservation,
- fallback routing behavior,
- observability metric emission,
- merge validation failures.

---

# 32. Compatibility Guarantees

The following are stable public contract surfaces:

- shard identity semantics,
- merge policy semantics,
- lineage structure,
- canonical reason codes,
- deterministic replay semantics,
- observability metric semantics,
- explainability levels,
- trace propagation guarantees.

---

# 33. Future Evolution

Planned extensions include:

- adaptive shard balancing,
- dynamic shard resizing,
- speculative execution,
- runtime shard migration,
- weighted scheduling,
- federated orchestration,
- cryptographic lineage attestations,
- topology-aware merge policies,
- AI-assisted scheduling explainability.

---

# 34. Operational Invariants

The following invariants are mandatory:

1. Every shard belongs to exactly one parent job.
2. Merge decisions are deterministic.
3. Retry attempts preserve lineage identity.
4. Unknown shards are rejected.
5. Duplicate shard envelopes are invalid.
6. Payload integrity violations invalidate merge eligibility.
7. Merge policies MUST be replay-safe.
8. Distributed execution MUST remain auditable.
9. Runtime trace continuity MUST remain preservable.
10. Public contract semantics MUST remain backward compatible within a MAJOR version.
11. Observability semantics MUST remain stable across MINOR versions.
12. Distributed failures MUST remain explainable and correlatable.

---

## Appendix A. Diagrams

### A.1 Runtime Architecture Model

![Runtime Architecture Model](https://i.imgur.com/pIVHxJi.png)

<details>
<summary>code</summary>

```text
flowchart TB
  C[Client] --> S[Scheduler]
  S --> SP[Split Planner]
  SP --> M["SplitPlanManifest (shard_plans[])"]
  M --> RM["Resource Manager (leases/retries)"]
  RM --> W[Distributed Runtime Workers]
  W --> PR[PartialResultEnvelope + QFS payload_ref]
  W --> PF["PartialFailureEnvelope (reason_code + retryable)"]
  PR --> MC[Merge Coordinator]
  PF --> MC
  MC --> FD["MergeDecision (final outcome)"]
  FD --> QFS["QFS Lineage Layer (split/shards/merge/lineage)"]
  S --> EX["Explainability Layer (decisions + fallbacks)"]
  EX --> QFS
  S --> OT["Telemetry Exporters (metrics + traces)"]
  W --> OT
  MC --> OT
```

</details>

---

### A.2 Split Planner Contract

![Split Planner Contract](https://i.imgur.com/PGuR1e2.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant Sch as Scheduler
  participant Pl as Split Planner
  participant QFS as QFS (lineage)
  participant Ex as Explainability

  Sch->>Pl: plan_split(parent_job_id, tasks, max_shards, policy)
  Pl->>Pl: Validate inputs (dedup, non-empty, max_shards, backend IDs)
  Pl->>Pl: Deterministic planning (ordering + stable IDs)
  Pl-->>Sch: SplitPlanManifest(version=3.1.0, shard_plans[])
  Sch->>QFS: Persist split manifest qfs://jobs/<job_id>/split/manifest.yaml
  Sch->>Ex: Persist decision snapshot (scheduler_decision_version)
```

</details>

---

### A.3 Split Plan Manifest

![Split Plan Manifest](https://i.imgur.com/zMAZIRx.png)

<details>
<summary>code</summary>

```text
classDiagram
  class SplitPlanManifest {
    +string version
    +string parent_job_id
    +string scheduler_decision_version
    +int64 created_at_ms
    +string trace_id
    +ShardPlan[] shard_plans
  }

  class ShardPlan {
    +string version
    +string parent_job_id
    +string shard_id
    +string backend_id
    +string[] task_ids
    +int32 attempt
    +int64 lease_timeout_ms?
    +map resource_profile?
    +string trace_id
    +string lineage_ref?
  }

  SplitPlanManifest "1" --> "many" ShardPlan
```

</details>

---

### A.4 Identity Guarantees

![Identity Guarantees](https://i.imgur.com/sneKwcB.png)

<details>
<summary>code</summary>

```text
flowchart TB
  P[parent_job_id] --> F[Shard ID function]
  N["NNN (stable index)"] --> F
  F --> SID["<parent>-shard-<NNN>"]

  Inputs[Determinism inputs] --> F
  Inputs --- T["task ordering (canonical)"]
  Inputs --- Topo[backend topology snapshot]
  Inputs --- Pol[policy config]
  Inputs --- Ver[contract version 3.1.0]

  F -->|same inputs| SAME[Byte-identical shard_id set]
```

</details>

---

### A.5 Partial Result Envelope

![Partial Result Envelope](https://i.imgur.com/pnZrJnM.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant W as Runtime Worker
  participant QFS as QFS
  participant MC as Merge Coordinator
  participant Obs as Observability

  W->>QFS: Write shard result payload qfs://jobs/<job_id>/shards/<NNN>/result.*
  W->>W: Compute checksum sha256
  W-->>MC: PartialResultEnvelope (parent_job_id, shard_id, attempt, payload_ref, checksum, trace_id, correlation_id)
  MC->>MC: Validate membership + version + checksum availability
  MC->>Obs: Emit events/metrics (shard_completed)
```

</details>

---

### A.6 Partial Failure Envelope

![Partial Failure Envelope](https://i.imgur.com/guB471q.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant W as Runtime Worker
  participant MC as Merge Coordinator
  participant RM as Resource Manager
  participant Obs as Observability

  W-->>MC: PartialFailureEnvelope (reason_code, retryable, attempt, trace_id, correlation_id)
  MC->>MC: Normalize + account failure (failed_shard_ids)
  MC->>RM: If retryable -> request retry lease (shard_id, attempt+1)
  RM-->>W: Retry assignment (same shard_id) (attempt increments)
  MC->>Obs: Emit failure telemetry (reason_code taxonomy)
```

</details>

---

### A.7 Envelope Invariants

![Envelope Invariants](https://i.imgur.com/z0Z69XQ.png)

<details>
<summary>code</summary>

```text
flowchart TB
  E[Incoming Envelope] --> V0{version == 3.1.0?}
  V0 -- no --> R0["Reject: FAILED_PRECONDITION (mixed/unsupported version)"]
  V0 -- yes --> V1{parent_job_id matches?}
  V1 -- no --> R1["Reject: INVALID_ARGUMENT (parent mismatch)"]
  V1 -- yes --> V2{shard_id in manifest?}
  V2 -- no --> R2["Reject: INVALID_ARGUMENT (unknown shard)"]
  V2 -- yes --> V3{duplicate shard_id?}
  V3 -- yes --> R3["Reject: INVALID_ARGUMENT (duplicate envelope)"]
  V3 -- no --> V4{checksum ok + payload exists?}
  V4 -- no --> R4["Reject: FAILED_PRECONDITION (integrity/availability)"]
  V4 -- yes --> OK[Accept & account]
```

</details>

---

### A.8 Merge Semantics / Validation / Decision

![Merge Semantics / Validation / Decision](https://i.imgur.com/Rp9iiuV.png)

<details>
<summary>code</summary>

```text
flowchart TB
  In[(Collected envelopes)] --> A[Stage 1: Parent consistency]
  A --> B[Stage 2: Version consistency]
  B --> C[Stage 3: Shard uniqueness]
  C --> D[Stage 4: Membership validation]
  D --> E["Stage 5: Payload integrity (checksum + availability)"]
  E --> F[Stage 6: Coverage analysis merged/failed/missing/retry-pending]
  F --> G["Stage 7: Traceability validation (trace_id continuity)"]
  G --> P{Apply merge policy}
  P -->|AllShardsRequired| M1[All expected shards succeeded?]
  P -->|Quorum| M2[min_successful_shards satisfied?]
  P -->|WeightedQuorum| M3[minimum_weight satisfied?]
  P -->|BestEffort| M4[Merge what is available]
  M1 --> D1[MergeDecision]
  M2 --> D1
  M3 --> D1
  M4 --> D1
  D1 --> QFS[Persist MergeDecision qfs://jobs/<job_id>/merge/decision.yaml]
```

</details>

---

### A.9 Merge Policies

![Merge Policies](https://i.imgur.com/Lo42WQK.png)

<details>
<summary>code</summary>

```text
stateDiagram-v2
  [*] --> Collecting
  Collecting --> Validating: enough envelopes received or deadline
  Validating --> AwaitingRetries: retry_pending_shards > 0 and budget remains
  AwaitingRetries --> Collecting: retry envelopes arrive

  Validating --> Success: policy satisfied (All/Quorum/Weighted/BestEffort)
  Validating --> Failure: policy cannot be satisfied (quorum impossible, validation failed)
  Validating --> PartialSuccess: BestEffort partial merge completed

  Success --> [*]
  Failure --> [*]
  PartialSuccess --> [*]
```

</details>

---

### A.10 Retry and Replay Semantics

![Retry and Replay Semantics](https://i.imgur.com/9550w48.png)

<details>
<summary>code</summary>

```text
flowchart TB
  SID["shard_id (fixed)"] --> R["Retry attempt"]
  PJ["parent_job_id (fixed)"] --> R
  TR["trace continuity preserved"] --> R
  R --> A1["attempt = attempt + 1"]
  R -->|payload changes| NewP["New payload_ref + checksum"]
  R -->|identity unchanged| SameID["Same (parent_job_id, shard_id)"]
```

</details>

---

### A.11 QFS Lineage Integration

![QFS Lineage Integration](https://i.imgur.com/HkXwUx7.png)

<details>
<summary>code</summary>

```text
flowchart LR
  Root[qfs://jobs/<job_id>/] --> Split[split/ manifest.yaml + planner metadata]
  Root --> Shards[shards/ <NNN>/ result.* / error.* / attempts/]
  Root --> Merge[merge/ decision.yaml + validation report]
  Root --> Lineage["lineage/ lineage.json (parent<->shards)"]
  Root --> Traces[traces/ spans.json + events.json]
  Root --> Explain[explain/ assignment + fallback + merge rationale]
```

</details>

---

### A.12 Observability Integration

![Observability Integration](https://i.imgur.com/jdeGmVc.png)

<details>
<summary>code</summary>

```text
flowchart LR
  Ev[Runtime events] --> Met["Metrics (bounded labels)"]
  Ev --> Tr["Traces (traceparent)"]
  Ev --> Log[Structured logs]

  Met --> M1[eigen_cluster_queue_backlog_depth]
  Met --> M2[eigen_cluster_redeliveries_total]
  Met --> M3[eigen_cluster_dead_letter_total]
  Met --> M4[eigen_cluster_assignment_latency_ms]
  Met --> M5[eigen_cluster_merge_failures_total]
  Met --> M6[eigen_cluster_shard_retries_total]
  Met --> M7[eigen_cluster_replay_failures_total]
  Met --> M8[eigen_cluster_trace_breakage_total]

  Tr --> Attr[Attrs: parent_job_id, shard_id, backend_id, merge_correlation_id]
  Log --> Fields[Fields: parent_job_id, shard_id, attempt, reason_code, correlation_id]
```

</details>

---

### A.13 Explainability Integration

![Explainability Integration](https://i.imgur.com/ELnvTOU.png)

<details>
<summary>code</summary>

```text
flowchart TB
  Sch[Scheduler decision] --> A[Backend assignment explain]
  Sch --> F[Fallback selection explain]
  MC[Merge Coordinator] --> MP[Merge policy decision explain]
  RM[Resource Manager] --> RR[Retry rationale explain]
  A --> QFS[qfs://jobs/<job_id>/explain/]
  F --> QFS
  MP --> QFS
  RR --> QFS
```

</details>
