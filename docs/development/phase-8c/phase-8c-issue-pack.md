This document is a ready-to-use set of GitHub issues for the **Phase-8C** stage of the roadmap.

**Context Sources:**
- `docs/development/phase-8/phase-8-implementation-roadmap-v1.1.0.md` (Section: "Phase-8C")
- `docs/development/phase-8c/phase-8c-execution-plan.md`
- `docs/development/post-mvp-open-source-roadmap.md` (phase progression context)
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md` (normative versioning constraints)

---

## Versioning & Compatibility Rules (Mandatory for every Phase-8C issue)

> Include this block in the description of every issue (as "Definition of Done / Constraints").

1. **SemVer is mandatory for stable contracts** across API, protobuf schemas, policy payloads, and persisted model metadata.
2. **Breaking behavior requires `MAJOR`** and explicit migration notes.
3. **Backward-compatible additions use `MINOR`** with deterministic defaults.
4. **`PATCH` is non-semantic only** (bug fixes, docs fixes, observability tuning).
5. **Deprecations require a fixed support window:** deprecated interfaces remain supported for 2 minor releases or 90 days, whichever is longer.
6. **Compatibility matrix updates are versioned artifacts** and must be fixture-tested.
7. **CI must fail closed** on undocumented contract drift and policy regressions.

---

## Milestone

- **Milestone:** `Phase-8C Adaptive Intelligence Loop`
- **Suggested labels:** `phase-8c`, `compiler`, `optimizer`, `learning`, `observability`, `ci`, `quality`

---

## Priority and ownership proposal (requires maintainer confirmation)

| Issue | Priority | Proposed owner group |
| --- | --- | --- |
| P8C-01 Eigen-DPDA Deterministic + Model-Assisted Transition Runtime | P0 | Compiler/Runtime |
| P8C-02 GNN Optimizer Baseline + Offline/Online Evaluation Harness | P0 | Optimizer/ML |
| P8C-03 Continuous Learning Trigger/Promotion/Rollback Pipeline | P0 | ML Platform + Runtime |
| P8C-04 Explainability Decision Log Schema + KB Lineage Indexing | P1 | KB/Data Platform + Compiler |
| P8C-05 Phase-8C CI Gate Bundle (Trigger, Canary, Rollback, Reproducibility) | P0 | QA/CI Infrastructure |
| P8C-06 Phase-8C Observability & Alert Pack for Adaptive Loop | P1 | Observability/SRE |
| P8C-07 Phase-8C Docs/RFC-ADR Sync + Exit Evidence Bundle | P1 | Architecture/Governance + Tech Writing |

---

## Issues

### P8C-01 — Eigen-DPDA Deterministic + Model-Assisted Transition Runtime

**Type:** Compiler / Runtime  
**Labels:** `phase-8c`, `compiler`, `runtime`, `quality`

**Problem** Deterministic execution guarantees are incomplete without hardened fallback behavior for model-assisted transitions.

**Scope**
- Implement deterministic fallback path for every model-assisted transition decision.
- Add stable reason-code mapping for selected/fallback transitions.
- Add replay fixture suite with fixed seeds and cross-runtime determinism checks.

**Acceptance Criteria**
- Fixed-seed replays produce identical transition traces.
- Missing/invalid model outputs are handled by deterministic fallback with stable diagnostics.
- CI blocks merges when determinism or reason-code invariants regress.

**RFC link**
- `rfcs/0041-phase8c-eigen-dpda-deterministic-model-assisted-transition-contract-v1.md`

---

### P8C-02 — GNN Optimizer Baseline + Offline/Online Evaluation Harness

**Type:** Optimizer / ML Runtime  
**Labels:** `phase-8c`, `optimizer`, `ml`, `quality`

**Problem** Adaptive optimization requires reproducible baseline scoring and trustworthy evaluation paths before production rollout.

**Scope**
- Implement topology-aware placement/routing baseline.
- Add offline evaluation harness with frozen datasets and deterministic metric bundle.
- Add online shadow evaluation harness with promotion blockers.

**Acceptance Criteria**
- Offline harness is reproducible across fixed fixtures.
- Shadow evaluation outputs promotion recommendation with explicit gate reasons.
- Regression against baseline heuristic blocks promotion.

**RFC link**
- `rfcs/0042-phase8c-gnn-optimizer-evaluation-and-promotion-contract-v1.md`

---

### P8C-03 — Continuous Learning Trigger/Promotion/Rollback Pipeline

**Type:** ML Platform / Control Plane  
**Labels:** `phase-8c`, `learning`, `runtime`, `quality`

**Problem** The self-learning loop is not production-safe without enforceable trigger, promotion, and rollback automation.

**Scope**
- Implement trigger policy (default every 1000 new circuits).
- Implement shadow validation + canary promotion policy.
- Implement automatic rollback on regression with runbook diagnostics.

**Acceptance Criteria**
- Threshold events create versioned model artifacts automatically.
- Canary policy enforces fail-closed non-regression behavior.
- Regression fixtures trigger automated rollback and stable reason codes.

**RFC link**
- `rfcs/0043-phase8c-continuous-learning-control-plane-and-safety-gates-contract-v1.md`

---

### P8C-04 — Explainability Decision Log Schema + KB Lineage Indexing

**Type:** Explainability / Data Platform  
**Labels:** `phase-8c`, `kb`, `observability`, `governance`

**Problem** Production adoption requires explainable model-assisted behavior and auditable lineage across traces and model versions.

**Scope**
- Define decision-log schema for DPDA and optimizer decisions.
- Persist and index model lineage in KB (training set hash, eval bundle hash, promotion policy version).
- Add query paths for incident triage and audit workflows.

**Acceptance Criteria**
- Decision logs are queryable by trace ID and model version.
- Lineage records link training input, evaluation evidence, and promotion outcome.
- Schema and index drift are CI-gated.

**RFC link**
- `rfcs/0041-phase8c-eigen-dpda-deterministic-model-assisted-transition-contract-v1.md`
- `rfcs/0042-phase8c-gnn-optimizer-evaluation-and-promotion-contract-v1.md`

---

### P8C-05 — Phase-8C CI Gate Bundle (Trigger, Canary, Rollback, Reproducibility)

**Type:** Quality / CI  
**Labels:** `phase-8c`, `ci`, `quality`

**Problem** Phase-8C closure requires automated release gates enforcing adaptive-loop safety and reproducibility.

**Scope**
- Add trigger gate for automatic model version creation.
- Add canary non-regression gate vs baseline heuristic.
- Add rollback safety gate and reproducibility hash gate.

**Acceptance Criteria**
- Gate bundle is required on `main` and release branch policy.
- Failures are fail-closed with deterministic reason codes + mitigation hints.
- Fixture evidence artifacts are versioned and linked.

**RFC link**
- `rfcs/0043-phase8c-continuous-learning-control-plane-and-safety-gates-contract-v1.md`

---

### P8C-06 — Phase-8C Observability & Alert Pack for Adaptive Loop

**Type:** Observability / SRE  
**Labels:** `phase-8c`, `observability`, `sre`

**Problem** Adaptive-loop incidents are difficult to triage without dedicated telemetry, alerting, and runbook alignment.

**Scope**
- Add telemetry for retrain queue pressure, candidate promotion failures, rollback rates.
- Define alert thresholds + noise suppression strategy.
- Link alerts to incident response runbooks and owner escalation map.

**Acceptance Criteria**
- All critical adaptive-loop failure classes emit actionable alerts.
- Alert thresholds are fixture-validated for deterministic trigger behavior.
- Runbook coverage is complete for each critical alert.

**RFC link**
- `rfcs/0043-phase8c-continuous-learning-control-plane-and-safety-gates-contract-v1.md`

---

### P8C-07 — Phase-8C Docs/RFC-ADR Sync + Exit Evidence Bundle

**Type:** Governance / Documentation  
**Labels:** `phase-8c`, `docs`, `governance`

**Problem** Phase-8C cannot be closed without synchronized execution/governance documentation and linked evidence.

**Scope**
- Publish Phase-8C execution/issue/checklist/compatibility package.
- Synchronize accepted RFCs with mirrored ADR decisions.
- Produce exit evidence bundle with CI gates and release-note impact summary.

**Acceptance Criteria**
- Phase-8C planning artifacts are linked from `docs/development/README.md`.
- RFC/ADR coverage decision is explicit and references accepted Phase-8C contracts.
- Exit bundle includes CI evidence and compatibility statement.

**RFC link**
- `rfcs/0041-phase8c-eigen-dpda-deterministic-model-assisted-transition-contract-v1.md`
- `rfcs/0042-phase8c-gnn-optimizer-evaluation-and-promotion-contract-v1.md`
- `rfcs/0043-phase8c-continuous-learning-control-plane-and-safety-gates-contract-v1.md`
