# ADR 0041 — Product 1.0 Resource Manager Deployment Model

## Status

Proposed

## Decision

Resource Manager shall be treated as the canonical reservation and capacity coordination authority for Product 1.0 Wave 5, with one of the following final shapes:

1. standalone service,
2. embedded kernel module,
3. hybrid service with a stable internal API.

## Consequences

- explicit ownership boundary,
- compatibility notes for current placeholder reservation surface,
- no ambiguity for Kernel/QRTX consumers.
