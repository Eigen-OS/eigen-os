# ADR Index

Architecture Decision Records (ADRs) capture decisions that are already adopted in the codebase.

## Lifecycle policy

- **RFC** = proposal and discussion artifact.
- **ADR** = accepted and operational decision.
- When an RFC reaches **Implemented**, its normative outcome must be mirrored in `docs/adr/`.

## Records

- [0001 — Record architecture decisions and RFC→ADR migration policy](0001-record-architecture-decisions.md)
- [0002 — MVP-1 contract baseline (derived from implemented RFCs)](0002-mvp1-contract-baseline.md)
- [0003 — MVP-2 JobSpec parser contract (JobSpec → SubmitJobRequest)](0003-mvp2-jobspec-parser-contract.md)
- [0004 — MVP-2 Eigen-Lang AST safety and deterministic AQO generation](0004-mvp2-eigen-lang-ast-safety.md)
- [0005 — MVP-2 conformance fixtures and CI gating policy](0005-mvp2-conformance-and-ci-gates.md)
- [0006 — MVP-2 release closure and baseline freeze](0006-mvp2-release-closure-and-baseline-freeze.md)

- [0007 — MVP-3 release readiness, runtime contracts, and security closure](0007-mvp3-release-readiness-runtime-contracts-and-security-closure.md)

## Phase-3 status

- As of 2026-04-27, no Phase-3 benchmarking ADR has been accepted yet.
- Required coverage check: [`../development/phase-3-rfc-adr-gap-analysis.md`](../development/phase-3-rfc-adr-gap-analysis.md).
- Policy reminder: once any Phase-3 RFC is implemented, its normative decisions must be mirrored in one or more ADRs before release closure.
