# Eigen OS — Operating System for Hybrid Quantum‑Classical Computing

**The bridge between declarative intent and quantum hardware.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/Status-Architecture%20%26%20Contracts-orange)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![Rust](https://img.shields.io/badge/Rust-1.92%2B-orange)

> ⚠️ **Project status:** Eigen OS is in the **architecture + contracts** phase (pre‑alpha).  
> Expect breaking changes until **v1.0**. Contracts are frozen only when an RFC is marked **Accepted** and the corresponding reference docs/tests exist.

---

## 🎯 Vision

Eigen OS is an open, modular operating system designed to transform heterogeneous and unstable quantum hardware resources into a unified, predictable, and efficient computing environment — with first‑class support for **hybrid quantum‑classical workflows**.

### What we want to enable
- Domain specialists describe **intent** (circuits, objectives, constraints).
- Eigen OS compiles intent into a portable IR and orchestrates execution on simulators and real backends.
- A stable device abstraction layer makes “different hardware” feel consistent.

---

## ✅ What we’re building now (MVP scope)

This repository currently focuses on **freezing the MVP contracts** and preparing an implementation that can run end‑to‑end on a simulator.

### MVP deliverables (architecture → runnable skeleton)
**Contracts (source of truth)**
- **JobSpec v0.1** (`job.yaml`) — how jobs are described.
- **Public gRPC API** (`eigen_api.v0.1`) — job/device lifecycle.
- **Internal RPC** (kernel/compiler/driver manager).
- **AQO v0.1** — canonical intermediate representation (IR).
- **Error model + error mapping** — consistent behavior across layers.

**Eigen‑Lang v0.1 (MVP)**
- **RFC 0012**: language scope + safety + compatibility policy.
- Reference spec: syntax/semantics/allowlist + mapping to AQO.
- **AST‑only compilation** (no execution of user Python on the server).

**Runnability (MVP target)**
- Local stack that supports: `submit → compile → execute(sim) → results`.
- Simulator driver as a “golden backend”.
- Basic observability: metrics endpoint + trace context propagation.

---

## 🧭 What comes later (Post‑MVP)

These are intentionally **out of MVP** and will be designed/implemented in later phases:

- Real hardware drivers (multiple vendors) + calibration pipelines
- Advanced scheduling (multi‑tenant quotas, fairness, priority classes)
- Hybrid workflow engine expansions (rich loop constructs, distributed execution)
- Knowledge Base / GNN optimizer / neuro‑symbolic expansions beyond MVP baseline
- HA / multi‑region deployments, production hardening

---

## 🏗️ Architecture (high‑level)

Eigen OS is organized as layered contracts:

1) **Abstraction**: Eigen‑Lang + System API (public boundary)  
2) **Kernel**: orchestration + scheduling + job lifecycle (QRTX)  
3) **Runtime services**: compiler + driver manager + storage (QFS)  
4) **HAL**: device drivers (QDriver) for simulators and hardware

📌 Start here: **`docs/README.md`**  
- Architecture overview: `docs/architecture/overview.md`  
- Contract map: `docs/architecture/contract-map.md`  
- Components: `docs/architecture/components.md`

---

## 📚 Documentation & RFCs

### Documentation (developers)
Docs are structured using **Diátaxis** (Tutorials / How‑to / Reference / Explanation).  
- Entry point: `docs/README.md`
- Language reference: `docs/reference/eigen-lang/README.md`
- API/contracts: `docs/reference/`
- MVP DoD: `docs/development/mvp-definition-of-done.md`

### RFCs (design contracts)
- RFCs live in: `rfcs/`
- A change that affects users or cross‑service contracts **must** go through an RFC.

---

---

## 🔖 Versioning & stability

- Until **v1.0**, Eigen OS APIs and file formats may change (breaking changes are expected while we iterate).
- When contracts are accepted, we treat them as the project’s **public API** and document changes.
- Releases will follow **Semantic Versioning** and changes will be recorded in **CHANGELOG.md** (Keep a Changelog format).


## 🧩 Repository structure (current / target)

> Names can be adjusted during design. The goal is: **contracts are obvious**, and implementation follows.

```text
eigen-os/
├── rfcs/                       # RFCs (design proposals, contract freezes)
├── docs/                       # Developer docs (source of truth)
├── proto/                      # Protobuf contracts (public + internal)
├── eigen-kernel/               # Kernel (QRTX, scheduler, state machine) [Rust]
├── eigen-driver-manager/       # Driver manager + plugin runtime [Rust]
├── eigen-qdrivers/             # Drivers (simulator first, then hardware) [Rust]
├── eigen-compiler/             # Eigen‑Lang → AQO compiler [Python]
├── eigen-lang/                 # Eigen‑Lang stdlib + tooling (validator) [Python]
├── eigen-cli/                  # CLI client [Rust]
└── eigen-examples/             # Examples / tutorials
```

---

## 🚀 Getting started (right now)

Eigen OS is not “install and run” yet. **Today you can contribute by freezing contracts and docs.**

### For contributors (design phase)
1) Read `docs/README.md` (architecture + contracts).
2) Analyze the RFC in rfcs/and leave comments in the GitHub discussion (RFC discussion).
3) Help complete reference docs:
   - JobSpec, AQO, error model, Eigen‑Lang reference
4) Help set up CI gates:
   - protobuf lint + breaking checks
   - conformance tests (Eigen‑Lang → AQO)

### Planned “first runnable” milestone
A local simulator E2E quickstart will appear in:
- `docs/tutorials/quickstart-local-sim.md`

---

## 👥 Contributing

We welcome contributions — especially on contracts and docs while the project is in blueprint mode.

**How to help now**
- Review RFCs / propose ADRs
- Improve reference docs and examples
- Implement the simulator driver and conformance tests
- Wire up CI (proto checks, linting, integration tests)

> `CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` / `SECURITY.md` will be added as the repo stabilizes.

---

## 📄 License

Licensed under the **Apache License 2.0**. See [LICENSE](LICENSE).