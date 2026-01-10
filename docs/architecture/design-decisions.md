# Architectural Decisions (Design Decisions)

This page is a **table of contents for decisions**. Details are recorded in **ADRs** (`docs/adr/`) and **Reference** (`docs/reference/`).

## MVP Decisions (contractual)
- **API Contracts**: see `docs/reference/api/grpc-public.md` and `docs/reference/api/grpc-internal.md`.

- **User Source (Eigen‑Lang)**: `docs/reference/eigen-lang-submission.md`.

- **Error Model**: `docs/reference/error-model.md` + `docs/reference/error-mapping.md`.

- **Observability**: trace context propagation (`traceparent`) + metrics `/metrics` (see `howto/run-observability.md`).

## Decision Log (ADR)
- `docs/adr/0001-record-architecture-decisions.md` — ADR process and template.

TODO: add ADR for each "major" decision: public API surface, compilation model (AST‑only), QFS layout, error model, streaming semantics.