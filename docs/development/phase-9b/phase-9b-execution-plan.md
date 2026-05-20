# Phase-9B Execution Plan — Intelligence Closure (TZ v1.3.0)

## Purpose

Phase-9B closes the mandatory **data-centric self-learning loop** from TZ v1.3.0 while preserving open-core boundaries defined in the Phase-9 alignment plan.

Primary outcomes:

- harden Knowledge Base (KB) contracts and storage semantics for deterministic learning inputs;
- introduce deterministic Pattern Miner and compiler recommendation flow;
- formalize DPDA/GNN quality feedback contracts with measurable non-regression gates;
- ship reproducible Continuous Learning (CL) training/validation/canary/hot-swap lifecycle.

## Scope and non-scope

### In scope

- KB immutability, anonymization, and indexing profile hardening.
- Pattern Miner service contract + run semantics.
- Compiler/optimizer consumption of KB context and recommendation payloads.
- CL trigger policy, model registry/versioning, validation and canary rollback paths.
- Phase-9B release gates and evidence bundle templates.

### Out of scope

- New experimental model families (plugin track).
- Tenant-specific ranking heuristics and BI analytics UX.
- Commercial workflow controls (SLA/billing/policy monetization).

## Normative constraints

- SemVer policy and migration discipline MUST follow `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`.
- Contract drift checks MUST remain fail-closed in CI.
- Any behavior affecting deterministic runtime fallback MUST include fixture evidence.

## Workstreams

1. **KB Integrity & Scale**
   - Immutable Circuit/Pattern/Task records.
   - User-ID anonymization hardening + re-identification risk checks.
   - Index profile and query latency SLO evidence.

2. **Pattern Miner & Recommendation Contract**
   - Deterministic background run cadence.
   - Recommendation API for compiler consumption.
   - Traceability from recommendation -> compile decisions -> execution result.

3. **DPDA/GNN Quality Signal Closure**
   - Stable metric schema (swap count, predicted noise, runtime, fidelity deltas).
   - Inference telemetry and confidence policy.
   - Deterministic fallback when confidence/regression gates fail.

4. **Continuous Learning Lifecycle**
   - Retrain trigger policy (`N` new circuits, time ceiling, or manual override).
   - Reproducible training package (dataset snapshot + config + model digest).
   - Canary rollout and auto-rollback.

5. **Governance / Docs / Exit Artifacts**
   - Issue pack, checklists, compatibility report, exit evidence mapping.
   - RFC/ADR sync for any new contracts or lifecycle policy decisions.

## Exit gates (Phase-9B)

Phase-9B is complete only when:

1. Retrain pipeline is reproducible from versioned inputs and recorded digests.
2. Canary rollout has deterministic rollback to previous model version on regression.
3. Benchmark report shows uplift or non-regression versus active production baseline.
4. KB contract changes are migration-documented and fixture-tested.
5. Phase-9B issue pack items are closed with objective evidence links.
