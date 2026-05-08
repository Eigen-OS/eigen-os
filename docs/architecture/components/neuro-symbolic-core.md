# Neuro-Symbolic Core (state snapshot)

- **Phase target:** Post-MVP / Phase 1+ evolution track.
- **Snapshot date:** 2026-05-08.
- **Current implementation state:** **not implemented as an active runtime component**; architecture intent is preserved across RFC and architecture docs, while runtime currently executes without a dedicated neuro-symbolic service.

## Responsibility

### Implemented now (what exists in codebase)

- There is **no standalone `neuro-symbolic-core` service/crate/module** in the runtime path (`system-api → eigen-kernel → eigen-compiler/driver-manager`).
- Existing runtime behavior uses deterministic MVP compilation and kernel execution contracts; neuro-symbolic decisions are not part of released execution-critical logic.
- Some adjacent concepts exist as placeholders or non-core naming:
  - plugin manifest type `optimizer` is implemented at CLI/contract level (Phase-6 plugin surface), but this is **not** the neuro-symbolic core.
  - simple optimization metadata is present in kernel VQE-flow related fields, but no hybrid neural-symbolic policy engine is wired.

### TODO (missing responsibility to implement)

- TODO: introduce explicit bounded responsibility of Neuro-Symbolic Core as a first-class component (compile-time + run-time adaptation scope split).
- TODO: define deterministic safety envelope for when neuro-symbolic recommendations are advisory vs authoritative.
- TODO: specify integration contract with `eigen-compiler` (AST/AQO enrichment), `eigen-kernel` (scheduling/routing hints), and `knowledge-base` (retrieval/writeback loop).
- TODO: define lifecycle states for model artifacts (train/candidate/active/rollback).

## RFC / ADR alignment re-check

### Confirmed status in repository indexes

- `docs/rfcs-pointer.md` marks:
  - MVP-2/3 and Phase-3/4/5 contract sets as implemented/accepted with ADR sync.
  - Phase-6 plugin package prepared/accepted in pointer, with ADR sync pending for that phase.
  - Phase-7 policy/toolchain RFCs accepted with ADR sync.
- No dedicated RFC/ADR currently declares a released neuro-symbolic runtime core as implemented.
- Neuro-symbolic capabilities remain roadmap/target architecture items (including architecture overview and goals/mission docs), not current runtime closure artifacts.

### TODO (RFC/ADR work items)

- TODO: create a dedicated Neuro-Symbolic Core RFC package (minimum: service contract, safety policy, observability, rollback/versioning).
- TODO: add synchronized ADR(s) once RFC status reaches Accepted/Implemented.
- TODO: add phase gap-analysis document specifically for neuro-symbolic rollout readiness and dependency gates.
- TODO: bind neuro-symbolic claims in `docs/architecture/overview.md` to explicit acceptance criteria and closure artifact links.

## Interfaces

### Implemented now

- No gRPC service, REST endpoint, or internal RPC owned by a neuro-symbolic-core component.
- No protobuf package, no service discovery registration, and no CLI command targeting a dedicated neuro-symbolic service.
- No plugin runtime interface currently maps to a concrete neuro-symbolic execution contract.

### TODO

- TODO: define `NeuroSymbolicService` gRPC API (recommended initial methods):
  - `ScoreCompilationPlan`
  - `SelectOptimizationStrategy`
  - `RecommendBackendMapping`
  - `ExplainDecision`
- TODO: define strict request/response schemas with versioned confidence, provenance, and determinism fields.
- TODO: formalize timeout, fallback, and error-handling semantics so kernel/compiler remain operational if service is unavailable.
- TODO: define compatibility profile with Phase-7 versioning policy (deprecation, additive fields, feature flags).

## Inputs / Outputs

### Implemented now

- No executable neuro-symbolic input contract exists in current runtime.
- Inputs that *could* be candidates in future (AST, AQO, backend metrics, topology) are processed today by other components under their own contracts.
- No structured neuro-symbolic decision artifact is emitted to QFS or result APIs.

### TODO

- TODO: define canonical input bundles:
  - compiler-side: normalized AST features + candidate AQO variants,
  - runtime-side: backend capability snapshots, noise/topology telemetry, SLO constraints,
  - historical-side: knowledge-base retrieval candidates.
- TODO: define output artifact schema:
  - ranked action set,
  - confidence + uncertainty,
  - explainability payload,
  - policy compliance flags.
- TODO: persist output artifact in QFS (Level 3) with replay metadata for audit/reproducibility.

## Storage / State
### Implemented now

- No dedicated persistent state/schema/table/object-store namespace for neuro-symbolic core.
- No model registry path, feature store, or decision cache wired in runtime.
- No periodic training/evaluation job contract in scheduler/runtime for this component.

### TODO

- TODO: define storage split:
  - online inference cache,
  - offline training datasets,
  - model registry and signed model manifests,
  - policy/rules snapshot storage.
- TODO: define migration/versioning policy for feature schemas and model metadata.
- TODO: define retention/privacy/security controls for telemetry-derived training data.
- TODO: add backup/restore and rollback playbooks for model + rules state.

## Failure modes
### Implemented now

- Since component is not active, there are no runtime failure modes attributable to neuro-symbolic core.
- Existing runtime failures are handled by compiler/kernel/driver-manager contracts independently.

### TODO

- TODO: define explicit failure taxonomy:
  - inference timeout,
  - low-confidence/no-decision,
  - stale model,
  - policy violation,
  - KB retrieval miss,
  - incompatible feature schema.
- TODO: define mandatory fallback behavior per call site (compiler and kernel paths).
- TODO: define circuit-breaker and degraded-mode policy (deterministic baseline fallback).
- TODO: define operator runbook and automated remediation signals.

## Observability

### Implemented now

- No component-scoped metrics/logs/traces for neuro-symbolic core are emitted.
- Current observability available in system pertains to existing services only.

### TODO

- TODO: define minimal metrics set:
  - request count/latency/error rate,
  - fallback rate,
  - confidence distribution,
  - decision acceptance/rejection ratio,
  - drift indicators.
- TODO: define trace spans and correlation propagation to compiler/kernel traces.
- TODO: define explainability and audit log requirements (who/what model/version/why decision).
- TODO: define SLOs and alert thresholds before production enablement.

## Security and governance

### Implemented now

- No dedicated security perimeter exists because service is absent.
- Global platform security controls apply only to currently running components.

### TODO

- TODO: define signed model artifact verification and provenance policy.
- TODO: define RBAC for model promotion/rollback and policy edits.
- TODO: define isolation boundaries for inference runtime and plugin interactions.
- TODO: define red-team and adversarial robustness validation requirements.

## Incremental rollout plan (documentation-preserving TODO backlog)

1. TODO: **Contract phase** — publish RFC(s) + protobuf draft + compatibility matrix.
2. TODO: **Shadow phase** — run passive scoring against live traffic with deterministic baseline untouched.
3. TODO: **Advisory phase** — emit recommendations + explanations, no automatic actuation.
4. TODO: **Guarded actuation phase** — limited-scope enablement under policy gates and rollback switch.
5. TODO: **General availability** — conformance tests, SLO closure, ADR synchronization, release readiness report.

## Traceability checklist (to avoid losing scope)

- [x] Explicitly recorded that component is currently non-implemented in runtime.
- [x] Preserved target architecture intent from overview/mission/goals docs.
- [x] Re-checked RFC/ADR pointer alignment and marked missing neuro-symbolic contract package.
- [x] Added section-level TODOs for every missing capability area (interfaces, I/O, storage, failures, observability, security).
- [x] Added phased backlog so next stage can continue without scope loss.
