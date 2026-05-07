# Component documentation audit (2026-05-07)

## Scope checked
- Architecture component docs in `docs/architecture/components/*.md`.
- Service/component README files under:
  - `src/services/*/README.md`
  - `src/rust/crates/*/README.md`

## Unified compatibility matrix

| Component | Architecture doc status vs code | Key drift | Decision needed | Priority |
|---|---|---|---|---|
| System API | **Partial mismatch** | Component page describes production-grade REST/auth stack as current state; service README describes MVP gRPC skeleton + basic auth modes. | Split into **Implemented (MVP)** vs **Target** sections. | P0 |
| Eigen Compiler | **Mismatch** | Component page claims rich frontend subsystems as implemented; README describes current AST safety baseline and limits. | Rewrite page to contract-first implemented scope, move advanced internals to roadmap. | P0 |
| Driver Manager | **Partial mismatch** | Component page states resilience/pooling/failover as if implemented; README lists skeleton + registry + health/metrics only. | Mark advanced features as future tense and tie to phase milestones. | P1 |
| Resource Manager | **Strong mismatch** | Architecture page says MVP embedded in kernel; crate README presents standalone advanced service architecture. | Choose single canonical MVP truth and align both docs. | P0 |
| QFS | **Strong mismatch** | Architecture page says MVP CircuitFS subset; crate README describes full 3-level QFS with state/live qubit manager as if available. | Keep MVP subset as implemented; move level-1/2 text to roadmap/future section. | P0 |
| QRTX | **Mostly aligned** | Architecture page says linear MVP pipeline and no full DAG; crate README confirms same state machine scope. | Minor editorial sync only. | P2 |
| Security/Isolation | **Strong mismatch** | Architecture page is MVP-baseline oriented; crate README describes advanced module (QKD, ABAC, HSM, full services) as current. | Reframe crate README into MVP-now vs future-security architecture. | P0 |
| Observability | **Strong mismatch** | Architecture page gives broad platform APIs; crate README describes full observability core architecture not present in crate contents/implementation baseline. | Reduce claims to implemented metrics/tracing primitives and separate roadmap features. | P0 |
| Benchmark Service | **Index visibility fixed; semantics not unified** | Component is documented in service README but still not a dedicated architecture component page. | Add dedicated component page or explicitly classify under observability extension. | P1 |

## Detailed findings (added scope: QFS / QRTX / Security / Observability)

### QFS
- `docs/architecture/components/qfs.md` explicitly constrains MVP to CircuitFS only.
- `src/rust/crates/qfs/README.md` describes Level 2/Level 1 capabilities and end-to-end APIs as currently available.
- Result: readers cannot tell what is implemented now vs conceptual design.

### QRTX
- `docs/architecture/components/qrtx.md` and `src/rust/crates/qrtx/README.md` are materially consistent on the MVP state machine.
- Result: no blocking drift; only minor wording cleanup recommended.

### Security / Isolation
- `docs/architecture/components/security-isolation.md` documents pragmatic MVP controls (auth mode, payload limits, compiler restrictions).
- `src/rust/crates/security-module/README.md` presents advanced architecture (QKD, ABAC, HSM flows, dedicated runtime service) as if currently implemented.
- Result: major scope inflation in README compared to MVP reality.

### Observability
- `docs/architecture/components/observability.md` claims dedicated gRPC/REST/WebSocket interfaces and multi-backend event bus as current platform behavior.
- `src/rust/crates/observability/README.md` similarly presents a broad standalone “observability core” with extensive modules.
- Result: architecture and crate docs are mutually reinforcing but likely both ahead of implemented code; must be normalized to “implemented vs planned”.

## Single source-of-truth policy (proposed)
1. For **implemented behavior**, authoritative source = test-backed code contracts + minimal README “Current MVP behavior”.
2. For **planned behavior**, authoritative source = `docs/roadmap.md` + RFC/ADR links.
3. Component docs must contain two explicit headings:
   - `Implemented in this repo (as of <date>)`
   - `Planned / target architecture`

## Action backlog (to execute)
1. Normalize System API, Compiler, Resource Manager, QFS, Security, Observability pages to “implemented vs planned”.
2. Add a dedicated architecture page for Benchmark Service.
3. Add a docs CI drift gate (claim lint) for present-tense MVP statements.
4. Add status badges on component pages: `implemented`, `partial`, `target`.
