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
- [0008 — Phase-3 benchmark run lifecycle core v1](0008-phase3-benchmark-run-lifecycle-core-v1.md)
- [0009 — Phase-3 dataset ingestion contract v1](0009-phase3-dataset-ingestion-contract-v1.md)
- [0010 — Phase-3 comparison methodology and history contract v1](0010-phase3-compare-history-contract-v1.md)
- [0011 — Phase-4 backend selection scoring contract v1](0011-phase4-backend-selection-scoring-contract-v1.md)
- [0012 — Phase-4 explainability API contract v1](0012-phase4-explainability-api-contract-v1.md)
- [0013 — Phase-4 scheduling policy engine contract v1](0013-phase4-scheduling-policy-engine-contract-v1.md)
- [0014 — Phase-5 cluster runtime control-plane contract v1](0014-phase5-cluster-runtime-control-plane-contract-v1.md)
- [0015 — Phase-5 distributed queue and delivery semantics v1](0015-phase5-distributed-queue-and-delivery-semantics-v1.md)
- [0016 — Phase-5 distributed tracing and execution topology contract v1](0016-phase5-distributed-tracing-and-execution-topology-contract-v1.md)

## Phase-3 status

- As of 2026-04-27, implemented Phase-3 RFCs are fully synchronized with ADRs (ADR 0008/0009/0010).
- Required coverage check: [`../development/phase-3-rfc-adr-gap-analysis.md`](../development/phase-3-rfc-adr-gap-analysis.md).
- Phase-3 release package: [`../development/phase-3-release-readiness-checklist.md`](../development/phase-3-release-readiness-checklist.md), [`../development/phase-3-compatibility-report.md`](../development/phase-3-compatibility-report.md).
- Policy reminder: once any Phase-3 RFC is implemented, its normative decisions must be mirrored in one or more ADRs before release closure.

## Phase-4 status

- As of 2026-04-28, implemented Phase-4 RFCs are synchronized with ADRs (ADR 0011/0012/0013).
- Required coverage check: [`../development/phase-4-rfc-adr-gap-analysis.md`](../development/phase-4-rfc-adr-gap-analysis.md).
- Phase-4 release package: [`../development/phase-4-release-readiness-checklist.md`](../development/phase-4-release-readiness-checklist.md), [`../development/phase-4-compatibility-report.md`](../development/phase-4-compatibility-report.md).
- Policy reminder: when a Phase-4 RFC is marked `Implemented`, corresponding ADR record(s) must be synchronized before release closure.

## Phase-5 status

- As of 2026-04-28, implemented Phase-5 RFCs are synchronized with ADRs (ADR 0014/0015/0016).
- Required coverage check: [`../development/phase-5-rfc-adr-gap-analysis.md`](../development/phase-5-rfc-adr-gap-analysis.md).
- Phase-5 release package: [`../development/phase-5-release-readiness-checklist.md`](../development/phase-5-release-readiness-checklist.md), [`../development/phase-5-compatibility-report.md`](../development/phase-5-compatibility-report.md).
- Policy reminder: when a Phase-5 RFC is marked `Implemented`, corresponding ADR record(s) must be synchronized before release closure.
