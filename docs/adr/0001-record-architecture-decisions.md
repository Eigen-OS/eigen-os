# ADR 0001: Record architecture decisions and RFC→ADR migration policy

- **Status:** Accepted
- **Date:** 2026-04-24
- **Deciders:** Core architecture maintainers

## Context

The repository contains implemented RFCs, but operational decisions were not consistently captured in ADR form. This made it harder to understand which proposals are now mandatory for implementation.

## Decision

1. Keep RFCs as proposal/history documents under `rfcs/`.
2. Use ADRs under `docs/adr/` as the canonical record of implemented architecture decisions.
3. For every RFC marked `Implemented`, create or update one ADR that captures:
   - the active decision,
   - current constraints,
   - implementation consequences,
   - and references to source RFCs.
4. New implementation phases (such as MVP-2) must add ADRs for cross-service decisions before large code rollout.

## Consequences

- Decision history becomes easier to audit.
- New contributors can read stable decisions without parsing full RFC narratives.
- RFC status transitions now require ADR synchronization as part of delivery.

## References

- RFC process: `rfcs/0001-rfc-process.md`
- ADR index: `docs/adr/README.md`