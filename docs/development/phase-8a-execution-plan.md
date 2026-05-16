# Phase-8A Execution Plan (Contracts + Vertical Slice MVP)

- **Status:** In progress
- **Date:** 2026-05-16
- **Source roadmap:** `docs/development/phase-8-implementation-roadmap-v1.1.0.md`
- **Milestone:** M8A

## Scope

Phase-8A converts architecture intent into implementation-ready contracts and one deterministic end-to-end path:

`Eigen-Lang -> compile -> optimize -> execute (simulator) -> persist artifacts/dataset metadata -> KB queryable record`.

## Required Phase-8A documentation package

1. RFC 0034 — Knowledge Base API v1.
2. RFC 0035 — GNN Optimizer Service Contract v1.
3. RFC 0036 — Continuous Learning Control Plane Contract v1.
4. RFC 0037 — QFS-L2 Checkpoint Envelope Contract v1.
5. This execution plan as the implementation binding for sprint planning, CI gate mapping, and acceptance review.

## Workstreams and deliverables

### A. Contract finalization

- Lock protobuf/service surfaces for KB, optimizer, learning control plane, and QFS-L2 envelope.
- Resolve all critical TODOs in component docs for these domains.
- Define explicit error models and compatibility guarantees.

### B. Vertical slice MVP

- Implement feature-flagged path (`kb_v1`, `optimizer_v1`, `learning_pipeline_v1`, `qfs_l2_checkpoint_v1`).
- Add deterministic fixture for compile/optimize/execute/persist/query flow.
- Ensure artifacts and dataset metadata are trace-linked via stable IDs.

### C. Phase-8A CI gate bundle

- Contract schema drift gate.
- Integration gate for vertical slice deterministic replay.
- Performance probe fixtures for initial TZ acceptance trendlines:
  - compile latency for simple circuits,
  - scheduler enqueue p95 trend,
  - KB indexed query latency trend,
  - dataset ingestion bounded fixture.

## Acceptance criteria

Phase-8A is complete only when:

- all four RFCs are in `Accepted` state;
- versioned schemas are published and linked in docs;
- at least one deterministic integration test validates the full vertical slice;
- there are no unresolved contract TODO markers in critical component docs;
- CI includes an executable Phase-8A gate bundle.

## Dependencies

- Existing Phase-7 compatibility policy and migration-note enforcement.
- Existing simulator backend path for deterministic execution.
- Existing observability baseline from Phase-5/Phase-7 contracts.

## Risks and mitigations

1. **Contract churn risk**  
   Mitigation: freeze criteria and compatibility rubric before implementation merges.
2. **Cross-service schema mismatch risk**  
   Mitigation: single source-of-truth protobuf package boundaries + conformance fixtures.
3. **Non-deterministic optimizer behavior risk**  
   Mitigation: deterministic seed policy and fallback heuristic in first release.

## Exit review checklist

- [ ] RFC 0034 accepted and linked in architecture/reference docs.
- [ ] RFC 0035 accepted and linked in architecture/reference docs.
- [ ] RFC 0036 accepted and linked in architecture/reference docs.
- [ ] RFC 0037 accepted and linked in architecture/reference docs.
- [ ] Vertical-slice integration test passing in CI.
- [ ] Phase-8A probe fixtures committed and runnable.
- [ ] Compatibility impact statement published in release notes draft.
