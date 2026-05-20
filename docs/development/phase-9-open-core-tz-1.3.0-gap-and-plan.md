# Phase 9 — Open-Core Alignment Plan for TZ v1.3.0

## Purpose

This document translates the current implementation analysis into an actionable plan to reach **100% coverage of TZ v1.3.0 requirements** while preserving a **clean, flexible open core**.

Primary objective:

- keep mandatory runtime/orchestration/data/security functionality in kernel scope;
- move non-mandatory or policy-heavy behavior to plugins/SaaS where possible;
- keep contracts open, versioned, deterministic, and test-gated.

## 1) Open-Core Scope Decision (Normative)

### 1.1 Must remain in open core (required by TZ)

- Eigen-Lang core DSL and deterministic validation/runtime wrappers.
- System API (gRPC/REST) with authn/authz hooks.
- QRTX scheduler and lifecycle state machine.
- QFS L3 (CircuitFS), QFS L2 (checkpoint store), QFS L1 (Live Qubit Manager).
- Driver Manager + HAL (QDriver API contracts).
- Security module (PDP, secret-management integration contracts, audit).
- Observability stack contracts and SLO metrics.
- Baseline compiler/optimizer runtime path (DPDA + GNN integration points).
- Contract/version compatibility checks, CI conformance gates, reference docs.

### 1.2 Must be pluggable or externalized (non-core)

- Advanced scheduling policies (batch/preemption/tenant heuristics beyond baseline fairness).
- Extended ML model families and experimental optimizer heads.
- Heavy analytics, BI/reporting UX, dashboards beyond core SRE telemetry.
- Marketplace/distribution experiences.
- Billing/SLA commercial controls.

### 1.3 Boundary rule

Anything that can change frequently per tenant/customer without changing deterministic kernel guarantees should default to plugin/SaaS.

## 2) Gap Matrix vs TZ v1.3.0

| Area | Current state | Gap | Target outcome |
|---|---|---|---|
| Eigen-Lang + System API | Base decorators/API live | Missing expanded DSL contracts, error taxonomy hardening | Finalized DSL/API specs with deterministic diagnostics |
| QRTX | Lifecycle/DAG/retry implemented | SLA-grade allocation/quota/deadline behavior incomplete | Core scheduler SLO compliance and deterministic policy baseline |
| QFS L2 | Checkpoint/restore partial hardening | Quotas/retention/cache/eviction need closure | Fully recoverable, quota-safe checkpoint fabric |
| LQM (QFS L1) | Partial integration | Atomic allocation + failover + driver wiring incomplete | Production-ready LQM with telemetry and resilience |
| Driver Manager + HAL | Core API + trust baseline present | Driver coverage, packaging, factory ergonomics incomplete | Signed multi-backend driver pack + stable onboarding path |
| Security | JWT/mTLS/audit baseline | Unified PDP enforcement, Vault/KMS lifecycle, attack rules | End-to-end zero-trust + auditable policy enforcement |
| KB + Continuous Learning | Ingest/search baseline | Immutability, scale, pattern miner, retrain automation | Data-centric closed loop with safe model promotion |
| Observability | Metrics/logs/tracing baseline | Coverage gaps on compile/fidelity/scheduler SLO traces | Full critical-path observability with release gates |
| Compatibility/docs | Existing SemVer assets | RFC0032 migration discipline + TZ scenario examples | Complete operator/developer documentation and migration paths |

## 3) Delivery Stages

## Stage A — Core closure (critical path)

Focus: unblock mandatory kernel compliance.

- QFS L2 completion: retention, quotas, LRU restore cache, recovery tests.
- LQM completion: atomic qubit allocation, offline-node handling, reconnect policy, QDriver wiring.
- Security convergence: PDP enforcement in QRTX/LQM/QFS/KB paths; Vault/KMS integration; rate/anomaly rules + Alertmanager links.
- Driver hardening: signed driver loading mandatory; official simulator+cloud driver matrix.
- CI/security gates: SAST/DAST/SBOM plus contract conformance and failure-injection tests.

**Exit gates:**

- all Stage A issue-pack checks green;
- new contracts fixture-locked;
- documented migration notes and rollback procedures.

## Stage B — Intelligence closure (required by TZ learning loop)

Focus: fulfill data-centric self-learning requirements without polluting kernel.

- KB hardening: immutable records, user-id anonymization, scaled indexing profile.
- Pattern Miner background service and compiler-facing recommendation API.
- DPDA/GNN integration with KB context and quality metrics (SWAP/fidelity/runtime).
- Continuous Learning pipeline: retrain trigger (every N new circuits), validation, canary rollout, hot model swap.

**Exit gates:**

- reproducible retrain pipeline evidence;
- deterministic fallback to previous model on canary regression;
- benchmark uplift or non-regression report.

## Stage C — Multi-tenant policy + plugin-first expansion

Focus: keep kernel minimal and move variability outward.

- Core: tenant/project fields, base quotas, fair queueing primitives.
- Plugins: optional advanced scheduling (batch/preemption/backfill/drift-aware scoring).
- Explain APIs: `/explain` decision evidence for backend/scheduling outcomes.
- Plugin SDK updates: policy plugin templates, conformance test fixtures, trust/sandbox defaults.

**Exit gates:**

- core remains deterministic with plugins disabled;
- plugin failures isolated from kernel lifecycle;
- compatibility matrix updated and fixture-verified.

## Stage D — Docs, SDK, ecosystem hardening

Focus: operability and contributor scalability.

- Spec updates: JobSpec/AQO/QFS/KB contracts + version-impact templates.
- Guides: Eigen-Lang (VQE, benchmark), cluster ops, plugin authoring, security runbooks.
- CLI/SDK ergonomics: `plugin scaffold/validate`, benchmark compare/report.
- Contribution/roadmap hygiene: issue-pack templates, release checklists, migration playbooks.

**Exit gates:**

- docs smoke checks pass;
- quickstart paths reproducible;
- release checklist artifacts complete.

## 4) Pluginization Backlog (Extract from core)

Candidates to explicitly remove from core over Stage C-D:

- non-baseline scheduling heuristics;
- experimental optimizer variants;
- optional analytics/report rendering;
- backend-specific UX adapters.

Policy: every extraction must keep an open contract and have at least one reference plugin implementation.

## 5) Issue Pack Template (for every stage)

Each stage must ship with:

1. **Issue pack:** prioritized GitHub issues by component (kernel, compiler, storage, security, docs).
2. **Release gates:** measurable pass/fail criteria (tests, latency/error/fidelity thresholds).
3. **Docs delta:** specs + migration notes + examples updated in same milestone.

## 6) Definition of Done for TZ v1.3.0 Alignment

Alignment is complete only when all are true:

- mandatory TZ components are implemented in open core with deterministic behavior;
- optional/high-variance features are pluginized or externalized;
- CI enforces contracts, security, and compatibility;
- docs cover operator, developer, and integrator paths with versioned migration guidance.
