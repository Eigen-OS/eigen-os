This document is a ready-to-use set of GitHub issues for the **Phase-8A** stage of the roadmap.

**Context Sources:**
- `docs/development/phase-8-implementation-roadmap-v1.1.0.md` (Section: "M8A")
- `docs/development/phase-8a-execution-plan.md`
- `docs/development/post-mvp-open-source-roadmap.md` (Phase progression context)
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md` (normative versioning constraints)

---

## Versioning & Compatibility Rules (Mandatory for every Phase-8A issue)

> Include this block in the description of every issue (as "Definition of Done / Constraints").

1. **SemVer is mandatory for stable contracts** across API, protobuf schemas, CLI payloads, and persisted envelopes.
2. **Breaking behavior requires `MAJOR`** and explicit migration notes.
3. **Backward-compatible additions use `MINOR`** with deterministic defaults.
4. **`PATCH` is non-semantic only** (bug fixes, docs fixes, observability tuning).
5. **Deprecations require a fixed support window:** deprecated interfaces remain supported for 2 minor releases or 90 days, whichever is longer; removals then require explicit RFC/ADR update + migration notes.
6. **Compatibility matrix updates are versioned artifacts** and must be fixture-tested.
7. **CI must fail closed** on undocumented contract drift.

---

## Milestone

- **Milestone:** `Phase-8A Contracts + Vertical Slice MVP`
- **Suggested labels:** `phase-8a`, `contracts`, `integration`, `ci`, `quality`, `rfc`

---

## Priority and ownership proposal (requires maintainer confirmation)

| Issue | Priority | Proposed owner group |
| --- | --- | --- |
| P8A-01 Knowledge Base API Contract v1 Finalization | P0 | Architecture/Governance + Runtime/Core |
| P8A-02 GNN Optimizer Service Contract v1 Finalization | P0 | Optimizer/Compiler |
| P8A-03 Continuous Learning Control Plane Contract v1 Finalization | P0 | Runtime/Core + ML Platform |
| P8A-04 QFS-L2 Checkpoint Envelope Contract v1 Finalization | P0 | Runtime/Core + Data/Storage |
| P8A-05 Vertical Slice MVP: compile -> optimize -> execute -> persist -> query | P0 | Runtime/Core + Integration |
| P8A-06 Phase-8A CI Gate Bundle and Deterministic Replay Fixtures | P0 | QA/CI Infrastructure |
| P8A-07 Phase-8A RFC/ADR/Docs Synchronization and Exit Review Pack | P1 | Architecture/Governance + Tech Writing |

> Confirmation required from maintainers for final DRI assignments and sequencing.

---

## Issues

### P8A-01 — Knowledge Base API Contract v1 Finalization

**Type:** Architecture / API  
**Labels:** `phase-8a`, `contracts`, `rfc`

**Problem** The KB service surface needs an implementation-locked v1 contract with explicit compatibility and error model behavior.

**Scope**
- Finalize KB API protobuf/service schema and versioning envelope.
- Define deterministic error taxonomy, reason codes, and retry semantics.
- Link contract to RFC 0034 and implementation references.

**Acceptance Criteria**
- KB API v1 schema is frozen and versioned.
- Compatibility guarantees and error model are documented.
- Contract fixtures exist and pass schema lint/breaking checks.

**RFC link**
- `rfcs/0034-knowledge-base-api-v1.md`

---

### P8A-02 — GNN Optimizer Service Contract v1 Finalization

**Type:** Architecture / Service Contract  
**Labels:** `phase-8a`, `contracts`, `optimizer`, `rfc`

**Problem** Optimizer interface drift risk is high without a locked service contract and deterministic fallback semantics.

**Scope**
- Finalize optimizer request/response schema and service boundaries.
- Define deterministic seed policy and fallback heuristic contract.
- Define performance/trace fields required by downstream observability.

**Acceptance Criteria**
- Optimizer v1 contract is frozen and documented.
- Deterministic behavior requirements are specified and fixture-tested.
- CI detects schema drift and blocks undocumented breaking changes.

**RFC link**
- `rfcs/0035-gnn-optimizer-service-contract-v1.md`

---

### P8A-03 — Continuous Learning Control Plane Contract v1 Finalization

**Type:** Architecture / Control Plane  
**Labels:** `phase-8a`, `contracts`, `learning`, `rfc`

**Problem** Learning pipeline orchestration requires stable control-plane commands and state transitions to avoid cross-service ambiguity.

**Scope**
- Finalize control-plane commands, lifecycle states, and transition invariants.
- Define idempotency and replay behavior for control actions.
- Specify audit and observability fields for governance traces.

**Acceptance Criteria**
- Control-plane v1 schema and state model are versioned.
- Transition and idempotency invariants are test-covered.
- Control-plane compatibility notes are linked in docs.

**RFC link**
- `rfcs/0036-continuous-learning-control-plane-contract-v1.md`

---

### P8A-04 — QFS-L2 Checkpoint Envelope Contract v1 Finalization

**Type:** Architecture / Data Contract  
**Labels:** `phase-8a`, `contracts`, `storage`, `rfc`

**Problem** Checkpoint persistence/query path needs a stable envelope to guarantee replayability and cross-version decoding.

**Scope**
- Finalize QFS-L2 checkpoint envelope schema and metadata fields.
- Define trace-link requirements between artifacts, dataset metadata, and checkpoint IDs.
- Define compatibility strategy for future envelope extensions.

**Acceptance Criteria**
- QFS-L2 envelope v1 is published and fixture-tested.
- Trace-linking fields are mandatory and validated in tests.
- Docs include decoding/upgrade notes for supported versions.

**RFC link**
- `rfcs/0037-qfs-l2-checkpoint-envelope-contract-v1.md`

---

### P8A-05 — Vertical Slice MVP: compile -> optimize -> execute -> persist -> query

**Type:** Implementation / Integration  
**Labels:** `phase-8a`, `integration`, `vertical-slice`, `quality`

**Problem** Phase-8A requires one deterministic end-to-end path proving implementation readiness beyond contract text.

**Scope**
- Implement feature-flagged path: `kb_v1`, `optimizer_v1`, `learning_pipeline_v1`, `qfs_l2_checkpoint_v1`.
- Add deterministic integration fixture for the full flow.
- Ensure stable IDs and traceparent propagation across all steps.

**Acceptance Criteria**
- End-to-end deterministic replay test passes in CI.
- Artifacts/dataset metadata/KB record are trace-linked via stable IDs.
- Feature flags are documented with safe defaults and rollout notes.

**RFC link**
- `docs/development/phase-8a-execution-plan.md`

---

### P8A-06 — Phase-8A CI Gate Bundle and Deterministic Replay Fixtures

**Type:** Quality / CI  
**Labels:** `phase-8a`, `ci`, `quality`, `contracts`

**Problem** Phase-8A closure requires enforceable automated gates for contracts, replay determinism, and initial TZ trend probes.

**Scope**
- Add contract schema drift gate for all 8A surfaces.
- Add integration gate for deterministic vertical-slice replay.
- Add probe fixtures for compile latency, scheduler enqueue p95 trend, KB indexed query latency trend, and dataset ingestion bounded fixture.

**Acceptance Criteria**
- CI gate bundle is executable and required on `main`.
- Drift, replay, and probe gates fail closed with actionable diagnostics.
- Probe fixture outputs are versioned and documented.

**RFC link**
- `docs/development/phase-8a-execution-plan.md`

---

### P8A-07 — Phase-8A RFC/ADR/Docs Synchronization and Exit Review Pack

**Type:** Governance / Documentation  
**Labels:** `phase-8a`, `rfc`, `architecture`, `docs`

**Problem** Phase-8A cannot be closed without synchronized RFC status, ADR traceability, and release-facing compatibility notes.

**Scope**
- Confirm RFCs 0034/0035/0036/0037 are accepted and indexed.
- Add/refresh implementation ADRs mapped to each accepted RFC.
- Synchronize pointers in `docs/rfcs-pointer.md` and `docs/development/README.md`.
- Publish exit review checklist evidence bundle.

**Acceptance Criteria**
- All four RFCs are accepted and cross-linked in docs.
- ADR mapping checklist is complete and reviewable.
- Exit review includes CI evidence, compatibility impact statement, and release-note draft links.

**RFC link**
- `rfcs/0034-knowledge-base-api-v1.md`
- `rfcs/0035-gnn-optimizer-service-contract-v1.md`
- `rfcs/0036-continuous-learning-control-plane-contract-v1.md`
- `rfcs/0037-qfs-l2-checkpoint-envelope-contract-v1.md`