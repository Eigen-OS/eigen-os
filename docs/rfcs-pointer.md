# RFCs and ADRs

## Purpose

- `rfcs/` stores proposals, rationale, and evolution history.
- `docs/adr/` stores accepted architectural decisions that are operationally binding.

## Current policy

- RFC status `Implemented` requires a synchronized ADR record.
- ADRs are the primary entry point for implementation teams.
- RFCs remain the canonical history of alternatives and discussion context.

## MVP-2 RFC set (implemented)

- [RFC 0013 — MVP-2 JobSpec Parser and Submit Contract](../rfcs/0013-mvp2-jobspec-parser-submit-contract.md)
- [RFC 0014 — MVP-2 Eigen-Lang AST Safety and Deterministic AQO](../rfcs/0014-mvp2-eigen-lang-ast-safety-deterministic-aqo.md)
- [RFC 0015 — MVP-2 Conformance Fixtures and CI Gates](../rfcs/0015-mvp2-conformance-and-ci-gates.md)

## Phase 1 RFC set (draft)

- [RFC 0019 — Phase 1 Production Runtime Plan](../rfcs/0019-phase1-production-runtime-plan.md)

## MVP-3 RFC set (accepted)

- [RFC 0016 — MVP-3 Kernel Runtime and Driver Execution Contract](../rfcs/0016-mvp3-kernel-driver-execution-contract.md)
- [RFC 0017 — MVP-3 Results Persistence, Retrieval, and CLI Runtime UX](../rfcs/0017-mvp3-results-retrieval-and-cli-runtime-ux.md)
- [RFC 0018 — MVP-3 Runtime Observability and Release Gates](../rfcs/0018-mvp3-runtime-observability-and-release-gates.md)
- Post-MVP roadmap: [development/post-mvp-open-source-roadmap.md](development/post-mvp-open-source-roadmap.md)
- ADR package: [docs/adr/0007-mvp3-release-readiness-runtime-contracts-and-security-closure.md](adr/0007-mvp3-release-readiness-runtime-contracts-and-security-closure.md)

## Phase-3 RFC set (implemented)

- Status on 2026-04-27: required Phase-3 contract RFC package is merged and synchronized with ADRs.
- Coverage check: [development/phase-3-rfc-adr-gap-analysis.md](development/phase-3-rfc-adr-gap-analysis.md)
- Implemented RFCs:
  - [RFC 0020 — Phase-3 Benchmark Run Lifecycle Contract v1](../rfcs/0020-phase3-benchmark-run-lifecycle-contract-v1.md)
- [RFC 0021 — Phase-3 Dataset Ingestion Contract v1](../rfcs/0021-phase3-dataset-ingestion-contract-v1.md)
  - [RFC 0022 — Phase-3 Comparison Methodology and History Contract v1](../rfcs/0022-phase3-compare-history-contract-v1.md)
  - Synchronized ADRs:
  - [ADR 0008 — Phase-3 benchmark run lifecycle core v1](adr/0008-phase3-benchmark-run-lifecycle-core-v1.md)
  - [ADR 0009 — Phase-3 dataset ingestion contract v1](adr/0009-phase3-dataset-ingestion-contract-v1.md)
  - [ADR 0010 — Phase-3 comparison methodology and history contract v1](adr/0010-phase3-compare-history-contract-v1.md)

## Phase-4 RFC set (implemented)

- Status on 2026-04-28: required Phase-4 contract RFC package is implemented and synchronized with ADRs.
- Coverage check: [development/phase-4-rfc-adr-gap-analysis.md](development/phase-4-rfc-adr-gap-analysis.md)
- Implemented RFCs:
  - [RFC 0023 — Phase-4 backend selection scoring contract v1](../rfcs/0023-phase4-backend-selection-scoring-contract-v1.md)
  - [RFC 0024 — Phase-4 explainability API contract v1](../rfcs/0024-phase4-explainability-api-contract-v1.md)
  - [RFC 0025 — Phase-4 scheduling policy engine contract v1](../rfcs/0025-phase4-scheduling-policy-engine-contract-v1.md)
- Synchronized ADRs:
  - [ADR 0011 — Phase-4 backend selection scoring contract v1](adr/0011-phase4-backend-selection-scoring-contract-v1.md)
  - [ADR 0012 — Phase-4 explainability API contract v1](adr/0012-phase4-explainability-api-contract-v1.md)
  - [ADR 0013 — Phase-4 scheduling policy engine contract v1](adr/0013-phase4-scheduling-policy-engine-contract-v1.md)
- Release package:
  - [development/phase-4-release-readiness-checklist.md](development/phase-4-release-readiness-checklist.md)
  - [development/phase-4-compatibility-report.md](development/phase-4-compatibility-report.md)

## Phase-5 RFC set (implemented)

- Status on 2026-04-28: required Phase-5 distributed contract RFC package is implemented and synchronized with ADRs.
- Coverage check: [development/phase-5-rfc-adr-gap-analysis.md](development/phase-5-rfc-adr-gap-analysis.md)
- Implemented RFCs:
  - [RFC 0026 — Phase-5 cluster runtime control-plane contract v1](../rfcs/0026-phase5-cluster-runtime-control-plane-contract-v1.md)
  - [RFC 0027 — Phase-5 distributed queue and delivery semantics v1](../rfcs/0027-phase5-distributed-queue-and-delivery-semantics-v1.md)
  - [RFC 0028 — Phase-5 distributed tracing and execution topology contract v1](../rfcs/0028-phase5-distributed-tracing-and-execution-topology-contract-v1.md)
  - Synchronized ADRs:
  - [ADR 0014 — Phase-5 cluster runtime control-plane contract v1](adr/0014-phase5-cluster-runtime-control-plane-contract-v1.md)
  - [ADR 0015 — Phase-5 distributed queue and delivery semantics v1](adr/0015-phase5-distributed-queue-and-delivery-semantics-v1.md)
  - [ADR 0016 — Phase-5 distributed tracing and execution topology contract v1](adr/0016-phase5-distributed-tracing-and-execution-topology-contract-v1.md)
- Release package:
  - [development/phase-5-release-readiness-checklist.md](development/phase-5-release-readiness-checklist.md)
  - [development/phase-5-compatibility-report.md](development/phase-5-compatibility-report.md)

## Phase-6 RFC set (draft)

- Status on 2026-04-28: Phase-6 plugin ecosystem planning package is prepared; RFCs are in Draft and pending acceptance.
- Coverage check: [development/phase-6-rfc-adr-gap-analysis.md](development/phase-6-rfc-adr-gap-analysis.md)
- Accepted RFCs:
  - [RFC 0029 — Phase-6 plugin SDK and manifest contract v1](../rfcs/0029-phase6-plugin-sdk-and-manifest-contract-v1.md)
  - [RFC 0030 — Phase-6 plugin lifecycle and runtime isolation contract v1](../rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md)
  - [RFC 0031 — Phase-6 plugin compatibility and trust policy contract v1](../rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md)
- ADR sync status:
  - Pending until Phase-6 RFCs move to Accepted/Implemented.

## Phase-7 RFC set (accepted)

- Status on 2026-04-29: required Phase-7 RFC package is accepted and indexed with synchronized ADRs for implementation checkpoint closure.
- Coverage check: [development/phase-7-rfc-adr-gap-analysis.md](development/phase-7-rfc-adr-gap-analysis.md)
- Accepted RFCs:
  - [RFC 0032 — Phase-7 API and contract versioning policy v1](../rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md)
  - [RFC 0033 — Phase-7 developer experience and conformance toolchain baseline v1](../rfcs/0033-phase7-developer-experience-and-conformance-toolchain-baseline-v1.md)
- Synchronized ADRs:
  - [ADR 0018 — Phase-7 API and contract versioning policy v1](adr/0018-phase7-api-and-contract-versioning-policy-v1.md)
  - [ADR 0019 — Phase-7 developer experience and conformance toolchain baseline v1](adr/0019-phase7-developer-experience-and-conformance-toolchain-baseline-v1.md)
- Release closure artifacts:
  - [development/phase-7-release-readiness-checklist.md](development/phase-7-release-readiness-checklist.md)
  - [development/phase-7-compatibility-report.md](development/phase-7-compatibility-report.md)

## Phase-8A RFC set (accepted)

- Status on 2026-05-16: required Phase-8A contract RFC package is accepted for implementation kickoff.
- Implemented/accepted RFCs:
  - [RFC 0034 — Phase-8A Knowledge Base API contract v1](../rfcs/0034-phase8a-knowledge-base-api-contract-v1.md)
  - [RFC 0035 — Phase-8A GNN optimizer service contract v1](../rfcs/0035-phase8a-gnn-optimizer-service-contract-v1.md)
  - [RFC 0036 — Phase-8A Continuous learning control plane contract v1](../rfcs/0036-phase8a-continuous-learning-control-plane-contract-v1.md)
  - [RFC 0037 — Phase-8A QFS-L2 checkpoint envelope contract v1](../rfcs/0037-phase8a-qfs-l2-checkpoint-envelope-contract-v1.md)
- Execution binding:
  - [development/phase-8a-execution-plan.md](development/phase-8a-execution-plan.md)
- Synchronized ADRs:
  - [ADR 0020 — Phase-8A Knowledge Base API contract v1](adr/0020-phase8a-knowledge-base-api-contract-v1.md)
  - [ADR 0021 — Phase-8A GNN optimizer service contract v1](adr/0021-phase8a-gnn-optimizer-service-contract-v1.md)
  - [ADR 0022 — Phase-8A Continuous learning control plane contract v1](adr/0022-phase8a-continuous-learning-control-plane-contract-v1.md)
  - [ADR 0023 — Phase-8A QFS-L2 checkpoint envelope contract v1](adr/0023-phase8a-qfs-l2-checkpoint-envelope-contract-v1.md)
- Release closure artifacts:
  - [development/phase-8a-rfc-adr-gap-analysis.md](development/phase-8a-rfc-adr-gap-analysis.md)
  - [development/phase-8a-release-readiness-checklist.md](development/phase-8a-release-readiness-checklist.md)
  - [development/phase-8a-compatibility-report.md](development/phase-8a-compatibility-report.md)

## Phase-8B RFC set (accepted)

- Status on 2026-05-17: required Phase-8B runtime/data hardening RFC package is accepted and synchronized with ADRs for milestone closure.
- Coverage check: [development/phase-8b/phase-8b-rfc-adr-gap-analysis.md](development/phase-8b/phase-8b-rfc-adr-gap-analysis.md)
- Accepted RFCs:
  - [RFC 0038 — Phase-8B QRTX scheduling and lifecycle hardening contract v1](../rfcs/0038-phase8b-qrtx-scheduling-and-lifecycle-hardening-contract-v1.md)
  - [RFC 0039 — Phase-8B QFS-L2/L3 data fabric hardening contract v1](../rfcs/0039-phase8b-qfs-l2-l3-data-fabric-hardening-contract-v1.md)
  - [RFC 0040 — Phase-8B runtime/data observability and SLO gates contract v1](../rfcs/0040-phase8b-runtime-data-observability-and-slo-gates-v1.md)
- Synchronized ADRs:
  - [ADR 0024 — Phase-8B QRTX scheduling and lifecycle hardening contract v1](adr/0024-phase8b-qrtx-scheduling-and-lifecycle-hardening-contract-v1.md)
  - [ADR 0025 — Phase-8B QFS-L2/L3 data fabric hardening contract v1](adr/0025-phase8b-qfs-l2-l3-data-fabric-hardening-contract-v1.md)
  - [ADR 0026 — Phase-8B runtime/data observability and SLO gates contract v1](adr/0026-phase8b-runtime-data-observability-and-slo-gates-v1.md)
- Release closure artifacts:
  - [development/phase-8b/phase-8b-release-readiness-checklist.md](development/phase-8b/phase-8b-release-readiness-checklist.md)
  - [development/phase-8b/phase-8b-compatibility-report.md](development/phase-8b/phase-8b-compatibility-report.md)
  - [development/phase-8b/phase-8b-exit-evidence-bundle.md](development/phase-8b/phase-8b-exit-evidence-bundle.md)

## Quick links

- RFC directory: [`../rfcs/`](../rfcs/)
- ADR index: [`adr/README.md`](adr/README.md)
- MVP-2 execution plan: [`development/mvp-2-compilation-pipeline.md`](development/mvp-2-compilation-pipeline.md)
