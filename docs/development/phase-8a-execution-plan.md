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

## Feature flag defaults and rollout notes (P8A-05)

| Flag | Default | Rollout note |
|---|---|---|
| `feature.kb_v1` | `false` | Enable first in replay/fixture environments to verify stable `results_ref`/record linkage before shared environments. |
| `feature.optimizer_v1` | `false` | Enable after deterministic replay is green; keep disabled for non-hybrid jobs to preserve baseline behavior. |
| `feature.learning_pipeline_v1` | `false` | Enable only with bounded fixture datasets and trace-linked artifacts for auditability. |
| `feature.qfs_l2_checkpoint_v1` | `false` | Enable after checkpoint envelope conformance checks are passing in CI for target branch. |

All flags must remain explicitly set during phased rollout; missing flags resolve to deterministic safe defaults (`false`).

## CI gate bundle implementation (P8A-06)

The Phase-8A gate bundle is executable via `scripts/ci/check-phase8a-gates.sh` and wired as a required CI job (`phase8a-ci-gate-bundle`) in `.github/workflows/ci.yml`.

Gate sequence (fail-closed):

1. `check-contract-drift.py` validates all versioned contract artifacts against `scripts/ci/contract-version-manifest.json`.
2. `integration_phase8a_vertical_slice_fixture_replay_is_deterministic` verifies deterministic replay of compile → optimize → execute → persist/query.
3. `check-runtime-decision-determinism.sh` validates deterministic scheduler/runtime decision replay artifacts.
4. `check-phase8a-probe-fixtures.py` validates versioned probe fixtures and budget bounds for:
   - compile latency trend,
   - scheduler enqueue p95 trend,
   - KB indexed query latency trend,
   - bounded dataset ingestion fixture.

Probe fixtures are versioned at `docs/development/fixtures/phase8a/probe_trends_v1.json`.
