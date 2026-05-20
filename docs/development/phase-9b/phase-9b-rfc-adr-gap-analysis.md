# Phase-9B RFC/ADR Gap Analysis

## Goal

Identify whether the current RFC/ADR set is sufficient for **Stage B — Intelligence closure** from `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md`.

## Inputs

- `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md`
- `docs/development/phase-9b/phase-9b-execution-plan.md`
- `rfcs/0034-phase8a-knowledge-base-api-contract-v1.md`
- `rfcs/0035-phase8a-gnn-optimizer-service-contract-v1.md`
- `rfcs/0036-phase8a-continuous-learning-control-plane-contract-v1.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`

## Coverage matrix

| Stage-B requirement | Existing spec coverage | Gap decision |
|---|---|---|
| KB immutability + anonymization + index SLO profile | Partial in RFC 0034; immutability/anonymization policy not strict enough | **Gap: add/update normative policy** |
| Pattern Miner deterministic lifecycle + recommendation payload | Partially implied in roadmap/docs; not fixed as stable contract | **Gap: must be formalized** |
| DPDA/GNN quality feedback contracts and fallback policy | Split between RFC 0035 and implementation docs; fallback semantics under-specified | **Gap: align under one normative contract surface** |
| Continuous Learning retrain/canary/rollback determinism | RFC 0036 covers baseline CL control plane; rollback determinism + evidence schema incomplete | **Gap: extend policy** |
| Versioning/migration discipline | RFC 0032 sufficient | **No new gap** |

## Decision

A dedicated Phase-9B RFC is required to consolidate Stage-B requirements and tighten deterministic lifecycle semantics.

- **Action:** introduce `rfcs/0047-phase9b-intelligence-closure-contract-v1.md`.
- **ADR impact:** publish `docs/adr/0033-phase9b-intelligence-closure-contract-v1.md` to keep RFC→ADR synchronization explicit for Stage-B closure governance and evidence policy.

## Follow-up checklist

- [ ] Publish ADR 0033 and add it to `docs/adr/README.md`.
- [ ] Publish Phase-9B release checklist, compatibility report, and exit evidence bundle.
- [ ] Update `docs/development/README.md` with complete Phase-9B artifact links.
- [ ] Update compatibility fixtures for any new/changed payload schemas.
- [ ] Add migration notes for contract changes (if any breakage risk exists).
- [ ] Ensure CI includes Phase-9B conformance gates as required checks.
