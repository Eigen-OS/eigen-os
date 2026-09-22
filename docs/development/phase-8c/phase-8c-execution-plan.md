# Phase-8C Execution Plan (Intelligence and Self-Learning Loop)

- **Status:** Planned
- **Date:** 2026-05-19
- **Source roadmap:** `docs/development/phase-8/phase-8-implementation-roadmap-v1.1.0.md`
- **Milestone:** M8C

## Scope

Phase-8C operationalizes adaptive intelligence as a production loop:

`runtime traces -> KB feature views -> retrain trigger -> candidate model build -> shadow validation -> canary promotion -> rollback guardrails -> decision/explainability audit`.

## Required Phase-8C documentation package

1. RFC package:
   - RFC 0041 — Eigen-DPDA Deterministic + Model-Assisted Transition Contract v1.
   - RFC 0042 — GNN Optimizer Evaluation and Promotion Contract v1.
   - RFC 0043 — Continuous Learning Control Plane and Safety Gates Contract v1.
2. This execution plan (sprint/ownership binding + CI gate mapping).
3. Phase-8C issue pack (ready-to-use GitHub issues with acceptance criteria).
4. Phase-8C RFC/ADR gap analysis (coverage decision and required governance deltas).
5. Phase-8C release readiness checklist (closure criteria for adaptive loop).
6. Phase-8C compatibility report (contract/version impact for compiler/runtime/KB/learning pipeline).

## Workstreams and deliverables

### A. Eigen-DPDA v1 hardening

- Implement deterministic fallback path for all model-assisted transition decisions.
- Add model-assisted transition selection path with stable reason-code vocabulary.
- Add traceable decision logs (input features, policy branch, selected transition, fallback marker).
- Provide replay harness validating deterministic behavior under fixed seeds/fixtures.

### B. GNN optimizer v1 baseline

- Deliver topology-aware placement/routing baseline with deterministic scoring envelope.
- Add offline evaluation harness (frozen datasets + reproducible metrics bundle).
- Add online evaluation harness in shadow mode before any production promotion.
- Standardize optimizer artifact lifecycle (train/eval/candidate/promoted/rolled_back).

### C. Continuous learning pipeline

- Implement trigger policy (default: every 1000 new circuits, configurable by policy).
- Implement shadow validation and canary promotion workflow with explicit blocking conditions.
- Implement automated rollback on regression with stable diagnostics and runbook references.
- Ensure KB registration of model lineage, feature snapshots, and evaluation evidence.

### D. Explainability, governance, and observability

- Define explainability audit schema for compiler/optimizer decisions.
- Add telemetry and alerts for retrain queue pressure, promotion failures, and rollback storms.
- Add policy controls for promotion freeze, emergency fallback, and model pinning.
- Bind all learning decisions to trace IDs for incident triage and compliance reporting.

### E. CI/release gate expansion for 8C

- Add threshold-trigger gate validating automatic model version creation on configured event counts.
- Add canary non-regression gate against baseline heuristic (target metric families frozen per fixture set).
- Add reproducibility gate for benchmark report generation (same inputs => same report hash).
- Add rollback safety gate validating automatic regression containment behavior.

## Acceptance criteria

Phase-8C is complete only when:

- automatic model version creation is observed on threshold trigger events;
- canary promotion policy demonstrates non-regression and enforces fail-closed behavior;
- rollback automation activates on regression fixtures and emits deterministic reason codes;
- benchmark report for optimization gain vs baseline heuristic is reproducible;
- explainability/decision logs are queryable and cross-linked with model lineage in KB;
- compatibility and migration impact are documented for all modified contracts.

## Dependencies

- Phase-8A accepted contracts for KB/GNN/learning control plane foundations.
- Phase-8B runtime/data observability, checkpoint integrity, and queue stability baselines.
- Accepted policy from `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`.

## Risks and mitigations

1. **Nondeterministic behavior in model-assisted transitions**  
   Mitigation: mandatory deterministic fallback + replay gates + seed policy enforcement.
2. **False-positive model promotions**  
   Mitigation: shadow-only prechecks + strict canary blockers + rollback automation.
3. **Data drift/label-quality degradation in retraining inputs**  
   Mitigation: dataset quality score threshold + quarantine pipeline + lineage audits.
4. **Operational overload from frequent retraining**  
   Mitigation: trigger backpressure controls, retrain budget caps, and promotion windows.

## Exit review checklist

- [ ] Threshold-triggered model versioning gate is green with evidence links.
- [ ] Canary non-regression gate is green against baseline heuristic profiles.
- [ ] Rollback automation gate is green for regression fixtures.
- [ ] Reproducible benchmark-report hash gate is green.
- [ ] Explainability decision logs are queryable and linked to trace/model lineage IDs.
- [ ] Phase-8C compatibility report is approved and linked in release-note draft.
