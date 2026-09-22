# P9B-06 — Canary Rollout + Auto-Rollback on Regression

## Implemented contract updates

- `optimizer_evaluation` contract advanced to `1.5.0`.
- Continuous learning pipeline policy advanced to `1.4.0`.
- Canary policy now carries deterministic cohort and window fields:
  - `canary.cohort.dimension`
  - `canary.cohort.value`
  - `canary.evaluation_window_minutes`
- Canary outcomes are auditable with stable reason codes:
  - `CANARY_PROMOTION_APPROVED`
  - `CANARY_REGRESSION_VS_BASELINE_HEURISTIC`
  - `CANARY_INSUFFICIENT_SHADOW_SAMPLES`
- Auto-rollback now includes deterministic operational targets:
  - rollback `target_model_version`
  - rollback SLO (`slo_minutes=15`)
  - runbook reference for execution evidence.

## CI and release expectations

- Canary/rollback contract fields are fixture-covered by benchmark-service unit tests.
- Phase-9B gates must fail closed when canary reason codes indicate regression or insufficient evidence.
- Release evidence must include one rollback drill proving recovery within the SLO window.
