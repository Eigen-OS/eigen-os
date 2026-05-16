# RFC 0036: Phase-8A Continuous Learning Control Plane Contract v1

- **Status**: Accepted
- **Authors**: Eigen OS maintainers
- **Created**: 2026-05-16
- **Target Milestone**: Phase 8A
- **Tracking Issue**: M8A-03

## Summary

Defines the control-plane contract for automated training/evaluation/promotion/rollback of optimizer models, including safety gates and model lifecycle states.

## Goals

- Standardize learning lifecycle operations across scheduler, optimizer, and KB.
- Make promotion and rollback policy explicit and auditable.
- Enable event-triggered model versioning (e.g., every 1000 new circuits).

## Non-goals

- Model architecture internals.
- Feature-store implementation details.

## Reference-level design

### Lifecycle states

`DRAFT -> TRAINED -> VALIDATED -> SHADOW -> CANARY -> PROMOTED -> RETIRED`

### Commands

- `StartTraining(TrainingSpec)`
- `RunEvaluation(EvalSpec)`
- `PromoteModel(PromotionSpec)`
- `RollbackModel(RollbackSpec)`
- `GetModelLifecycle(model_version)`

### Safety gates

Promotion requires:
- regression budget checks;
- canary threshold pass;
- explainability artifact attached;
- rollback plan reference.

### Error model

- `LEARN_INVALID_STATE_TRANSITION`
- `LEARN_EVAL_FAILED`
- `LEARN_PROMOTION_BLOCKED`
- `LEARN_ROLLBACK_FAILED`
- `LEARN_INTERNAL`

## Observability

- state transition audit trail;
- promotion lead time;
- rollback frequency and root-cause labels;
- gate-failure counters.

## Test plan

- State-machine conformance tests.
- Negative tests for invalid transitions.
- Canary + rollback integration fixture.

## Compatibility and versioning

- **Version impact:** learning control-plane contract `1.0.0`.
- **Compatibility:** additive states/fields with backward-safe semantics are `MINOR`; transition-rule breaking changes are `MAJOR`.

## Open questions

- Cross-environment promotion policy (staging -> production).
- Default regression budgets per workload class.
