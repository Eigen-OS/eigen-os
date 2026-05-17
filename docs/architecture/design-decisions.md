# Architectural Decisions (Design Decisions)

This page is a **table of contents for decisions**. Details are recorded in **ADRs** (`docs/adr/`) and **Reference** (`docs/reference/`).

## MVP Decisions (contractual)
- **API Contracts**: see `docs/reference/api/grpc-public.md` and `docs/reference/api/grpc-internal.md`.

- **User Source (Eigen‑Lang)**: `docs/reference/eigen-lang-submission.md`.

- **Error Model**: `docs/reference/error-model.md` + `docs/reference/error-mapping.md`.

- **Observability**: trace context propagation (`traceparent`) + metrics `/metrics` (see `howto/run-observability.md`).

## Decision Log (ADR)
- `docs/adr/0001-record-architecture-decisions.md` — ADR process and template.
- `docs/adr/0018-phase7-api-and-contract-versioning-policy-v1.md` — SemVer, deprecation windows, migration notes, and contract-drift policy.
- `docs/adr/0019-phase7-developer-experience-and-conformance-toolchain-baseline-v1.md` — developer tooling and conformance gate baseline.
- `docs/adr/0020-phase8a-knowledge-base-api-contract-v1.md` through `docs/adr/0023-phase8a-qfs-l2-checkpoint-envelope-contract-v1.md` — Phase-8A knowledge, optimizer, learning-control, and checkpoint envelope decisions.
- `docs/adr/0024-phase8b-qrtx-scheduling-and-lifecycle-hardening-contract-v1.md` — deterministic QRTX DAG, scheduling policy, and lifecycle hardening.
- `docs/adr/0025-phase8b-qfs-l2-l3-data-fabric-hardening-contract-v1.md` — QFS-L2/L3 artifact, retention, indexing, checkpoint/restore integrity hardening.
- `docs/adr/0026-phase8b-runtime-data-observability-and-slo-gates-v1.md` — runtime/data telemetry correlation, alert packs, and Phase-8B SLO gate evidence.

Current baseline is tracked by existing ADRs in `docs/adr/`; additional ADRs are created only when corresponding code/contract changes are approved.
