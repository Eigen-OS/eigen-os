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
- [0017 — Phase-6 plugin contract RFC package acceptance baseline](0017-phase6-plugin-contract-rfc-package-acceptance.md)
- [0018 — Phase-7 API and contract versioning policy v1](0018-phase7-api-and-contract-versioning-policy-v1.md)
- [0019 — Phase-7 developer experience and conformance toolchain baseline v1](0019-phase7-developer-experience-and-conformance-toolchain-baseline-v1.md)
- [0020 — Phase-8A Knowledge Base API contract v1](0020-phase8a-knowledge-base-api-contract-v1.md)
- [0021 — Phase-8A GNN optimizer service contract v1](0021-phase8a-gnn-optimizer-service-contract-v1.md)
- [0022 — Phase-8A Continuous learning control plane contract v1](0022-phase8a-continuous-learning-control-plane-contract-v1.md)
- [0023 — Phase-8A QFS-L2 checkpoint envelope contract v1](0023-phase8a-qfs-l2-checkpoint-envelope-contract-v1.md)
- [0024 — Phase-8B QRTX scheduling and lifecycle hardening contract v1](0024-phase8b-qrtx-scheduling-and-lifecycle-hardening-contract-v1.md)
- [0025 — Phase-8B QFS-L2/L3 data fabric hardening contract v1](0025-phase8b-qfs-l2-l3-data-fabric-hardening-contract-v1.md)
- [0026 — Phase-8B runtime/data observability and SLO gates contract v1](0026-phase8b-runtime-data-observability-and-slo-gates-v1.md)
- [0027 — Phase-9A Policy Engine v2 Contract](0027-phase9a-policy-engine-v2-contract.md)
- [0028 — Phase-9A Federated Identity and Workload Attestation Contract](0028-phase9a-federated-identity-and-workload-attestation.md)
- [0029 — Phase-9A Contract Drift Detection and Auto-Remediation Baseline](0029-phase9a-contract-drift-detection-and-auto-remediation.md)
- [0030 — Phase-8D QDriver API v1 final contract and conformance semantics](0030-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md)
- [0031 — Phase-8D provider driver matrix contract and tolerance profiles](0031-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md)
- [0032 — Phase-8D externalization surfaces contract v1](0032-phase8d-externalization-surfaces-contract-v1.md)
- [0033 — Phase-9B intelligence closure contract v1](0033-phase9b-intelligence-closure-contract-v1.md)

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

## Phase-6 status

- As of 2026-04-29, required Phase-6 plugin contract RFC package is accepted and indexed (RFC 0029/0030/0031; ADR 0017 governance baseline).
- Required coverage check: [`../development/phase-6-rfc-adr-gap-analysis.md`](../development/phase-6-rfc-adr-gap-analysis.md).
- Phase-6 planning package: [`../development/phase-6-plugin-ecosystem.md`](../development/phase-6-plugin-ecosystem.md), [`../development/phase-6-issue-pack.md`](../development/phase-6-issue-pack.md).
- Policy reminder: as Phase-6 RFCs move to `Implemented`, normative outcomes must be synchronized into ADRs before release closure.

## Phase-7 status

- As of 2026-04-29, required Phase-7 RFC package is accepted and synchronized with ADRs (ADR 0018/0019).
- Required coverage check: [`../development/phase-7-rfc-adr-gap-analysis.md`](../development/phase-7-rfc-adr-gap-analysis.md).
- Phase-7 closure package: [`../development/phase-7-release-readiness-checklist.md`](../development/phase-7-release-readiness-checklist.md), [`../development/phase-7-compatibility-report.md`](../development/phase-7-compatibility-report.md).
- Policy reminder: when Phase-7 contracts evolve, SemVer policy and migration-note gates from RFC 0032/0033 remain mandatory.

## Phase-8A status

- As of 2026-05-16, required Phase-8A RFC package is accepted and synchronized with ADRs (ADR 0020/0021/0022/0023).
- Required coverage check: [`../development/phase-8a-rfc-adr-gap-analysis.md`](../development/phase-8a-rfc-adr-gap-analysis.md).
- Phase-8A closure package: [`../development/phase-8a-release-readiness-checklist.md`](../development/phase-8a-release-readiness-checklist.md), [`../development/phase-8a-compatibility-report.md`](../development/phase-8a-compatibility-report.md).
- Policy reminder: breaking contract changes require MAJOR + migration notes; deprecation support window remains 2 minors or 90 days, whichever is longer.

## Phase-8B status

- As of 2026-05-17, accepted Phase-8B RFCs are synchronized with ADRs (ADR 0024/0025/0026).
- Required coverage check: [`../development/phase-8b/phase-8b-rfc-adr-gap-analysis.md`](../development/phase-8b/phase-8b-rfc-adr-gap-analysis.md).
- Phase-8B release package: [`../development/phase-8b/phase-8b-release-readiness-checklist.md`](../development/phase-8b/phase-8b-release-readiness-checklist.md), [`../development/phase-8b/phase-8b-compatibility-report.md`](../development/phase-8b/phase-8b-compatibility-report.md), [`../development/phase-8b/phase-8b-exit-evidence-bundle.md`](../development/phase-8b/phase-8b-exit-evidence-bundle.md).
- Policy reminder: Phase-8B runtime/data contract changes must preserve deterministic reason codes, CI gate evidence, and SemVer/migration-note discipline.

## Phase-8C status

- As of 2026-05-19, Phase-8C closure package is synchronized with accepted RFC/ADR baselines (RFC 0035/0036/0040 ↔ ADR 0021/0022/0026).
- Required coverage check: [`../development/phase-8c/phase-8c-rfc-adr-gap-analysis.md`](../development/phase-8c/phase-8c-rfc-adr-gap-analysis.md).
- Phase-8C release package: [`../development/phase-8c/phase-8c-release-readiness-checklist.md`](../development/phase-8c/phase-8c-release-readiness-checklist.md), [`../development/phase-8c/phase-8c-compatibility-report.md`](../development/phase-8c/phase-8c-compatibility-report.md), [`../development/phase-8c/phase-8c-exit-evidence-bundle.md`](../development/phase-8c/phase-8c-exit-evidence-bundle.md).
- Policy reminder: Phase-8C governance updates are documentation-only unless contract artifacts change; SemVer and migration-note gates remain mandatory for any future contract deltas.

## Phase-8D status

- As of 2026-05-19, required Phase-8D RFC package is accepted and synchronized with ADRs (ADR 0030/0031/0032).
- Required coverage check: [`../development/phase-8d/phase-8d-rfc-adr-gap-analysis.md`](../development/phase-8d/phase-8d-rfc-adr-gap-analysis.md).
- Phase-8D release package: [`../development/phase-8d/phase-8d-release-readiness-checklist.md`](../development/phase-8d/phase-8d-release-readiness-checklist.md), [`../development/phase-8d/phase-8d-compatibility-report.md`](../development/phase-8d/phase-8d-compatibility-report.md), [`../development/phase-8d/phase-8d-exit-evidence-bundle.md`](../development/phase-8d/phase-8d-exit-evidence-bundle.md).
- Policy reminder: breaking behavior requires MAJOR and migration notes; deprecations follow 2-minor-or-90-day policy.

## Phase-9A status

- As of 2026-05-19, required Phase-9A RFC package is accepted and synchronized with ADRs (ADR 0027/0028/0029).
- Policy reminder: Phase-9A contract changes require deterministic reason codes, SemVer discipline, and migration-note evidence for breaking changes.

## Phase-9B status

- As of 2026-05-20, required Phase-9B RFC package is synchronized with ADRs (ADR 0033).
- Required coverage check: [`../development/phase-9b/phase-9b-rfc-adr-gap-analysis.md`](../development/phase-9b/phase-9b-rfc-adr-gap-analysis.md).
- Phase-9B release package: [`../development/phase-9b/phase-9b-release-readiness-checklist.md`](../development/phase-9b/phase-9b-release-readiness-checklist.md), [`../development/phase-9b/phase-9b-compatibility-report.md`](../development/phase-9b/phase-9b-compatibility-report.md), [`../development/phase-9b/phase-9b-exit-evidence-bundle.md`](../development/phase-9b/phase-9b-exit-evidence-bundle.md).
- Policy reminder: CI must fail closed on undocumented contract drift and conformance regressions; deprecations retain support for 2 minors or 90 days, whichever is longer.
