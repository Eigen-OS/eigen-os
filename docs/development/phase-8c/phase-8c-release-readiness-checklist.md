# Phase-8C Release Readiness Checklist

- **Status:** Draft (for milestone execution)
- **Date:** 2026-05-19
- **Milestone:** M8C

Use this checklist at sprint reviews and release candidate evaluation for Phase-8C closure.

## 1) Governance and contract readiness

- [ ] RFC 0041 accepted and linked.
- [ ] RFC 0042 accepted and linked.
- [ ] RFC 0043 accepted and linked.
- [ ] ADR mirrors created/updated for all accepted RFC decisions.
- [ ] Compatibility matrix updates completed and versioned.

## 2) Adaptive-loop functional readiness

- [ ] Threshold trigger policy creates model versions automatically (default 1000 new circuits).
- [ ] Shadow validation stage executes for every candidate model.
- [ ] Canary promotion policy enforces non-regression blockers.
- [ ] Automated rollback activates on defined regression criteria.
- [ ] Deterministic fallback path for DPDA transitions validated.

## 3) Explainability and lineage readiness

- [ ] Decision logs are emitted for model-assisted and fallback decisions.
- [ ] Decision logs are queryable by trace ID and model version.
- [ ] KB lineage index links training inputs, evaluation bundles, and promotion outcomes.
- [ ] Incident triage queries are documented with sample workflows.

## 4) Quality and CI gate readiness

- [ ] Trigger gate (automatic version creation) is required and green.
- [ ] Canary non-regression gate is required and green.
- [ ] Rollback safety gate is required and green.
- [ ] Reproducible benchmark report/hash gate is required and green.
- [ ] Gate failures produce deterministic reason codes and mitigation hints.

## 5) Observability and operations readiness

- [ ] Alerts for retrain queue pressure are enabled.
- [ ] Alerts for promotion failures are enabled.
- [ ] Alerts for rollback storms are enabled.
- [ ] Runbooks exist and are linked for each critical alert.
- [ ] On-call escalation map is reviewed with component owners.

## 6) Exit evidence bundle completeness

- [ ] Benchmark gain vs baseline heuristic report is published.
- [ ] Reproducibility evidence artifact is published.
- [ ] Compatibility report is published.
- [ ] Release-note impact summary draft is prepared.
- [ ] Phase-8C closure sign-off is recorded by engineering + architecture owners.
