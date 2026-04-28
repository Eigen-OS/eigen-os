This document is a ready-to-use set of GitHub issues for the **Phase-5** stage of the roadmap.

**Context Sources:**
- `docs/roadmap.md` (Section: "Phase-5: Distributed Execution")
- `docs/development/post-mvp-open-source-roadmap.md` (Section: "Phase-5: Distributed Execution")
- `docs/development/phase-5-distributed-execution.md`
- `docs/development/phase-5-rfc-adr-gap-analysis.md`

---

## Versioning Rules (Mandatory for every Phase-5 issue)

> Include this block in the description of every issue (as "Definition of Done / Constraints").

1. **SemVer for stable distributed contracts:**
   - Cluster control-plane DTOs, queue/delivery schemas, and topology envelopes use `MAJOR.MINOR.PATCH`.
2. **Breaking changes only via `MAJOR`:**
   - Any incompatible assignment, lease, ack/requeue, or lineage-field semantics require `MAJOR`.
3. **Backward-compatible additions via `MINOR`:**
   - Optional observability, diagnostics, and metadata fields use `MINOR`.
4. **`PATCH` for fixes only:**
   - No public delivery guarantee or lineage semantic changes in `PATCH` releases.
5. **Mandatory version markers in distributed artifacts:**
   - Assignment records, queue lease events, and execution topology artifacts include explicit version fields.
6. **Deprecation policy:**
   - Contract fields cannot be removed before at least one `MINOR` release marks them deprecated.
7. **Changelog discipline:**
   - Every Phase-5 PR includes:
     - `Version impact`
     - `Compatibility`
     - `Migration notes` (if applicable).

---

## Milestone

- **Milestone:** `Phase-5 Distributed Execution`
- **Suggested labels:** `phase-5`, `distributed-runtime`, `cluster`, `queue`, `observability`, `eigen-lang`, `quality`, `rfc`

---

## Issues

### P5-01 — Cluster Runtime Control Plane Core v1

**Type:** Feature  
**Labels:** `phase-5`, `cluster`, `runtime`

**Problem** Single-node orchestration cannot provide scalable parallel execution and fault isolation.

**Scope**
- Cluster bootstrap contract for `--cluster` mode.
- Worker registration and capability handshake.
- Deterministic assignment baseline and fallback behavior.

**Acceptance Criteria**
- Control plane starts in cluster mode and discovers workers deterministically.
- Assignment decisions include explicit version and lineage metadata.
- Node-loss fallback behavior is documented and integration-tested.

**RFC link**
- `rfcs/0026-phase5-cluster-runtime-control-plane-contract-v1.md`

---

### P5-02 — Worker Node Service and Remote Execution Contract

**Type:** Feature  
**Labels:** `phase-5`, `cluster`, `worker`

**Problem** Worker-side execution behavior must be consistent, idempotent, and debuggable.

**Scope**
- Worker execution API (`start`, `heartbeat`, `complete`, `cancel`).
- Runtime artifact staging/materialization contract.
- Retry-safe idempotency enforcement.

**Acceptance Criteria**
- Duplicate delivery with same idempotency key is safe.
- Heartbeat/timeout behavior is deterministic and fixture-tested.
- Cancellation intent and terminal state are durable.

**RFC link**
- `rfcs/0026-phase5-cluster-runtime-control-plane-contract-v1.md`

---

### P5-03 — Pluggable Queue Layer and Delivery Semantics v1

**Type:** Platform  
**Labels:** `phase-5`, `queue`, `runtime`

**Problem** Distributed execution needs a formal queue abstraction rather than ad-hoc in-process dispatch.

**Scope**
- Queue adapter interface for local and external providers.
- Lease/ack/requeue/dead-letter contract.
- Delivery semantics baseline and compatibility fixtures.

**Acceptance Criteria**
- Queue adapters pass common contract suite.
- Lease expiration and redelivery behavior are deterministic.
- Dead-letter paths are observable and test-covered.

**RFC link**
- `rfcs/0027-phase5-distributed-queue-and-delivery-semantics-v1.md`

---

### P5-04 — Distributed Tracing and Topology Lineage Contract

**Type:** Observability / API  
**Labels:** `phase-5`, `observability`, `api`

**Problem** Cross-node failures are hard to debug without stable topology lineage and trace propagation.

**Scope**
- Trace-context propagation across control plane, queue, worker, and driver layers.
- Topology envelope (`cluster_id`, `worker_id`, `partition_id`, `attempt`).
- Conformance fixtures for topology metadata in status/results surfaces.

**Acceptance Criteria**
- End-to-end trace continuity validated in integration tests.
- Job status/results include topology metadata with version markers.
- Contract tests block incompatible lineage field changes.

**RFC link**
- `rfcs/0028-phase5-distributed-tracing-and-execution-topology-contract-v1.md`

---

### P5-05 — Eigen-Lang Distributed Execution Metadata and Hints

**Type:** Compiler / Language  
**Labels:** `phase-5`, `eigen-lang`, `compiler`

**Problem** Developers need first-class distributed execution intent and diagnostics in Eigen-Lang workflows.

**Scope**
- Compile-time validation for distributed target constraints.
- Distributed metadata in compiler outputs.
- Topology-aware runtime hints mapped to explainability artifacts.

**Acceptance Criteria**
- Unsupported distributed configurations fail with deterministic diagnostics.
- Metadata format is versioned and documented.
- Conformance fixtures protect distributed metadata compatibility.

**RFC link**
- `rfcs/0026-phase5-cluster-runtime-control-plane-contract-v1.md`
- `rfcs/0028-phase5-distributed-tracing-and-execution-topology-contract-v1.md`

---

### P5-06 — SRE Pack for Cluster Health and Queue Reliability

**Type:** Observability  
**Labels:** `phase-5`, `observability`, `sre`

**Problem** Operations need clear health signals and runbooks for distributed runtime incidents.

**Scope**
- Metrics for worker heartbeats, lease churn, redelivery rate, dead-letter volume.
- Dashboards for assignment latency, queue backlog, and node availability.
- Alerts + runbooks for queue stall, worker-flap, and trace breakage.

**Acceptance Criteria**
- Dashboards cover control-plane -> queue -> worker critical path.
- Alerts fire on reliability and SLO threshold breaches.
- Runbook includes deterministic triage and rollback steps.

**RFC link**
- `rfcs/0027-phase5-distributed-queue-and-delivery-semantics-v1.md`
- `rfcs/0028-phase5-distributed-tracing-and-execution-topology-contract-v1.md`

---

### P5-07 — Determinism and Replay Gate for Distributed Scheduling

**Type:** Quality  
**Labels:** `phase-5`, `quality`, `distributed-runtime`

**Problem** Distributed systems regress quickly without replay-based determinism gates.

**Scope**
- Replay harness for assignment + lease + retry transitions.
- Drift detection for delivery and lineage output compatibility.
- CI gate for non-deterministic branch detection.

**Acceptance Criteria**
- Replay of recorded distributed artifacts yields stable outcomes.
- Drift gate blocks uncontrolled semantic changes.
- Failure output identifies non-deterministic signal source.

**RFC link**
- `rfcs/0026-phase5-cluster-runtime-control-plane-contract-v1.md`
- `rfcs/0027-phase5-distributed-queue-and-delivery-semantics-v1.md`

---

### P5-08 — RFC Package for Phase-5 Distributed Contracts

**Type:** Architecture / Governance  
**Labels:** `phase-5`, `rfc`, `architecture`

**Problem** Phase-5 implementation cannot be stabilized without formal distributed contract RFCs.

**Scope**
- Create/accept RFCs for:
  1. cluster runtime control-plane contract,
  2. queue + delivery semantics contract,
  3. distributed tracing and topology contract.
- Link RFCs from roadmap/development docs.

**Acceptance Criteria**
- Required Phase-5 RFC set is merged and indexed.
- Each RFC includes compatibility and test-plan sections.
- RFC statuses are explicit (`Draft`/`Accepted`/`Implemented`).

**RFC link**
- `rfcs/0026-phase5-cluster-runtime-control-plane-contract-v1.md`
- `rfcs/0027-phase5-distributed-queue-and-delivery-semantics-v1.md`
- `rfcs/0028-phase5-distributed-tracing-and-execution-topology-contract-v1.md`
