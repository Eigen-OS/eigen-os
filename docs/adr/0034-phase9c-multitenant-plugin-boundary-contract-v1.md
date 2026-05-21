# ADR 0034: Phase-9C Multi-tenant Plugin Boundary Contract v1

- Status: Accepted
- Date: 2026-05-21
- Deciders: Core maintainers
- RFC: `rfcs/0048-phase9c-multitenant-plugin-boundary-contract-v1.md`

## Context

Stage-9C of the TZ v1.3.0 alignment plan requires explicit separation between deterministic kernel behavior and high-variance tenant policy behavior. The project needs one accepted contract that governs tenant envelope semantics, plugin boundary enforcement, failure isolation, and explainability evidence.

## Decision

Adopt the Phase-9C multi-tenant plugin boundary contract as an operational baseline with these mandatory outcomes:

1. Tenant/project identity envelope and baseline quotas are core-owned and deterministic.
2. Advanced scheduling policies are plugin-only and cannot be embedded into kernel baseline behavior.
3. Plugin failures are isolated from kernel lifecycle and always trigger deterministic fallback paths.
4. Explain API includes tenant-aware decision provenance and stable fallback reason codes.
5. SDK/conformance tooling must provide policy-plugin scaffold + validate flows with fail-closed checks.
6. Versioning remains governed by RFC 0032 SemVer and migration-note policy.

## Consequences

### Positive

- Enforces clean open-core boundaries and keeps high-variance behavior outside kernel.
- Improves tenant incident triage via standardized explain evidence and reason codes.
- Reduces operational risk by making plugin failure behavior deterministic and auditable.

### Trade-offs

- Higher upfront SDK and conformance-test maintenance burden.
- Additional compatibility matrix and migration documentation work per Stage-9C iteration.

## Compliance notes

- This ADR defines governance and contract boundaries; it does not itself introduce a runtime breaking change.
- Any future breaking contract updates within Stage-9C scope require MAJOR bump and migration notes.
