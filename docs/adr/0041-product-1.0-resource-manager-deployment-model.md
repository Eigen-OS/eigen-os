# ADR 0041 — Product 1.0 Resource Manager Deployment Model

## Status

Proposed

## Context

Wave 5 needs a canonical ownership decision for device inventory, reservations,
and capacity coordination. The repository already has an active Kernel/QRTX
orchestration layer and a Driver Manager that is the canonical source of device
topology and capability truth.

## Decision

Resource Manager is adopted as a **kernel-owned internal authority** for Product
1.0 rather than a separate standalone public service.

In this model:

- QRTX remains the runtime lifecycle authority.
- Driver Manager remains the device-truth source.
- Resource Manager materializes deterministic inventory snapshots from Driver
  Manager topology/capability metadata and supplies allocation/reservation
  inputs to QRTX.
- The current public reservation surface remains a compatibility layer until the
  kernel-owned authority is fully wired.

## Consequences

- No new public service boundary is introduced for Product 1.0.
- Device inventory semantics become explicit and replay-safe.
- Reservation compatibility can be maintained without pretending the MVP surface
  is the canonical authority.
- Future implementation work can evolve the internal boundary without changing
  the external ownership model.

## Required follow-up

- Update the Resource Manager architecture document.
- Update the contract inventory and manifest.
- Keep compatibility notes for the current MVP reservation behavior.
- Reference this ADR from the Wave 5 issue pack and release evidence bundle.
