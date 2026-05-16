# ADR 0020: Phase-8A Knowledge Base API Contract v1

- **Status**: Accepted
- **Date**: 2026-05-16
- **Decision owners**: Runtime/Core, Architecture/Governance
- **Supersedes / Related**: RFC 0034, ADR 0018, ADR 0019

## Context

Phase-8A introduces a stable Knowledge Base (KB) API surface that must remain SemVer-governed and deterministic across request/response envelopes, error mapping, and traceability fields. RFC 0034 defines the normative contract package and acceptance constraints.

## Decision

Adopt RFC 0034 as the operational baseline for KB API v1 with the following implementation-binding requirements:

1. KB API payload/envelope schemas are versioned artifacts; additive fields require deterministic defaults.
2. Error taxonomy and retry semantics are contract-bound and must not drift undocumented.
3. Trace/correlation fields required by observability policy are mandatory in stable endpoints.
4. CI remains fail-closed on undocumented contract drift and missing migration notes for breaking changes.

## Consequences

- Runtime and integration teams can implement KB API features against a fixed v1 governance boundary.
- Backward-compatible growth proceeds via MINOR evolution with deterministic defaults.
- Breaking changes require MAJOR classification and explicit migration notes.

## Verification and evidence

- RFC source: `rfcs/0034-phase8a-knowledge-base-api-contract-v1.md`
- Synchronization pointers: `docs/rfcs-pointer.md`, `docs/development/README.md`
- Phase-8A closure docs: gap analysis, readiness checklist, compatibility report
