# Repository layout

> TODO: port from ` `.

This document defines the **recommended repository structure** for the Eigen OS monorepo.

Eigen OS is a polyglot system:

- **Rust** for the performance-critical kernel and CLI
- **Python** for high-level services (System API, Driver Manager, Compiler, DSL runtime)
- **Multi-language SDKs** for external integrations

---

## Guiding principles

1. **Contracts-first**: public APIs are authored in `proto/` and consumed everywhere else.
2. **One deployable per directory**: each service/binary has its own folder, build file(s), and Docker/K8s entry.
3. **Clear boundary between apps and libraries**: shared code lives in `crates/` (Rust) or `libs/` (Python).
4. **Generated code is never the source of truth**: it is produced by `scripts/codegen/` and can be re-built in CI.
5. **Docs live with the code**: architecture, specs, and decisions are versioned together with implementation.
6. **Mirrored tests & examples**: test layout mirrors production code to keep coverage predictable.

---

## Source of truth

| Artifact | Canonical location | Format | Generated outputs | Primary consumers |
|---|---|---|---|---|
| **Proto (API contract)** | `proto/eigen_api/v1/*.proto` | Protocol Buffers | gRPC server & client stubs (Python/Rust/TS), API reference docs | System API, CLI, SDKs, internal services |
| **IR (Compiler Intermediate Representation)** | `specs/ir/` and `src/services/eigen-compiler/` | Markdown + schema (JSON/Proto) | AQO/QASM/native backends; debugging dumps | Compiler, optimizer, kernel execution |
| **JobSpec (Task specification)** | `specs/jobspec/` | YAML/JSON + JSON Schema | validated task payloads; UI/CLI templates | QRTX scheduler, System API, SDKs |
| **RFC / ADR (decision log)** | `rfcs/` (proposals) and `docs/adr/` (accepted decisions) | Markdown | none | All contributors |

**Rule of thumb:** if two sources disagree, *the source-of-truth wins*, and everything else must be regenerated or aligned.

---

## High-level tree (recommended)

```text
eigen-os/
├── .github/                       # GitHub workflows, templates, CODEOWNERS
│
├── rfcs/                          # RFC proposals (numbered, reviewed)
│   ├── TEMPLATE.md
│   └── RFC-0001-...md
│
├── docs/                          # Documentation (MkDocs or similar)
│   ├── README.md
│   ├── mkdocs.yml
│   ├── architecture/              # Architecture overview, components, diagrams
│   ├── adr/                       # Accepted Architecture Decision Records
│   ├── api-reference/             # Human-readable public API reference
│   ├── developer/                 # Contributor docs (build/test/release)
│   ├── user-guides/               # End-user docs
│   ├── spec/                      # Formal specs that complement `specs/`
│   └── diagrams/
│
├── proto/                         # ✅ API source of truth (contract-first)
│   └── eigen_api/v1/
│       ├── service.proto
│       ├── jobs.proto
│       ├── devices.proto
│       ├── compilation.proto
│       ├── monitoring.proto
│       └── auth.proto
│
├── specs/                         # ✅ Non-proto specs (schemas, examples)
│   ├── jobspec/
│   │   ├── schema/                # JSON Schema (validation)
│   │   └── examples/              # Minimal, canonical examples
│   └── ir/
│       ├── schema/
│       └── examples/
│
├── src/
│   ├── rust/                      # Single Cargo workspace for all Rust crates (preferred)
│   │   ├── Cargo.toml
│   │   ├── crates/                # Library crates
│   │   │   ├── qrtx/
│   │   │   ├── resource-manager/
│   │   │   ├── qfs/
│   │   │   ├── security-module/
│   │   │   └── observability/
│   │   └── apps/                  # Binary crates
│   │       ├── cli/
│   │       └── qdal-tools/
│   │
│   └── services/                  # Deployable services (mostly Python)
│       ├── system-api/
│       ├── driver-manager/
│       ├── eigen-lang/
│       └── eigen-compiler/
│
├── client-sdks/                   # Public SDKs (published packages)
│   ├── python/
│   ├── rust/
│   ├── javascript/
│   └── shared/                    # Shared protos + codegen helpers
│
├── tests/                         # Unit, integration, e2e, benchmarks
├── examples/                      # Runnable examples & tutorials
├── config/                        # Default config + profiles + schemas
├── deploy/                        # Docker/K8s/Cloud deployment assets
├── scripts/                       # Build/test/codegen automation
├── tools/                         # Developer tools (linters, local infra helpers)
│
├── README.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── GOVERNANCE.md
└── LICENSE
```

---

## Directory reference

| Path | What belongs here | What must NOT belong here |
|---|---|---|
| `.github/` | CI workflows, issue/PR templates, CODEOWNERS | product code |
| `rfcs/` | proposals for large changes, numbered RFCs | implementation details |
| `docs/` | user + developer docs, ADRs, diagrams | generated artifacts, build outputs |
| `proto/` | API contracts and shared messages | generated stubs |
| `specs/` | JobSpec + IR schemas, canonical examples | runtime code |
| `src/rust/` | all Rust crates in one workspace | Python code |
| `src/services/` | deployable services (Docker targets) | SDK publishing |
| `client-sdks/` | public SDK packages and examples | server implementations |
| `tests/` | unit/integration/e2e/benchmarks | ad-hoc scripts |
| `examples/` | executable demos and tutorials | core libraries |
| `config/` | default configs + profiles + JSON Schema | secrets |
| `deploy/` | docker-compose, K8s, Helm, Terraform | app logic |
| `scripts/` | repeatable automation (build/test/codegen) | manual one-offs |
| `tools/` | developer utilities (local infra, generators) | production code |

---

## Component conventions

### Rust workspace (`src/rust/`)

- Prefer **one** workspace `Cargo.toml` for all Rust crates.
- Put reusable crates into `crates/`.
- Put binaries into `apps/`.
- Each crate should have its own `README.md` describing:
  - responsibility
  - public API
  - integration points

### Python services (`src/services/`)

Each service is an independent Python package:

- `pyproject.toml` (preferred) + lockfile
- `src/<package_name>/...` layout
- `Dockerfile` (and optionally `docker-compose.yml` for local dev)
- `README.md` with:
  - how to run locally
  - env vars
  - health checks

### SDKs (`client-sdks/`)

- SDKs are **public distribution artifacts**; keep them stable and well-documented.
- Shared codegen inputs live under `client-sdks/shared/`.

---

## Code generation rules

1. **Proto is the contract**:
   - edit `proto/` only
   - regenerate stubs via `scripts/codegen/`
2. Generated files should be:
   - reproducible
   - either committed consistently (all languages) **or** never committed (preferred)
3. Codegen scripts should support:
   - local developer execution
   - CI execution (same output)

Recommended script layout:

```text
scripts/
└── codegen/
    ├── generate_protos.sh
    ├── python.sh
    ├── rust.sh
    └── javascript.sh
```

---

## Adding a new component (checklist)

### New Rust crate

1. Create `src/rust/crates/<name>/` (library) or `src/rust/apps/<name>/` (binary)
2. Add it to the workspace in `src/rust/Cargo.toml`
3. Add minimal tests and a `README.md`

### New Python service

1. Create `src/services/<service-name>/`
2. Add `pyproject.toml`, `Dockerfile`, `README.md`
3. Wire it into `deploy/docker/docker-compose.yml` (and optionally K8s)
4. Add health checks + basic integration tests

### New public API surface

1. Update `proto/eigen_api/v1/*.proto`
2. Regenerate stubs (`scripts/codegen/*`)
3. Update `docs/api-reference/`
4. If the change is breaking or wide-impact, add an RFC (and an ADR once accepted)

---

## Naming and file conventions

- Directory names: `kebab-case` (e.g., `driver-manager`)
- Python packages: `snake_case`
- Rust crates: `kebab-case` (Cargo convention)
- Specs:
  - schemas in `schema/`
  - canonical examples in `examples/`

---

## What goes in an RFC vs an ADR

- **RFC**: a proposal for a significant change (new API, new subsystem, large refactor)
- **ADR**: the final decision record (what we chose + why + consequences)

A typical flow is:

1. Open an RFC PR → discuss → merge
2. Implement → validate
3. Write an ADR referencing the RFC → merge

