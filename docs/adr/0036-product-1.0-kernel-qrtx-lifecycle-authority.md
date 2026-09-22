# ADR 0036: Product 1.0 Kernel/QRTX Lifecycle Authority

- Status: Accepted
- Date: 2026-06-02
- Deciders: Core maintainers
- RFC: `rfcs/0050-product-1.0-kernel-qrtx-lifecycle-authority.md`

## Context

Product 1.0 Wave 1 stabilized the public API, JobSpec ingestion, public errors, idempotency, and public-boundary observability. The next Product 1.0 alignment step is to remove MVP lifecycle ownership shortcuts from System API and make Kernel/QRTX the canonical runtime control plane described by the architecture and internal API references.

Existing MVP and phase RFCs cover kernel execution, distributed queueing, tracing, lifecycle hardening, and observability, but they do not provide one Product 1.0 decision for the cutover from public gateway behavior to Kernel-owned lifecycle state, replayable state records, DAG orchestration, cancellation/deadline propagation, and retry governance.

## Decision

Adopt RFC 0050 as the governance baseline for Wave 2 implementation. Wave 2 implementation issues must:

1. reconcile KernelGateway internal proto and reference semantics before changing runtime behavior,
2. make Kernel/QRTX the single Product 1.0 authority for lifecycle state mutations,
3. preserve Wave 1 public API behavior while System API delegates lifecycle operations,
4. define and enforce canonical lifecycle transitions and invalid-transition errors,
5. persist or replay enough state to reconstruct lifecycle records and result references,
6. model the Product 1.0 orchestration DAG with deterministic stage records,
7. propagate deadlines, cancellation, and bounded retry policy through downstream stage adapters,
8. emit orchestration observability markers and trace continuity evidence,
9. record version impact, affected interfaces, compatibility, breaking marker, migration notes, and release-note draft text in every issue.

## Consequences

### Positive

- Runtime lifecycle ownership aligns with the Product 1.0 architecture.
- Public clients remain insulated from internal ownership changes.
- Wave 3 compiler/AQO closure can integrate through stable Kernel-owned lifecycle and DAG contracts.
- Internal breaking changes become explicit, versioned, and migration-documented.

### Trade-offs

- Wave 2 may require MAJOR internal API or lifecycle semantics changes.
- System API and Kernel/QRTX must coordinate closely to avoid public regressions.
- Durable/replayable state evidence increases implementation and testing scope before Wave 3 can rely on the boundary.

## Compliance notes

- This ADR is a planning and governance decision; it does not by itself change runtime behavior.
- Any Wave 2 implementation PR that changes internal contract behavior must update the Wave 2 compatibility report and Product 1.0 manifest/inventory when schema/proto/conformance mappings change.
- Public breaking changes are not authorized by this ADR; they require a separate public RFC/ADR.
