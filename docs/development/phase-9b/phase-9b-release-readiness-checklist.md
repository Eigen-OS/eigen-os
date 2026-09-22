# Phase-9B Release Readiness Checklist

## Scope

This checklist closes Stage-B (Intelligence closure) from `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md` and must be completed together with:

- `docs/development/phase-9b/phase-9b-compatibility-report.md`
- `docs/development/phase-9b/phase-9b-exit-evidence-bundle.md`
- `docs/development/phase-9b/phase-9b-rfc-adr-gap-analysis.md`

## Contract & governance gates

- [ ] RFC 0047 status is `Accepted` or `Implemented` with no unresolved normative TODOs.
- [ ] ADR 0033 is published and synchronized with RFC 0047 outcomes.
- [ ] SemVer impact is declared for all changed contract surfaces per RFC 0032.
- [ ] Migration notes are present for every breaking change (if any).
- [ ] CI fail-closed policy is preserved for contract-drift and conformance gates.

## Stage-B functional closure gates

- [ ] KB records are immutable on write-once fields (Circuit/Pattern/Task evidence captured).
- [ ] User-identifying dimensions in KB evidence are anonymized with deterministic policy.
- [ ] Indexed KB query profile meets Stage-B latency targets under fixture workload.
- [ ] Pattern Miner cadence is deterministic and replayable from versioned inputs.
- [ ] Compiler recommendation payloads are versioned and trace-linked to execution outcomes.
- [ ] DPDA/GNN quality schema is stable and includes swap/runtime/fidelity deltas.
- [ ] Deterministic fallback path is exercised for low-confidence/regression cases.
- [ ] Continuous Learning retrain trigger policy (`N` circuits / time ceiling / manual override) is documented and tested.
- [ ] Canary rollout gate and auto-rollback path are verified against baseline model.

## Evidence & reproducibility gates

- [ ] Reproducibility report includes dataset snapshot digest, config digest, model digest.
- [ ] Canary report includes explicit promotion/rollback threshold table and outcomes.
- [ ] Non-regression report includes benchmark comparison vs active production baseline.
- [ ] Rollback drill includes timestamped operator runbook trace and post-rollback health checks.
- [ ] All evidence links in Phase-9B issue pack resolve and are immutable.

## Documentation closure gates

- [ ] `docs/development/README.md` links to all Phase-9B planning/closure artifacts.
- [ ] RFC/ADR gap status is explicit and up-to-date.
- [ ] Phase-9B compatibility report is published with versioning rationale.
- [ ] Exit evidence bundle maps every acceptance criterion to objective evidence links.
