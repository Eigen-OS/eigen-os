# ADR 0030 — Phase-8D QDriver API v1 Final Contract and Conformance Semantics

- **Status:** Accepted
- **Date:** 2026-05-19
- **Deciders:** Runtime, Driver Manager, Platform Governance
- **Supersedes:** None
- **Superseded by:** None
- **RFC Link:** `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`

## Context

Phase-8D closure requires a frozen QDriver v1.0 contract with deterministic conformance behavior across official providers.

## Decision

Adopt RFC 0044 as the operational baseline for QDriver API v1.0 and enforce fail-closed conformance and drift checks in CI.

## Consequences

- Official provider adapters must pass required conformance gates.
- Contract deltas follow SemVer policy with migration-note enforcement for breaking changes.
- Closure evidence is tracked through the Phase-8D exit evidence bundle.
