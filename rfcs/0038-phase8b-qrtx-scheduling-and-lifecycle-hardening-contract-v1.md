# RFC 0038: Phase-8B QRTX Scheduling and Lifecycle Hardening Contract v1

- **Status:** Accepted
- **Date:** 2026-05-17
- **Authors:** Runtime/Core
- **Phase:** 8B

## Summary
Defines the Phase-8B v1 contract for deterministic QRTX scheduling behavior, DAG dependency resolution, policy hooks, and idempotent lifecycle transitions.

## Motivation
Phase-8B requires production-grade scheduler behavior under research-scale load with replay-safe transitions and deterministic diagnostics.

## Proposal
1. Standardize DAG resolution semantics and reason codes.
2. Define priority/quota policy contract with deterministic tie-breakers.
3. Define topology/noise-aware dispatch hooks and fallback behavior.
4. Define lifecycle transition invariants for submit/schedule/dispatch/retry/cancel.
5. Add required fixture tests and CI fail-closed drift gates.

## Backward compatibility
- Additive changes use `MINOR`.
- Breaking transition semantics or reason-code behavior require `MAJOR` + migration notes.

## Acceptance
- Fixtures cover deterministic DAG/lifecycle behavior.
- CI enforces contract drift detection and migration-note policy.
