# ADR 0040: Product 1.0 Knowledge Base decision-log lineage contract

- Status: Accepted
- Date: 2026-06-11
- Deciders: Core maintainers
- RFC: `docs/development/wave-4/product-1.0-wave-4-issue-pack.md (W4-06)`

## Context

The Knowledge Base public service already persists records and decision logs with provenance, replay metadata, anonymization, and retention enforcement. Wave 4 needs the canonical replay-safe lineage structure recorded as an operational decision so runtime and benchmark flows can use it consistently.

## Decision

Adopt the following Product 1.0 decision-log lineage contract:

1. decision logs must capture deterministic identifiers, trace lineage, selected action, fallback usage, model version, and feature snapshots,
2. query semantics must be replay-safe and deterministic, including stable pagination order and cursor encoding,
3. provenance and replay metadata must survive archival and retention enforcement,
4. sensitive public attributes must be anonymized before persistence,
5. runtime and benchmark ingestion paths must use the same lineage contract.

## Consequences

### Positive

- Runtime decisions and benchmark replay evidence share one stable lineage model.
- Query and replay semantics remain deterministic across pagination and archival.
- Privacy-sensitive values are anonymized consistently.

### Trade-offs

- The lineage contract is intentionally bounded and does not expose raw private identity data.
- Future richer replay payloads must preserve the same deterministic contract shape.

## Compliance notes

- This ADR is accepted and operational for Wave 4.
- The closure evidence bundle and KB tests reference this contract directly.
- Any future change to replay semantics or anonymization boundaries requires explicit compatibility review.
