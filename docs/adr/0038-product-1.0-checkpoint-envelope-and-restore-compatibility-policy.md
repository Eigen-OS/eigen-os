# ADR 0038: Product 1.0 checkpoint envelope and restore compatibility policy

- Status: Accepted
- Date: 2026-06-11
- Deciders: Core maintainers
- RFC: `rfcs/0051-product-1.0-qfs-storage-authority-and-retention-semantics.md`

## Context

Wave 4 requires deterministic restore behavior for QFS checkpoints and replay snapshots. The repository already treats QFS L2 as a versioned checkpoint boundary, but the compatibility envelope was not yet recorded as an accepted governance decision.

## Decision

Adopt a versioned checkpoint envelope policy for Product 1.0 with the following requirements:

1. checkpoint envelopes must carry stable version metadata and restore compatibility markers,
2. restore attempts must reject version-incompatible payloads deterministically,
3. lineage and integrity metadata must remain queryable after archival,
4. checkpoint retention must preserve replay-safe evidence for supported versions,
5. restore failures must map to canonical error semantics.

## Consequences

### Positive

- Restore compatibility is deterministic and testable.
- QFS checkpoint replay stays aligned with the public error model.
- Migration guidance can be tied to explicit envelope versions.

### Trade-offs

- Future restore-envelope changes may require a MAJOR version increment.
- Checkpoint payloads must preserve a small amount of additional metadata.
- Operators must retain compatibility fixtures for the supported envelope window.

## Compliance notes

- This ADR is accepted and operational for Wave 4.
- Any change to the checkpoint envelope that breaks compatibility requires a MAJOR delta and updated migration notes.
- The Wave 4 closure evidence references this ADR as the checkpoint governance record.
