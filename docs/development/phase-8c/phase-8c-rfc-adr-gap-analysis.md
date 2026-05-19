# Phase-8C RFC/ADR Gap Analysis (Adaptive Intelligence Loop)

- **Status:** Proposed
- **Date:** 2026-05-19
- **Version:** 1.0.0
- **Issue:** P8C-07

## Objective

Determine whether Phase-8C scope is fully covered by existing accepted contracts or requires new RFC/ADR artifacts before implementation closure.

## Inputs reviewed

- `docs/development/phase-8/phase-8-implementation-roadmap-v1.1.0.md`
- `docs/development/phase-8c/phase-8c-execution-plan.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`
- Phase-8A and Phase-8B governance baselines (RFC 0034-0040 and corresponding ADR mirrors).

## Gap decision

**New RFC/ADR updates are required for Phase-8C.**

Rationale:
- Existing accepted RFCs (Phase-8A/8B) do not normatively define deterministic model-assisted transition semantics for Eigen-DPDA.
- Existing contracts do not define a complete evaluation/promotion contract for GNN optimizer lifecycle states.
- Continuous learning safety gates (trigger cadence, canary policy, rollback automation, lineage evidence) need explicit normative policy language.

## Required RFC package (blocking for Phase-8C closure)

1. **RFC 0041** — Eigen-DPDA Deterministic + Model-Assisted Transition Contract v1.
2. **RFC 0042** — GNN Optimizer Evaluation and Promotion Contract v1.
3. **RFC 0043** — Continuous Learning Control Plane and Safety Gates Contract v1.

Each accepted RFC must be mirrored by ADR updates according to repository ADR policy.

## Governance traceability requirements

- RFC statuses must reach **Accepted** before milestone closure.
- ADR mirrors must capture implementation constraints and operational tradeoffs.
- `docs/rfcs-pointer.md`, `docs/adr/README.md`, and `docs/development/README.md` must be updated with final links.
- Breaking contract deltas discovered during implementation require new RFC revision or follow-up RFC.

## Compatibility statement (current planning state)

- **Version Impact (planning docs only):** PATCH.
- **Breaking Marker (planning docs only):** false.
- **Migration Notes:** None at planning stage; to be re-evaluated when RFCs are accepted.

## Gap matrix

| Area | Required artifact | Current evidence | Status |
| --- | --- | --- | --- |
| Eigen-DPDA deterministic/model-assisted semantics | Accepted RFC + mirrored ADR | Planned RFC 0041 | Open |
| GNN optimizer evaluation/promotion lifecycle | Accepted RFC + mirrored ADR | Planned RFC 0042 | Open |
| Continuous learning trigger/canary/rollback safety gates | Accepted RFC + mirrored ADR | Planned RFC 0043 | Open |
| Docs pointer synchronization | Updated development/RFC/ADR indexes | Not yet updated | Open |
| Exit evidence package | CI gate evidence + compatibility statement | Not yet produced | Open |
