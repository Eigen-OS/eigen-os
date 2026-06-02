# RFC-0050: Product 1.0 Kernel/QRTX Lifecycle Authority

- Status: Proposed
- Created: 2026-06-02
- Target milestone: Product 1.0 Wave 2 Kernel Lifecycle Authority
- Depends on: RFC-0016, RFC-0026, RFC-0027, RFC-0028, RFC-0032, RFC-0038, RFC-0040, RFC-0049

## Summary

This RFC defines the normative Product 1.0 Wave 2 cutover that makes Kernel/QRTX the canonical lifecycle authority for job state, orchestration DAG execution, deadline/cancellation propagation, retry governance, result references, and orchestration observability.

## Motivation

Wave 1 stabilized the public boundary so external clients can submit, observe, cancel, and retrieve result references without depending on MVP-only request semantics. Product 1.0 now requires internal lifecycle ownership to align with the architecture: System API must act as public gateway and compatibility facade, while Kernel/QRTX owns runtime state and orchestration.

## Normative requirements

1. **Lifecycle authority:** Kernel/QRTX MUST be the single Product 1.0 authority for lifecycle state mutations.
2. **Public compatibility:** System API MUST preserve Wave 1 public behavior while delegating lifecycle operations to Kernel/QRTX.
3. **Internal API coverage:** `eigen.internal.v1` KernelGateway contracts MUST cover enqueue, status, cancel, results, update/event subscription, dispatch rationale, normalized security context, trace context, deadline policy, and retry policy.
4. **State machine:** Kernel/QRTX MUST define canonical states, terminal states, transition rules, terminal-state precedence, and invalid-transition errors.
5. **Replayable state:** Kernel/QRTX MUST persist or replay enough lifecycle data to reconstruct state, stage, timestamps, result references, cancellation intent, deadline, retry attempts, and canonical errors.
6. **Orchestration DAG:** Kernel/QRTX MUST model Product 1.0 stages for validate/enqueue, compile, optimize, schedule, execute, persist, record knowledge/observability, and finalize.
7. **Deadline propagation:** Kernel/QRTX MUST normalize deadlines and propagate them to downstream stage adapters.
8. **Cancellation fan-out:** Kernel/QRTX MUST fan out cancellation to queued, compiling, optimizing, scheduled, executing, and persisting work where those integrations exist, and MUST make cancellation idempotent.
9. **Retry governance:** Kernel/QRTX MUST govern retries through bounded policy tied to canonical retryability metadata from the error model and mapping matrix.
10. **Result references:** Kernel/QRTX MUST return result references through the Product 1.0 persistence boundary rather than System API-owned local state.
11. **Observability:** Kernel/QRTX MUST emit orchestration contract marker metrics, stage metrics/logs, and trace continuity evidence with bounded labels.
12. **Compatibility evidence:** Every internal breaking change MUST have version impact, migration notes, release notes, and conformance evidence.

## Compatibility policy

Wave 2 may introduce MAJOR changes to internal APIs, state-store semantics, lifecycle transitions, event/update streams, retry policy, and observability semantics when necessary to align with Product 1.0. Public Wave 1 behavior remains protected; public breaking changes require a separate public RFC/ADR.

## Acceptance criteria

- KernelGateway proto/reference coverage has no unexplained gaps.
- Kernel/QRTX state-machine tests cover valid transitions, invalid transitions, terminal-state precedence, replay/restart, cancellation, timeout, retryable failure, non-retryable failure, and result references.
- System API public conformance tests from Wave 1 pass through the Kernel/QRTX delegation path.
- Orchestration DAG integration tests cover submit-to-results and failed-stage paths.
- Observability tests prove bounded metric labels and trace continuity.
- Wave 2 compatibility report and evidence bundle are complete.

## Alternatives considered

### Keep lifecycle authority in System API

Rejected. This preserves MVP shortcuts and conflicts with the Product 1.0 architecture, where System API is the public gateway and Kernel/QRTX is the runtime control plane.

### Delay internal API changes until compiler/AQO closure

Rejected. Wave 3 compiler/AQO work needs a stable Kernel-owned lifecycle and DAG boundary. Delaying ownership would force compiler work to integrate with unstable state semantics.

### Implement only in-memory lifecycle authority

Allowed only as a temporary fixture-backed implementation if explicitly documented in evidence. Product 1.0 closure requires durable or replayable semantics before release certification.

## Rollout plan

1. Complete W2-01 contract matrix and state-machine decisions.
2. Implement W2-02 state store and transition validation.
3. Cut over W2-03 System API delegation while running Wave 1 public regression tests.
4. Add W2-04 DAG skeleton and stage records.
5. Add W2-05 cancellation/deadline fan-out.
6. Add W2-06 retry governance.
7. Add W2-07 observability and trace continuity gates.
8. Close W2-08 compatibility and evidence docs.

## Open questions

- Which persistence backend is the first production-grade Kernel state store?
- Does Product 1.0 require replay cursors for job update streams, or is server streaming with heartbeat sufficient for Wave 2?
- What is the minimal dispatch rationale payload that supports audit/explainability without leaking provider-private data?
- Which split/merge records are required in Wave 2 versus later multi-device closure waves?
