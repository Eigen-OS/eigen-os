# Phase 4 — Intelligent Runtime Plan

## Status

- **Phase**: 4 (Post-MVP)
- **Planning status**: Active (RFC package drafted)
- **Started on**: 2026-04-28
- **Last updated**: 2026-04-28
- **Previous phase closure**: [`phase-3-release-readiness-checklist.md`](phase-3-release-readiness-checklist.md)
- **Execution backlog**: [`phase-4-issue-pack.md`](phase-4-issue-pack.md)
- **RFC/ADR coverage check**: [`phase-4-rfc-adr-gap-analysis.md`](phase-4-rfc-adr-gap-analysis.md)

## Goal

Deliver an explainable, deterministic, and policy-configurable intelligent runtime layer that improves backend selection and scheduling outcomes without introducing opaque decision behavior.

## Scope (in)

1. **Backend scoring module**
   - Deterministic feature extraction from job/runtime/backend descriptors.
   - Weighted scoring model with explicit versioned scoring profile.
   - Explainability payloads that show factor contributions.

2. **Policy-configurable scheduling engine**
   - Policy bundles (`latency`, `throughput`, `cost`, `balanced`) with versioned defaults.
   - Deterministic tie-break and fallback rules.
   - Safe policy overrides with schema validation and guardrails.

3. **Explanation API surface (public + operator)**
   - `/explain/backend-selection`
   - `/explain/execution`
   - Stable explanation envelope with traceable rationale fields.

4. **Runtime intelligence observability**
   - Metrics for score computation latency, policy decisions, fallback frequency, and explain endpoint usage.
   - Structured logs and traces for decision lineage.
   - Dashboard + alert set for decision drift and scoring failures.

5. **Eigen-Lang integrations**
   - Compile-time diagnostics for unsupported or risky runtime targets.
   - Runtime-aware hints surfaced in compile output metadata.
   - Execution annotations carrying backend rationale identifiers.

## Scope (out)

- Black-box or proprietary model inference pipelines.
- Autonomous optimizer actions that cannot be traced to deterministic inputs.
- Distributed multi-node policy federation (Phase-5+).

## Exit criteria (Definition of Done)

1. Backend scoring contract is stable, versioned, and deterministic for identical inputs.
2. Policy engine enforces versioned policy bundles and deterministic conflict resolution.
3. Explanation APIs return structured and auditable rationale for backend and execution decisions.
4. Eigen-Lang emits runtime-intelligence metadata and diagnostics in a compatibility-tested format.
5. Observability pack covers score latency, fallback rates, explain endpoint errors, and policy drift signals.
6. Phase-4 RFC package and issue pack are published and cross-linked.

## Versioning constraints

- Scoring profile schema, policy bundle schema, and explanation API envelopes are SemVer-governed contracts.
- Breaking changes to decision semantics, explanation fields, or policy resolution rules require `MAJOR`.
- Backward-compatible optional metadata additions use `MINOR`.
- `PATCH` releases must not alter public decision or explanation semantics.
- Every decision artifact includes explicit contract-version markers.

## API/CLI targets

- API:
  - `/explain/backend-selection`
  - `/explain/execution`
- CLI (planned):
  - `eigen explain backend-selection`
  - `eigen explain execution`

## Dependencies and prerequisites

- Phase-3 runtime observability and contract baselines.
- Stable scheduler and execution metadata from Phase-2/Phase-3.
- Conformance and fixture harness for explanation outputs.

## Deliverables map

1. Planning + backlog: this document + [`phase-4-issue-pack.md`](phase-4-issue-pack.md).
2. Governance package: [`phase-4-rfc-adr-gap-analysis.md`](phase-4-rfc-adr-gap-analysis.md) + RFCs `0023/0024/0025` in `rfcs/`.
3. Implementation slices: scoring module, policy engine, explanation APIs, Eigen-Lang hints.
4. Release closure package (to be completed during execution):
   - `phase-4-release-readiness-checklist.md`
   - `phase-4-compatibility-report.md`

## Phase-4 default decisions (locked for v1)

The following defaults are now fixed for the initial Phase-4 implementation and should be treated as normative across RFC 0023/0024/0025.

### 1) Backend scoring feature allowlist

Scoring uses only features that are available pre-run or during orchestration, reproducible, user-explainable, and free from opaque-ML final-decision dependence.

#### Allowed feature groups

- **Job features**
  - `job_type`
  - `priority`
  - `shots`
  - `circuit_depth`
  - `circuit_width`
  - `estimated_runtime`
  - `backend_requirements`
  - `noise_sensitivity`
  - `deadline`
  - `cost_sensitivity`
- **Backend features**
  - `backend_type`
  - `qubit_count`
  - `availability`
  - `queue_length`
  - `historical_latency`
  - `historical_success_rate`
  - `historical_fidelity`
  - `error_rate`
  - `calibration_age`
  - `region`
  - `supported_features`
- **Runtime/context features**
  - `current_cluster_load`
  - `tenant_quota_state`
  - `retry_count`
  - `warm_cache_hit`
  - `previous_backend_attempts`
  - `data_freshness`
  - `observability_health`
- **Benchmark-derived features**
  - `benchmark_family`
  - `benchmark_similarity_score`
  - `expected_fidelity_delta`
  - `expected_latency_delta`
  - `transpilation_cost_estimate`

#### Explicitly disallowed in default path

- hidden embeddings without explanation mapping;
- opaque model logits as final decision input;
- features derived from private user data not required for execution;
- unstable features that cannot be audited later;
- any signal that cannot be persisted with the decision record.

#### Feature policy rules

Every feature must define:

- source;
- freshness window;
- fallback value;
- explanation text.

Every score contribution must be:

- bounded;
- monotonic, or explicitly documented as non-monotonic with rationale;
- visible in the decision trace.

Missing features must:

- use default fallback;
- be marked in explanation;
- never fail silently.

### 2) Rule-based policy priority ladder

Priority is rule-based and not a single unconstrained formula.

#### Level order

0. **Hard constraints** (reject candidate if violated)
   - compatible qubit count;
   - required backend type;
   - security/isolation policy;
   - tenant restrictions;
   - region constraints;
   - explicit user exclusions;
   - backend health minimum.
1. **Correctness / viability** (remove weak candidates)
   - estimated success probability;
   - supported gate set;
   - acceptable calibration age;
   - acceptable queue upper bound;
   - required runtime budget;
   - noise threshold.
2. **User intent**
   - latency, fidelity, cost, throughput, determinism, debuggability.
3. **Operational optimization** (tie-breakers)
   - queue length, cache-hit probability, backend locality, warm executor availability, batch compatibility.
4. **Learning-derived hints** (advisory only)
   - historical pattern match, benchmark similarity, previous run success on similar circuits.

#### Default priority map

```yaml
policy_priority_map:
  hard_constraints: 100
  correctness: 90
  user_intent: 70
  operational_optimization: 50
  learning_hints: 30

user_intent_weights:
  fidelity: 1.0
  latency: 0.8
  cost: 0.7
  throughput: 0.6
  determinism: 0.9
  debuggability: 0.85
```

#### Default selection strategy

1. filter by hard constraints;
2. rank by correctness;
3. apply user intent weights;
4. use operational tie-breakers;
5. apply learning hints only when they do not override levels above.

### 3) Explainability depth model

Three fixed explainability levels are required for testability:

- `L1_USER`: human-readable summary;
- `L2_ADMIN`: structured rationale;
- `L3_FORENSIC`: full decision trace.

#### User explainability (L1_USER)

Goal: answer “why this happened?” in plain language with shallow-to-medium depth.

Required fields:

- `selected_backend`
- `decision_summary`
- `top_factors`
- `rejected_backends`
- `confidence`
- `expected_latency`
- `expected_fidelity`
- `expected_cost_band`

Payload content expectations:

- chosen backend;
- top 3 reasons;
- rejected alternatives summary;
- estimated outcome;
- retry delta description;
- one-line recommendation.

L1_USER must avoid internal heuristics dumps, raw coefficient vectors (unless explicitly requested), and low-level trace noise.

#### Operator explainability (L2_ADMIN / L3_FORENSIC)

Goal: answer “what exactly did the engine do, and can we reproduce it?” with full detail.

Required fields:

- `policy_version`
- `feature_snapshot`
- `candidate_rankings`
- `score_breakdown`
- `constraint_rejections`
- `fallbacks_used`
- `source_freshness`
- `decision_hash`

Operator payload should include complete feature vector, normalized weights, candidate set, filtering reasons, scoring breakdown per backend, fallback usage, freshness status, trace ID, timestamp, and reproducibility hash.

Export formats:

- JSON;
- event log;
- trace span attributes.

### 4) SLOs for decision + explain engine

#### Latency SLOs

- Decision engine: `p95 < 150ms`, `p99 < 300ms`.
- Explain API:
  - `L1_USER p95 < 100ms`
  - `L2_ADMIN p95 < 200ms`
  - `L3_FORENSIC p95 < 500ms`

If full forensic output is too large, return immediate summary plus async export link/job id.

#### Availability SLOs

- Decision engine: `99.9%`
- Explain API: `99.5%`

If explainability is unavailable, scheduling continues via cached explanations, deferred generation, or degraded-but-safe mode.

#### Freshness SLOs

- backend telemetry freshness: `<= 30s`
- queue length freshness: `<= 10s`
- calibration freshness: `<= 5m`
- benchmark-derived advisory freshness: `<= 24h`

If data exceeds freshness window, it must be marked stale, confidence must be reduced, and stale advisory signals must not override hard constraints.

#### Consistency SLOs

- same input + same policy version + same feature snapshot => same decision;
- explanation hash must match decision hash;
- policy version must be embedded in every result.

#### Observability SLOs

Every decision emits:

- trace span;
- decision event;
- metric increment;
- policy version tag;
- backend candidate count;
- confidence score.

### 5) Minimal Phase-4 implementation contract

Phase-4 v1 must support:

- backend scoring;
- deterministic scoring function;
- feature allowlist;
- policy map;
- candidate filtering;
- explain APIs (`/explain/backend-selection`, `/explain/execution`);
- explain depths (`user`, `operator`, `forensic`);
- SLO monitoring for latency histogram, stale-data counter, fallback counter, and explanation-cache hit ratio.
