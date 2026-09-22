# RFC-0051: Product 1.0 QFS storage authority and retention semantics

- Status: Proposed
- Created: 2026-06-11
- Target milestone: Product 1.0 Wave 4 QFS closure
- Depends on: RFC-0050, ADR-0037, ADR-0038, docs/reference/formats/qfs-layout.md, docs/architecture/components/qfs.md

## Summary

This RFC defines the Product 1.0 QFS ownership and retention model for QFS L1/L2/L3. It freezes which layer owns live-resource reservations, which layer owns checkpoint restore compatibility, and which layer owns durable artifact retention so that Wave 4 can close without ambiguous runtime authority.

## Motivation

Wave 4 requires deterministic replay, retention, and live-resource semantics. Without a single governance record, the repository could drift between QFS-owned, Resource Manager-owned, and split-authority interpretations. That ambiguity would make retention policy, checkpoint recovery, and live reservation cleanup impossible to certify.

## Goals

- Freeze the Product 1.0 QFS ownership boundary for live-resource semantics.
- Preserve deterministic replay evidence for QFS L2/L3 artifacts.
- Define retention classes for immutable, pinned, and operator-deletable records.
- Align the implementation snapshot with the Wave 4 closure evidence.

## Non-Goals

- Implementing the future Resource Manager scheduling authority.
- Redesigning the QFS storage backend abstraction beyond the Product 1.0 boundary.
- Introducing new public API behavior for non-QFS surfaces.

## Reference-level design

- **QFS L3** owns immutable artifact persistence, integrity checks, and lineage metadata.
- **QFS L2** owns checkpoint envelope persistence and restore compatibility checks.
- **QFS L1** owns live reservation evidence and replay markers for runtime gating, while Kernel/QRTX remains the current runtime authority for live execution tokens.
- Retention policy must distinguish immutable, pinned, and operator-deletable records.
- Replay bundles must be deterministic and reference stable artifact identifiers.

## Security and privacy

Retention and replay artifacts must not expose secrets, credentials, or tenant-private data outside the authorized boundary. Any surfaced replay metadata must remain compatible with the canonical error model and public security policy.

## Observability

QFS storage and retention changes must preserve contract marker metrics, bounded labels, and trace continuity. Storage and replay failures must map to canonical public error semantics.

## Implementation and migration

- Update the Wave 4 QFS closure docs and manifest alignment evidence.
- Keep the current runtime behavior backward-compatible for Product 1.0 callers.
- Record migration notes only if a later MAJOR change reassigns live-resource ownership.

## Considered alternatives

- Full QFS ownership of live-resource semantics.
- Full Resource Manager ownership of live-resource semantics.
- Split authority with no stable boundary.

The split authority model is selected because it matches the implemented Kernel/QRTX lifecycle authority while preserving a future handoff path.

## Acceptance criteria

- The QFS ownership boundary is unambiguous.
- Retention policy is deterministic and documented.
- Replay and lineage evidence remain queryable after archival.
- The Wave 4 closure package can reference this RFC as the governance record for the QFS MAJOR delta.
