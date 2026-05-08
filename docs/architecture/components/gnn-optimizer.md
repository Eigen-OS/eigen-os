# GNN Optimizer (state snapshot)

- **Phase:** Post-MVP / future runtime capability.
- **Implementation state (verified 2026-05-08):** No dedicated `gnn-optimizer` service/crate/module is implemented in the current codebase; component remains architectural target.
- **Scope note:** This page captures what exists *around* optimizer behavior today and what is still missing for the planned GNN-based optimizer, so the next phase can proceed without losing requirements.

## Responsibility

### Implemented now (adjacent behavior)

- Kernel has a narrow built-in hybrid loop path for VQE-like jobs with a simple iterative parameter update (`simple_gradient_free_step`), persisted metrics, and metadata tagging.
- Plugin ecosystem groundwork includes `optimizer` as an allowed plugin type in Phase-6 contracts and CLI validation/scaffolding.

### TODO (GNN optimizer target responsibility)

- TODO: Implement a dedicated GNN optimizer component responsible for graph-based qubit placement/routing/hardware adaptation decisions in the production execution path.
- TODO: Define boundary between compiler optimization passes, scheduler policy, and GNN optimizer decisions (ownership matrix + precedence rules).
- TODO: Define deterministic fallback behavior when GNN inference is unavailable/untrusted.

## RFC / ADR alignment

### What is already aligned

- `docs/rfcs-pointer.md` and `docs/development/phase-6-rfc-adr-gap-analysis.md` confirm Phase-6 plugin RFC package is accepted and includes `optimizer` in GA plugin type set.
- `docs/architecture/overview.md` marks full GNN hardware optimizer as TODO/not fully implemented.

### TODO (governance to add)

- TODO: Publish a dedicated RFC for GNN optimizer contracts (if not included in later phase package) covering:
  - input/output schema,
  - determinism/explainability constraints,
  - safety and rollback policy.
- TODO: Add synchronized ADR(s) once implementation decisions are finalized (service placement, inference trust model, compatibility policy).
- TODO: Extend release-readiness and compatibility reports for the phase where GNN optimizer lands.

## Interfaces

### Implemented now

- No RPC/API dedicated to `gnn-optimizer` exists.
- Existing compiler RPC `OptimizeCircuit` is currently `UNIMPLEMENTED` and does not expose GNN functionality.
- Kernel VQE optimization behavior is internal logic, not a stable optimizer plugin API.
- CLI plugin tooling accepts `optimizer` manifest type, but this does not yet imply runtime execution contract for GNN optimization.

### TODO

- TODO: Define optimizer RPC/API contract (internal gRPC and/or plugin ABI) with explicit versioning.
- TODO: Specify invocation points (compile-time, pre-execution routing pass, adaptive runtime loop).
- TODO: Add strict schema for optimizer request context (circuit graph, hardware topology/noise snapshot, policy hints, determinism mode).
- TODO: Add optimizer response schema (transformed circuit/routing plan, confidence, explanation payload, fallback reason).
- TODO: Document timeout budgets and cancellation semantics between kernel/compiler and optimizer.

## Inputs / Outputs

### Implemented now

- No dedicated GNN optimizer executable I/O contract is implemented.
- Related current optimizer-adjacent artifacts:
  - Kernel VQE loop consumes job metadata keys such as `max_iters`, `optimizer_step`, and hybrid markers.
  - Kernel emits VQE metrics JSON (`kind: vqe_metrics`, optimizer label `simple_gradient_free_step`) plus result metadata (`vqe.*`).

### TODO

- TODO: Define canonical optimizer input model:
  - circuit as graph/IR projection,
  - backend coupling map + calibration/noise data,
  - objective profile (latency/fidelity/cost),
  - policy and tenant constraints.
- TODO: Define canonical optimizer outputs:
  - placement/routing/transformation plan,
  - scored alternatives,
  - explanation trace and confidence,
  - deterministic digest/hash for reproducibility checks.
- TODO: Define compatibility policy for model/artifact versions and feature flags.

## Storage / State

### Implemented now

- No GNN model registry, feature store, or optimizer cache is implemented.
- No QFS layout is reserved specifically for GNN optimizer assets/results.
- Only current related persisted artifact is kernel VQE metrics in QFS metadata path.

### TODO

- TODO: Define QFS/object-store layout for optimizer artifacts:
  - model references/checksums,
  - feature snapshots,
  - decision traces,
  - replay bundles.
- TODO: Define retention/TTL and redaction policy for optimizer telemetry artifacts.
- TODO: Define training/serving state separation (offline datasets vs runtime inference cache).
- TODO: Add migration/versioning strategy for optimizer artifact schemas.

## Failure modes

### Implemented now

- No runtime failure modes for GNN optimizer itself because component is absent from execution path.
- Existing optimizer-adjacent path (kernel VQE loop) has generic execution/persistence failures but these are not GNN-specific.

### TODO

- TODO: Define fail-open/fail-closed behavior for optimizer errors per policy tier.
- TODO: Enumerate and codify failure classes:
  - model load/verification failure,
  - invalid topology/features,
  - inference timeout,
  - non-deterministic output drift,
  - policy/trust rejection.
- TODO: Define fallback chain (heuristic mapper/static pass/manual policy) and required audit markers.
- TODO: Define incident/severity mapping and SLO error budgets for optimizer availability.

## Observability

### Implemented now

- No metrics/logs/traces dedicated to GNN optimizer are emitted.
- Current VQE loop persists per-iteration metrics JSON, but this is not a GNN optimizer observability contract.

### TODO

- TODO: Define mandatory metrics set:
  - invocation count/latency,
  - timeout/error rates by class,
  - fallback frequency,
  - objective improvement deltas.
- TODO: Define trace spans and correlation IDs across kernel/compiler/optimizer boundaries.
- TODO: Define explainability payload contract for operator-facing diagnostics (why this mapping/route was chosen).
- TODO: Add conformance checks and dashboards/alerts for optimizer regressions.

## Security and trust

### Implemented now

- No dedicated GNN optimizer trust/security contract is implemented.
- Phase-6 plugin planning establishes trust/isolation direction (Sigstore/Cosign, OCI sandbox with `runsc`) at ecosystem level, but not yet materialized as GNN optimizer runtime integration.

### TODO

- TODO: Define model provenance and signature verification requirements before optimizer activation.
- TODO: Define sandbox/isolation boundary for optimizer execution mode (in-process vs out-of-process).
- TODO: Define data minimization policy for hardware telemetry/features passed to optimizer.
- TODO: Define policy controls for enabling/disabling adaptive ML decisions per tenant/environment.

## Integration plan checkpoints (next phase scaffold)

1. TODO: Publish optimizer contract RFC + acceptance criteria.
2. TODO: Implement minimal deterministic optimizer interface with heuristic baseline and explicit fallback.
3. TODO: Integrate optional GNN inference backend behind feature flag.
4. TODO: Add explainability + observability contract tests.
5. TODO: Produce ADR sync and release-readiness closure docs for the phase.

## Evidence used for this snapshot

- Architecture overview documents full GNN optimizer as not yet implemented and marks it as TODO in runtime services.
- Compiler component documents `OptimizeCircuit` as `UNIMPLEMENTED`.
- Kernel runtime contains only simple VQE iterative optimizer behavior (`simple_gradient_free_step`) and metrics persistence.
- Phase-6 planning/governance docs include `optimizer` plugin type and accepted RFC package, with ADR sync still pending for closure.
