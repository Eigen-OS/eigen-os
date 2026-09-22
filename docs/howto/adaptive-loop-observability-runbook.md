# Adaptive-loop observability runbook

Use this runbook to triage retrain queue saturation, candidate promotion failures, and rollback instability in the Phase-8C adaptive loop.

## Contract + versioning

Phase-8C alert assets are SemVer-governed and additive.

- `adaptive_loop_observability_asset_version: 0.5.0`
- `adaptive_loop_alert_contract_version: 1.0.0`

## Alert pack

- Alert rules: `monitoring/metrics/prometheus/adaptive-loop-alerts.yaml`

## Owner escalation map

1. `owner=adaptive-loop-oncall` — primary response owner (acknowledge within 10 minutes).
2. `team=ml-platform` — secondary escalation if alert remains firing for 20 minutes.
3. SRE duty manager — incident commander escalation for any critical alert that persists for 30 minutes.

## Alerts and response

### retrain-queue-pressure

Alert: `EigenAdaptiveLoopRetrainQueuePressureCritical`

1. Validate queue metrics: `eigen_adaptive_retrain_queue_depth` and `eigen_adaptive_retrain_queue_oldest_age_seconds`.
2. Inspect active retrain workers and capacity policies for throttle/backpressure changes in the latest rollout.
3. Drain low-priority retrain jobs, then temporarily increase retrain worker budget within approved safety limits.
4. If queue pressure persists, rollback latest adaptive-loop scheduler/policy change and open an incident timeline.

### candidate-promotion-failures

Alert: `EigenAdaptiveLoopPromotionFailuresSpike`

1. Confirm sample size guard is met (`rate(eigen_adaptive_promotion_attempts_total[15m]) > 0.2`).
2. Inspect gate failures by reason code and identify top failing policy checks.
3. Freeze new promotions and execute deterministic replay for the failing candidate cohort.
4. Escalate to model-governance reviewer before resuming promotions.

### rollback-rate

Alerts: `EigenAdaptiveLoopRollbackRateHigh`, `EigenAdaptiveLoopRollbackRateCritical`

1. Compute rollback ratio in the same 30-minute window used by alert logic.
2. Diff rollout artifacts (`policy_version`, candidate lineage hash, evaluation bundle) against last known stable promotion.
3. For critical ratio breach, force `ROLLBACK_TO_STABLE` and pause automatic promotions until root cause is mitigated.
4. Capture postmortem evidence: ratio trend, gate reasons, rollback execution timestamp, and owner acknowledgements.
