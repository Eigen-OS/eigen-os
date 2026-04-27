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

## Quick links

- RFC directory: [`../rfcs/`](../rfcs/)
- ADR index: [`adr/README.md`](adr/README.md)
- MVP-2 execution plan: [`development/mvp-2-compilation-pipeline.md`](development/mvp-2-compilation-pipeline.md)
