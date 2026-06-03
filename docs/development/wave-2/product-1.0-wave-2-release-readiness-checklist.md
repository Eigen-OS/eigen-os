# Product 1.0 Wave 2 Release Readiness Checklist

**Status:** Wave 2 closure checklist completed for documentation/evidence gates
**Created:** 2026-06-02

## Scope

This checklist closes Product 1.0 Wave 2 and must be completed together with:

- `docs/development/wave-2/product-1.0-wave-2-execution-plan.md`
- `docs/development/wave-2/product-1.0-wave-2-issue-pack.md`
- `docs/development/wave-2/product-1.0-wave-2-compatibility-report.md`
- `docs/development/wave-2/product-1.0-wave-2-exit-evidence-bundle.md`
- `docs/development/wave-2/product-1.0-wave-2-rfc-adr-gap-analysis.md`
- `rfcs/0050-product-1.0-kernel-qrtx-lifecycle-authority.md`
- `docs/adr/0036-product-1.0-kernel-qrtx-lifecycle-authority.md`

---

## Contract and governance gates

- [x] RFC 0050 status is accepted or explicitly approved for implementation.
- [x] ADR 0036 is synchronized with RFC 0050.
- [x] Every Wave 2 issue includes the required Summary, Validation, Versioning & Compatibility, and Release Notes Draft blocks.
- [x] Product 1.0 manifest/inventory are updated for any concrete internal proto/schema/conformance path changes.
- [x] Every MAJOR or breaking internal change has migration notes and release evidence.
- [x] Compatibility report has no unresolved `TBD` values for completed issues.

## Internal API gates

- [x] KernelGateway proto/reference coverage matrix is complete.
- [x] Internal metadata requirements cover security context, tenant/project, request ID, trace context, deadline, retry policy, and idempotency carry-through.
- [x] Event/update subscription semantics are implemented or explicitly deferred with compatibility rationale.
- [x] Dispatch rationale and result-reference behavior are documented and conformance-tested.
- [x] Internal breaking changes are versioned and migration-documented.

## Kernel lifecycle gates

- [x] Kernel/QRTX owns canonical lifecycle state for Product 1.0 public lifecycle requests.
- [x] State-transition table is implemented and invalid transitions fail canonically.
- [x] Durable/replayable state evidence proves restart/replay behavior or documents fixture limitations.
- [x] Terminal-state precedence is deterministic for cancel, timeout, error, and success races.
- [x] System API direct lifecycle mutation is removed, disabled, or legacy-gated.

## Orchestration gates

- [x] Orchestration DAG stages cover validate/enqueue, compile, optimize, schedule, execute, persist, record observability/knowledge, and finalize.
- [x] Stage records include stable IDs, inputs/outputs, timestamps, trace context, and error metadata.
- [x] Submit-to-results integration test covers successful lifecycle.
- [x] Failed-stage integration tests cover retryable and non-retryable failures.
- [x] Placeholder adapters for future waves are explicit and cannot be mistaken for production implementations.

## Deadline, cancellation, and retry gates

- [x] Deadline normalization and propagation are tested.
- [x] Cancellation fan-out is tested for queued, compiling, executing, and finalizing/persisting paths where dependencies exist.
- [x] Resource reservation release or cancellation marking is tested.
- [x] Retry policy is bounded and tied to canonical retryability.
- [x] Retry exhaustion produces canonical terminal error state.

## Observability and evidence gates

- [x] Orchestration contract marker metrics are emitted.
- [x] Metrics use bounded labels and stable semantics.
- [x] Trace/request correlation survives delegation, DAG stages, retry, cancellation, and terminal states.
- [x] Exit evidence bundle links all commands, fixtures, generated artifacts, and known limitations.
- [x] Wave 3 handoff states that compiler/AQO closure can rely on Kernel-owned lifecycle semantics.

---

## Wave 3 handoff

Wave 3 may start after the Wave 2 closure commit. Wave 3 can rely on Kernel/QRTX as lifecycle authority, including deterministic state transitions, public-to-internal delegation, orchestration DAG stage records, cancellation/deadline propagation, bounded retry governance, and orchestration observability markers. Compiler/AQO work must integrate through these Kernel-owned contracts rather than reintroducing System API-owned lifecycle shortcuts.
