# Architectural Decisions (Design Decisions)

This page is a **table of contents for decisions**. Details are recorded in **ADRs** (`docs/adr/`) and **Reference** (`docs/reference/`).

## MVP Decisions (contractual)
- **API Contracts**: see `docs/reference/api/grpc-public.md` and `docs/reference/api/grpc-internal.md`.

- **User Source (Eigen‑Lang)**: `docs/reference/eigen-lang-submission.md`.

- **Error Model**: `docs/reference/error-model.md` + `docs/reference/error-mapping.md`.

- **Observability**: trace context propagation (`traceparent`) + metrics `/metrics` (see `howto/run-observability.md`).

## Decision Log (ADR)
- `docs/adr/0001-record-architecture-decisions.md` — ADR process and template.

Current baseline is tracked by existing ADRs in `docs/adr/`; additional ADRs are created only when corresponding code/contract changes are approved.