# ADR 0028: Phase-9A Federated Identity and Workload Attestation Contract

- **Status**: Accepted
- **Date**: 2026-05-19
- **Decision owners**: Security, Runtime/Core, Platform
- **Supersedes / Related**: RFC 0042, RFC 0031, RFC 0038

## Context

Phase-9A requires portable trust guarantees for multi-cluster execution and policy enforcement.

## Decision

Adopt RFC 0042 as the baseline contract:

1. Workload identity must be represented as signed attestation envelopes.
2. Dispatch requires successful attestation verification.
3. Trust tier and reason code must be available to policy evaluation and audit logs.

## Consequences

- Stale, tampered, or unverifiable workloads are denied deterministically.
- Runtime trust posture becomes observable and enforceable in CI/release gates.
