# Phase-8B Execution Plan (Runtime and Data Fabric Hardening)

- **Status:** Proposed
- **Date:** 2026-05-17
- **Source roadmap:** `docs/development/phase-8-implementation-roadmap-v1.1.0.md`
- **Milestone:** M8B

## Scope

Phase-8B hardens scheduler/runtime and storage/data fabric capabilities to production-readiness for research load profiles:

`submit -> dependency resolve -> priority/quota scheduling -> topology/noise-aware dispatch -> execute -> artifact persistence -> checkpoint/restore -> observability + alerting`.

## Required Phase-8B documentation package

1. This execution plan (implementation binding for sprint planning, CI gate mapping, and acceptance review).
2. Phase-8B issue pack (ready-to-use GitHub issues with acceptance criteria).
3. Phase-8B RFC/ADR gap analysis (whether new normative RFC/ADR updates are required beyond Phase-8A baselines).
4. Phase-8B release readiness checklist (operational exit verification for milestone closure).
5. Phase-8B compatibility report (documented version/support impact for runtime, QFS-L2/L3, and observability contracts).

## Workstreams and deliverables

### A. QRTX hardening

- Implement full DAG dependency resolver with deterministic cycle/missing-edge diagnostics.
- Implement priority + quota policy with fairness and starvation guardrails.
- Add topology/noise-aware dispatch hooks with deterministic fallback when telemetry is missing.
- Enforce idempotent, replay-safe lifecycle transitions across submit/schedule/dispatch/retry/cancel.

### B. QFS-L3 strict artifact fabric

- Enforce strict artifact layout and naming invariants.
- Introduce retention policy execution with deterministic cleanup reason codes.
- Add metadata indexing for artifact lookup and trace-linked navigation.

### C. QFS-L2 checkpoint/restore hardening

- Implement checkpoint/restore API behavior aligned to accepted envelopes.
- Add cost guardrails (size/time thresholds, admission controls, failure reason mapping).
- Add integrity verification for snapshot decode/replay and compatibility handling.

### D. Observability + alerting hardening

- Complete lifecycle span model for runtime stages (queue, schedule, dispatch, execute, persist).
- Join hardware telemetry with scheduler/execution spans via stable correlation IDs.
- Add alert packs for queue pressure, compiler regressions, and driver degradation.

### E. CI/release gate expansion for 8B

- Add synthetic load-test gate for queue scale (target: >=10,000 jobs).
- Add p95 enqueue latency trend gate in benchmark profile (target trend <=100 ms).
- Add artifact/checkpoint integrity and replay conformance gates.
- Add deterministic diagnostics for gate failures (reason code + mitigation hint).

## Acceptance criteria

Phase-8B is complete only when:

- load-test evidence demonstrates synthetic queue scale at or above 10,000 jobs;
- enqueue latency trend in benchmark environment is tracked and remains <= 100 ms p95 target envelope;
- artifact and checkpoint integrity suites are passing and versioned in CI;
- runtime lifecycle transitions are replay-safe and idempotency-tested;
- observability dashboards/alerts cover queue pressure, compiler regressions, and driver degradation;
- compatibility impact statement is published for runtime + storage surfaces.

## Dependencies

- Phase-8A accepted contracts and deterministic vertical-slice baseline.
- Existing Phase-7 compatibility and migration-note governance gates.
- Benchmark/synthetic workload fixture framework available in CI.

## Risks and mitigations

1. **Scheduler complexity/regression risk**  
   Mitigation: incremental policy rollout behind flags + replay fixture validation per merge.
2. **Storage consistency risk (L2/L3 interactions)**  
   Mitigation: strict schema/layout validators + integrity suite as required branch gates.
3. **Telemetry cardinality/performance risk**  
   Mitigation: bounded label policy + sampled deep traces + mandatory trend monitoring.
4. **SLO instability under mixed workloads**  
   Mitigation: enforce p95 trend gating and nightly scale probes with failure triage runbook.

## Exit review checklist

- [ ] Queue scale synthetic test (`>= 10,000`) is passing and evidence is linked.
- [ ] Enqueue latency p95 trend gate is green and documented.
- [ ] Artifact integrity gate is green with fixture evidence.
- [ ] Checkpoint/restore integrity gate is green with fixture evidence.
- [ ] Replay-safe lifecycle/idempotency suite is green.
- [ ] Observability alert pack is deployed and linked to runbooks.
- [ ] Phase-8B compatibility report is published and linked in release notes draft.
