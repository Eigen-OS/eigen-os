# ADR 0027: Phase-9A Policy Engine v2 Contract

- **Status**: Accepted
- **Date**: 2026-05-19
- **Decision owners**: Architecture/Governance, Runtime/Core, Security
- **Supersedes / Related**: RFC 0041, ADR 0013, ADR 0018

## Context

Policy behavior across scheduler and plugin-runtime surfaces must be deterministic, auditable, and versioned.

## Decision

Adopt RFC 0041 as the operational contract baseline:

1. Policy bundles are immutable, signed, and semver-versioned.
2. Evaluation decisions must include deterministic `reason_code` and `policy_revision`.
3. Missing/invalid bundles fail closed.

## Consequences

- Authorization outcomes become reproducible across runtime components.
- Breaking policy schema changes require MAJOR version + migration notes.
