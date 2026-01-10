# Eigen OS Documentation

The documentation is organized according to **Diátaxis: Tutorials** (learning), **How‑to** (recipes), **Reference** (contracts), **Explanation** (explanations).
This helps keep contracts (APIs/formats) *in one place* and avoid duplication.

## Getting started (MVP)

### Tutorials
- `tutorials/quickstart-local-sim.md` — set up the stack locally and run a job on the simulator
- `tutorials/first-job-eigen-lang.md` — write `program.eigen.py` + `job.yaml`, submit a job, get results

### Reference (source of truth)
- `reference/jobspec.md` — **JobSpec v0.1** (`job.yaml`)
- `reference/eigen-lang-submission.md` — what a "user source" is and how it is packaged
- `reference/api/grpc-public.md` — public `eigen_api.v1`
- `reference/api/grpc-internal.md` — internal `kernel_api.v1 / compiler_api.v1 / driver_api.v1`
- `reference/error-model.md` — error principles
- `reference/error-mapping.md` — **error mapping matrix** between layers
- `reference/formats/aqo.md` — AQO v0.1
- `reference/formats/qfs-layout.md` — QFS layout (артефакты/results/logs)

### Architecture (overview and diagrams)
- `architecture/overview.md` — architecture overview and boundaries
- `architecture/components.md` — component index
- `architecture/data-flow.md` — end‑to‑end data flows
- `architecture/contract-map.md` — who calls whom and with what (interfaces)
- `architecture/design-decisions.md` — key decisions (links to ADRs)

### Development (delivery control)
- `development/mvp-definition-of-done.md` — DoD for services
- `development/mvp-contract-freeze-checklist.md` — "contract frozen" checklist (RFC 0004/0006/0011)
- `development/repo-layout.md` — repository structure and source‑of‑truth

### Explanation / Product
- `explanation/mission.md` — mission and philosophy
- `explanation/goals.md` — goals and non‑goals
- `roadmap.md` — roadmap

## Components
Details: `architecture/components/`

- `system-api.md`
- `kernel-qrtx.md`
- `compiler.md`
- `driver-manager.md`
- `qfs.md`
- `resource-manager.md`
- `security-isolation.md`
- `observability.md`

## RFC and ADR
- RFC: `rfcs/` (proposals, before acceptance and during implementation)
- ADR: `docs/adr/` (accepted decisions and their consequences)


### Eigen‑Lang
- `reference/eigen-lang/README.md` — Eigen‑Lang language reference (v0.1)
