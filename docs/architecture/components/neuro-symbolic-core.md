# Neuro-DPDA + ML Advisor Architecture Specification

- **Document status:** Normative architecture source of truth
- **Subsystem:** Compiler, Knowledge Base, Optimizer, Driver Manager integration boundary

- **Contract version:** `1.0.0`
- **Applies to:** `src/services/neuro-symbolic-service/`, Compiler (Neuro-DPDA path), Knowledge Base, GNN Optimizer, Driver Manager, Kernel/QRTX, QFS lineage, observability exporters
- **Last updated:** 2026-06-22

This document is the single source of truth for the boundary between:

1. the **symbolic core** (deterministic Neuro-DPDA / rule engine),
2. the **knowledge base** (authoritative retrieval and replay evidence store), and
3. the **ML advisor** (advisory scoring, ranking, and explanation).

If this document conflicts with any component note, this document wins.

The architecture defined here is deliberately strict:

- the symbolic core is **deterministic**,
- the knowledge base is **authoritative for stored facts and retrieved evidence**,
- the ML advisor is **advisory only**,
- no model may infer anything that is required to remain authoritative, replay-safe, or policy-bound.

---

## 0. Contract marker

All NSC telemetry exporters MUST expose:

```text
eigen_nsc_contract_info{version="1.0.0"} 1
```

---

## 1. Normative terms

### 1.1 Symbolic core

The symbolic core is the deterministic execution path that performs:

- grammar and state tracking,
- semantic legality checks,
- rewrite admissibility checks,
- lowering precondition checks,
- policy enforcement for hard constraints,
- replay evidence capture for the accepted rule chain.

The symbolic core is implemented as a deterministic pushdown automaton (DPDA) plus the compiler rule engine and the fixed policy evaluation path.

Its symbolic rewrite pipeline is a fixed sequence of explicit, independently invocable stages:

1. parse
2. normalize
3. candidate_generation
4. legality_check
5. rewrite
6. emit_aqo

Each stage MUST be deterministic, MUST log its own start and completion outcome, and MUST preserve the same replay identity when executed under the same frozen snapshots and normalized inputs.

The symbolic baseline is the same deterministic path with advisory inputs removed. When model output is absent, malformed, low-confidence, or rejected by validation, the symbolic baseline MUST run without consuming that output.

### 1.2 Knowledge base

The knowledge base stores and serves replay-safe facts, historical decisions, candidate patterns, canonical patterns, snapshots, and decision logs.

The knowledge base may return ranked candidates and canonical matches, but it does not invent new semantic truth. The stable request/response envelope for compiler queries is defined in `docs/architecture/components/knowledge-base.md` and `docs/reference/api/grpc-internal.md`.

### 1.3 ML advisor

The ML advisor is any neural, graph-based, boosted, heuristic, or statistical component used to:

- rank deterministic options,
- score candidates,
- explain an observed decision,
- suggest a bounded rewrite or routing option,
- estimate relative preference under an explicit policy snapshot.

The ML advisor never becomes the source of truth for legality, topology, policy, or device state.

The advisor-facing explainability envelope and the offline KB ingestion path MUST both carry the same stable tabular telemetry schema for graph size, fanout, stage counts, historical success rate, latency, backend, and policy-state features. The schema version MUST be `telemetry-tabular-v1`, and the payload MUST remain deterministic for identical normalized telemetry inputs.

---

## 2. Deterministic and advisory boundaries

### 2.1 Deterministic

The following are deterministic and must be decided without model inference:

- source parsing and AST acceptance,
- semantic legality,
- allowed rewrite admission,
- AQO validation,
- workload-profile resolution,
- canonical pattern selection when the matching rule is exact,
- device capability truth,
- device health truth,
- device topology truth,
- policy evaluation,
- replay identity,
- final acceptance or rejection of a compiler / optimizer / driver action.

### 2.2 Advisory only

The following may use the ML advisor, but only as input to deterministic logic:

- rewrite ranking,
- candidate ranking,
- explanation ranking,
- routing preference ranking,
- placement preference ranking,
- candidate retrieval prioritization,
- bounded confidence summaries.

Advisory output must never directly change semantics. It may only be consumed by a deterministic checker, reducer, or selector.

### 2.3 Must never be inferred by the model

A model, score function, or learned policy MUST NOT infer any of the following as authoritative truth:

- semantic legality,
- compiler acceptance,
- backend capability,
- backend availability,
- device topology,
- device health,
- queue state,
- tenant or project ownership,
- policy approval,
- authorization state,
- canonical pattern identity,
- replay identity,
- hidden compiler state,
- hidden driver state,
- secret material,
- unredacted payloads,
- success of a rule that has not been deterministically validated.

If any of the above is missing or ambiguous, the system MUST fail closed or fall back to the deterministic baseline.

---

## 3. Replay and snapshot rules

The same input, the same model snapshot, and the same policy snapshot MUST reproduce the same output.

Replay identity is therefore a function of:

- normalized request input,
- compiler/options state,
- model snapshot identifier and digest,
- policy snapshot identifier and digest,
- KB snapshot / record version where retrieval is part of the decision,
- deterministic rule version,
- deterministic serialization rules.

The following artifacts MUST be persisted for replay:

- selected symbolic rule identifiers,
- rejected symbolic rule identifiers when relevant,
- model recommendation identifiers,
- model snapshot version and digest,
- policy snapshot version and digest,
- KB record identifiers and snapshot identifiers used in the decision,
- final deterministic decision,
- final output digest,
- replay-safe explanation envelope.

The ML advisor may change across versions, but a replay run may only use the exact frozen snapshot recorded for the original decision. Live snapshot discovery on the replay path is prohibited.

---

## 4. Component responsibilities

### 4.1 Compiler integration

The compiler is authoritative for:

- parsing Eigen-Lang,
- AST validation,
- rule-engine approval,
- lowering,
- AQO emission,
- stage-by-stage symbolic rewrite pipeline invocation,
- compiler diagnostics,
- replay evidence for accepted and rejected rules.

The compiler may consume ML advisor output only as advisory input.

The compiler must never:

- accept an invalid IR because a model favored it,
- infer legality from model confidence,
- skip a rule-engine check,
- resolve a workload profile from model output,
- emit AQO that is not validated by the deterministic pipeline.

### 4.2 Knowledge base integration

The knowledge base is authoritative for:

- historical compile and runtime decision logs,
- candidate pattern retrieval,
- canonical pattern lookup,
- replay evidence storage,
- model/policy snapshot references stored with a decision.

The knowledge base must never:

- merge cross-tenant or cross-project evidence,
- treat model scores as canonical facts,
- fabricate canonicality,
- promote an unvalidated candidate to truth,
- hide the provenance of retrieved records.

Retrieval may be deterministic similarity search, exact lookup, or replay-safe candidate ranking, but the final choice still belongs to deterministic logic.

### 4.3 Optimizer integration

The optimizer is authoritative for:

- placement and routing decisions,
- topology-aware transformations,
- fidelity/cost trade-off selection,
- backend-adaptive planning,
- deterministic fallback when advice is unavailable or invalid.

The optimizer may use ML advisor output to rank or compare candidates, but it must not:

- infer topology from stale observations,
- infer device availability from model scores,
- infer noise or calibration truth from learned similarity alone,
- bypass explicit policy constraints,
- bypass canonical device capabilities published by the driver manager.

### 4.4 Driver Manager integration

The driver manager is authoritative for:

- device identity,
- device availability,
- device health,
- topology truth,
- capability truth,
- queue and capacity truth,
- provider normalization,
- execution dispatch outcomes.

The ML advisor may observe driver-manager snapshots, but it must not infer or override any driver-manager authority.

If the driver-manager snapshot and the model recommendation disagree, the driver-manager snapshot wins and the request must be evaluated again under deterministic rules.

---

## 5. Integration contract matrix

| Subsystem | Deterministic authority | ML advisor role | Forbidden inference |
|---|---|---|---|
| Compiler | legality, lowering, AQO validation, rule admission | rank rewrites and explain decisions | legality, profile, replay identity |
| Knowledge Base | record truth, canonical lookup, replay evidence | rank retrieval candidates | canonicality, cross-scope truth, hidden provenance |
| Optimizer | routing, placement, deterministic fallback | score candidate plans | topology, noise, availability, policy |
| Driver Manager | device truth, health, capability, queue | summarize or rank observed snapshots | device state, provider truth, secret state |

---

## 6. Deployment and boundary rules

### 6.1 Public ingress

NSC MUST NOT be exposed through public ingress.

Only internal callers may reach the service boundary.

### 6.2 Frozen snapshot rule

Every scoring or replay request MUST bind to:

- a frozen policy snapshot,
- a frozen model snapshot,
- a deterministic rule snapshot,
- a deterministic KB snapshot when KB evidence participates in the decision.

Live lookup of policy or model versions during request handling is forbidden.

### 6.3 Fail-closed rule

Missing snapshots, digest mismatches, integrity failures, policy mismatches, tenant/project boundary violations, missing model output, malformed model output, and low-confidence model output MUST fail closed.

When advisory output is absent, invalid, or below the policy-defined confidence threshold, the deterministic symbolic baseline MUST be used and the advisory result MUST be ignored for decision-making.

---

## 7. Explainability and auditability

Every accepted advisor-influenced decision MUST include a bounded replay envelope containing:

- caller identity,
- tenant and project identifiers,
- policy snapshot version,
- model snapshot version,
- KB record identifiers,
- selected symbolic rule identifiers,
- final deterministic outcome,
- a replay digest,
- a bounded explanation summary.

The explanation summary may describe why an advisory suggestion was accepted, rejected, or transformed, but it must not expose unbounded model output or unredacted KB data.

---

## 8. Relationships to other contracts

This document narrows the compiler role described in:

- `docs/architecture/components/compiler.md`
- `docs/architecture/components/compiler-neuro-symbolic-advisor.md`
- `docs/architecture/components/neuro-symbolic-advisory-boundary.md`

It also defines the boundaries that downstream docs must follow for:

- `docs/architecture/components/knowledge-base.md`
- `docs/architecture/components/gnn-optimizer.md`
- `docs/architecture/components/driver-manager.md`
- `docs/reference/api/grpc-internal.md`
- `docs/reference/compiler-observability-contract.md`
- `docs/reference/compiler-model-migration-notes.md`

Any document that describes one of these integrations MUST defer to this document for boundary semantics.
