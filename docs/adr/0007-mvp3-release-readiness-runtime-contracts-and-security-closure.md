# ADR 0007 — MVP-3 release readiness, runtime contracts, and security closure

- **Status**: Accepted
- **Date**: 2026-04-25
- **Deciders**: Eigen OS maintainers
- **Supersedes / Related**: RFC 0016, RFC 0017, RFC 0018, ADR 0006

## Context

MVP-2 closed deterministic submission and compilation contracts. MVP-3 introduces runtime execution, terminal-state ownership, result retrieval semantics, and release-critical observability gates across `system-api -> kernel -> driver-manager`.

To ship MVP-3, we must formally accept the runtime RFC package, synchronize operator documentation, and record a final security audit of the kernel-driver execution boundary.

## Decision

1. Accept RFC 0016, RFC 0017, and RFC 0018 as operational architecture contracts for MVP-3.
2. Freeze the runtime lifecycle contract: `PENDING -> COMPILING -> RUNNING -> DONE|ERROR|CANCELLED|TIMEOUT` with idempotent terminalization.
3. Freeze CLI runtime command semantics for `status`, `watch`, and `results`, including terminal exits and diagnostics expectations.
4. Require runtime smoke + observability checks as release-blocking gates.
5. Close MVP-3 release readiness only after security audit completion for kernel-driver boundary controls.

## Consequences

### Positive

- Runtime behavior is deterministic and auditable for maintainers and API consumers.
- CLI and docs stay aligned with contract semantics for onboarding and troubleshooting.
- Release readiness has explicit evidence bundle (RFC acceptance + tracking checklist + security audit).

### Trade-offs

- Contract updates now require deliberate RFC/ADR churn rather than implicit implementation drift.
- CI remains strict on runtime/telemetry gates, which can increase PR feedback time.

## Evidence package

- Accepted RFCs:
  - `rfcs/0016-mvp3-kernel-driver-execution-contract.md`
  - `rfcs/0017-mvp3-results-retrieval-and-cli-runtime-ux.md`
  - `rfcs/0018-mvp3-runtime-observability-and-release-gates.md`
- Tracking closure:
  - `docs/development/mvp-3-execution-and-results.md`
- Security audit:

## Rollout / governance

- ADR 0007 is the normative reference for MVP-3 release closure.
- Future changes to runtime lifecycle or CLI terminal semantics must start with a new RFC and update this ADR chain.
