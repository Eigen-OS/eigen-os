# Product 1.0 Wave 2 Release Readiness Checklist

**Status:** Draft checklist for implementation closure
**Created:** 2026-06-02

## Scope

This checklist closes Product 1.0 Wave 2 and must be completed together with:

- `docs/development/product-1.0-wave-2-execution-plan.md`
- `docs/development/product-1.0-wave-2-issue-pack.md`
- `docs/development/product-1.0-wave-2-compatibility-report.md`
- `docs/development/product-1.0-wave-2-exit-evidence-bundle.md`
- `docs/development/product-1.0-wave-2-rfc-adr-gap-analysis.md`
- `rfcs/0050-product-1.0-kernel-qrtx-lifecycle-authority.md`
- `docs/adr/0036-product-1.0-kernel-qrtx-lifecycle-authority.md`

---

## Contract and governance gates

- [ ] RFC 0050 status is accepted or explicitly approved for implementation.
- [ ] ADR 0036 is synchronized with RFC 0050.
- [ ] Every Wave 2 issue includes the required Summary, Validation, Versioning & Compatibility, and Release Notes Draft blocks.
- [ ] Product 1.0 manifest/inventory are updated for any concrete internal proto/schema/conformance path changes.
- [ ] Every MAJOR or breaking internal change has migration notes and release evidence.
- [ ] Compatibility report has no unresolved `TBD` values for completed issues.

## Internal API gates

- [ ] KernelGateway proto/reference coverage matrix is complete.
- [ ] Internal metadata requirements cover security context, tenant/project, request ID, trace context, deadline, retry policy, and idempotency carry-through.
- [ ] Event/update subscription semantics are implemented or explicitly deferred with compatibility rationale.
- [ ] Dispatch rationale and result-reference behavior are documented and conformance-tested.
- [ ] Internal breaking changes are versioned and migration-documented.

## Kernel lifecycle gates

- [ ] Kernel/QRTX owns canonical lifecycle state for Product 1.0 public lifecycle requests.
- [ ] State-transition table is implemented and invalid transitions fail canonically.
- [ ] Durable/replayable state evidence proves restart/replay behavior or documents fixture limitations.
- [ ] Terminal-state precedence is deterministic for cancel, timeout, error, and success races.
- [ ] System API direct lifecycle mutation is removed, disabled, or legacy-gated.

## Orchestration gates

- [ ] Orchestration DAG stages cover validate/enqueue, compile, optimize, schedule, execute, persist, record observability/knowledge, and finalize.
- [ ] Stage records include stable IDs, inputs/outputs, timestamps, trace context, and error metadata.
- [ ] Submit-to-results integration test covers successful lifecycle.
- [ ] Failed-stage integration tests cover retryable and non-retryable failures.
- [ ] Placeholder adapters for future waves are explicit and cannot be mistaken for production implementations.

## Deadline, cancellation, and retry gates

- [ ] Deadline normalization and propagation are tested.
- [ ] Cancellation fan-out is tested for queued, compiling, executing, and finalizing/persisting paths where dependencies exist.
- [ ] Resource reservation release or cancellation marking is tested.
- [ ] Retry policy is bounded and tied to canonical retryability.
- [ ] Retry exhaustion produces canonical terminal error state.

## Observability and evidence gates

- [ ] Orchestration contract marker metrics are emitted.
- [ ] Metrics use bounded labels and stable semantics.
- [ ] Trace/request correlation survives delegation, DAG stages, retry, cancellation, and terminal states.
- [ ] Exit evidence bundle links all commands, fixtures, generated artifacts, and known limitations.
- [ ] Wave 3 handoff states that compiler/AQO closure can rely on Kernel-owned lifecycle semantics.

---

## Wave 3 handoff

Wave 3 may start after the Wave 2 closure commit. Wave 3 can rely on Kernel/QRTX as lifecycle authority, including deterministic state transitions, public-to-internal delegation, orchestration DAG stage records, cancellation/deadline propagation, bounded retry governance, and orchestration observability markers. Compiler/AQO work must integrate through these Kernel-owned contracts rather than reintroducing System API-owned lifecycle shortcuts.
