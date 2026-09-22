# ADR 0002: MVP-1 contract baseline (derived from implemented RFCs)

- **Status:** Accepted
- **Date:** 2026-04-24
- **Deciders:** Core architecture maintainers

## Context

MVP-1 (Core Services Setup) is complete. Implemented RFCs define service boundaries and contracts, but a concise baseline decision was missing in ADR form.

## Decision

Eigen OS freezes the following MVP-1 baseline decisions:

1. **Public boundary:** public gRPC surface is `JobService` and `DeviceService` for MVP.
2. **Job contract:** `job.yaml` (JobSpec v0.1) is canonical user job descriptor.
3. **Compilation IR:** AQO v0.1 is the canonical compiler output artifact.
4. **Execution boundary:** Kernel/QRTX orchestrates lifecycle stages and delegates execution via Driver Manager.
5. **Driver boundary:** QDriver API v0.1 is required for simulator and plugin drivers.
6. **CLI baseline:** MVP CLI commands and packaging rules are fixed (`submit/status/result/compile/visualize`).
7. **Observability and security minimums:** trace propagation, metrics exposure, structured logging, and boundary auth validation are mandatory for MVP.
8. **Language submission model:** Eigen-Lang source submission is AST-only and non-executing.

## Implemented RFC sources

- RFC 0003 — JobSpec v0.1 (`rfcs/0003-JobSpec-eigen-cli-v0.1.md`)
- RFC 0004 — Public gRPC API v0.1 (`rfcs/0004-public-gRPC-API-v0.1.md`)
- RFC 0005 — AQO format v0.1 (`rfcs/0005-aqo-format-v0.1.md`)
- RFC 0006 — QDriver API v0.1 (`rfcs/0006-qdriver-api-v0.1.md`)
- RFC 0007 — QRTX MVP (`rfcs/0007-qrtx-mvp.md`)
- RFC 0008 — Observability MVP (`rfcs/0008-observability-mvp.md`)
- RFC 0009 — Security & Isolation MVP (`rfcs/0009-security-isolation-mvp.md`)
- RFC 0010 — eigen-cli MVP (`rfcs/0010-eigen-cli-mvp.md`)
- RFC 0011 — Eigen-Lang submission format v0.1 (`rfcs/0011-eigen-lang-submission-v0.1.md`)
- RFC 0012 — Eigen-Lang v0.1 (`rfcs/0012-eigen-lang-v0.1.md`)

## Consequences

- MVP-1 implementation and maintenance must stay compatible with this baseline.
- Contract-breaking changes require a new RFC + ADR update path.
- MVP-2 work must extend this baseline additively.