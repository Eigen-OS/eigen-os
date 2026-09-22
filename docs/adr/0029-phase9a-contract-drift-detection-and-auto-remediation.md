# ADR 0029: Phase-9A Contract Drift Detection and Auto-Remediation Baseline

- **Status**: Accepted
- **Date**: 2026-05-19
- **Decision owners**: QA/CI, Architecture/Governance, Developer Experience
- **Supersedes / Related**: RFC 0043, ADR 0019, ADR 0026

## Context

Contract drift across APIs, schemas, and observability surfaces must be detected before release closure.

## Decision

Adopt RFC 0043 as the baseline:

1. Pre-merge and pre-release gates must run drift classification.
2. Breaking drift without migration notes fails closed.
3. Remediation artifacts are required release evidence.

## Consequences

- Drift regressions are surfaced earlier with deterministic ownership and reason codes.
- SemVer discipline is reinforced with automation.
