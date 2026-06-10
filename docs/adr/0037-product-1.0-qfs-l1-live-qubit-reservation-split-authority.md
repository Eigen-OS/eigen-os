# ADR 0037: Product 1.0 QFS-L1 live qubit / reservation split authority

- Status: Accepted
- Date: 2026-06-11
- Deciders: Core maintainers
- RFC: `docs/development/wave-4/product-1.0-wave-4-issue-pack.md` (W4-03)

## Context

Product 1.0 Wave 4 closes the ownership boundary for live-resource semantics.
The repository already has a Kernel/QRTX-owned lifecycle runtime with deterministic
stage records, cancellation, deadlines, and replay snapshots. Resource Manager,
per architecture, remains the target coordination layer for device-capacity
reservations and fairness, but it is not yet a standalone implemented service.

QFS-L1 live qubit semantics therefore need a stable Product 1.0 boundary that
does not pretend Resource Manager is already authoritative in the current MVP.

## Decision

Adopt a split authority boundary:

1. **Kernel/QRTX owns live execution reservation tokens and lease TTLs** for
   runtime gating, cancellation/deadline cleanup, and replay determinism.
2. **Resource Manager remains the target owner of device-capacity reservation
   coordination** for future Phase-1+ hardware scheduling semantics.
3. **QFS stores replay lineage and reservation evidence**, but does not own live
   scheduler authority.

This decision applies to Product 1.0 Wave 4 implementation and aligns runtime
behavior with the existing Kernel/QRTX lifecycle authority decision.

## Consequences

### Positive

- Live reservation semantics are deterministic inside Kernel/QRTX.
- Replay snapshots can include reservation token/lease lineage without moving
  runtime ownership into QFS.
- Resource Manager documentation can remain forward-looking without claiming
  unimplemented authority.
- Cancellation, deadline, and stale cleanup paths can be tested without a
  hidden ownership gap.

### Trade-offs

- Kernel/QRTX must expose and maintain explicit reservation state metadata.
- Future Resource Manager implementation will need a well-defined handoff path.
- Product 1.0 retains a split boundary rather than a single monolithic owner.

## Compliance notes

- This ADR is accepted and operational for Wave 4.
- Any public API or contract change caused by this boundary must still follow
  the Product 1.0 version policy.
- Public-facing reservation behavior remains compatibility-preserving.
