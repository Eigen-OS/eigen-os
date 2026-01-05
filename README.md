# Eigen OS — Operating System for Hybrid Quantum-Classical Computing

**The bridge between declarative intent and quantum hardware.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/Status-Architectural%20Blueprint-orange)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![Rust](https://img.shields.io/badge/Rust-1.92%2B-orange)

## 🎯 Vision
Eigen OS is an open, modular operating system designed to transform heterogeneous and unstable quantum hardware resources into a unified, predictable, and efficient computing environment. Our goal is to make quantum computing programmable, efficient, and accessible for domain specialists.

## 🏗️ Architecture (High-Level)
The system is built upon a four-layer architecture:

1.  **Abstraction Layer (EigenLang & System API):** The declarative EigenLang DSL and a unified gRPC/REST API.
2.  **OS Kernel (Eigen Kernel):** The Quantum Real-Time Executive (QRTX) scheduler, a three-tier storage system, and adaptive monitoring.
3.  **Runtime Services:** A neuro-symbolic compiler, a hardware GNN optimizer, and a driver manager.
4.  **Hardware Abstraction Layer (HAL):** A unified QDriver API for all types of quantum processors.

A detailed architectural description can be found in the [Documentation](/docs/ARCHITECTURE.md).

## 🏗️ Project Structure
This monorepository contains all core components of the Eigen OS stack.
```text
eigen-os/ (this repository)
├── .github/ # GitHub workflows, templates
├── eigen-rfcs/ # Architectural RFCs
├── eigen-docs/ # Documentation source (MkDocs)
├── eigen-kernel/ # OS Kernel (QRTX, Scheduler, Storage) [Rust]
├── eigen-qdal/ # Quantum Device Abstraction Layer [Rust]
├── eigen-lang/ # High-level DSL & API [Python]
├── eigen-compiler/ # Neurosymbolic Compiler & Optimizer [Python]
├── eigen-cli/ # Command-line interface [Rust]
└── eigen-examples/ # Tutorials and example programs
```

## 🚀 Getting Started
The project is currently in the active architectural design and early development phase.

### Prerequisites
*   **Rust & Cargo** (for `eigen-kernel`, `eigen-qdal`, `eigen-cli`)
*   **Python 3.10+ & pip** (for `eigen-lang`, `eigen-compiler`)
*   **Git**

### Development Setup
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Eigen-OS/eigen-os.git
    cd eigen-os
    ```
2.  **Set up the Rust components:**
    ```bash
    # You can build all Rust crates from the root
    cargo build --workspace
    # Or build each component individually
    cd eigen-kernel && cargo build
    ```
3.  **Set up the Python components:**
    ```bash
    # Install eigen-lang and eigen-compiler in editable mode
    cd eigen-lang && pip install -e .
    cd ../eigen-compiler && pip install -e .
    ```
4.  **Explore the examples:**
    ```bash
    cd eigen-examples/basic/bell_state
    # Follow the example's README
    ```

**Next steps for participants:**
1.  Review the **architectural vision** and **roadmap** in discussions.
2.  Study the key **RFCs (Request for Comments)** in the `eigen-rfcs/` directory, which define the project's core interfaces (QDriver API, job format, etc.).
3.  Join the discussion in Issues and Discussions.

## 👥 Contributing
We welcome contributions from the community! The development process is centralized in this monorepository.

Before getting started, please:
1.  Read our **[Code of Conduct](CODE_OF_CONDUCT.md)** and **[Contributing Guide](CONTRIBUTING.md)** (to be created).
2.  **Fork & Clone this repository** – you get the entire stack with one clone.
3.  Create a feature branch, make your changes across relevant components, and submit a **single Pull Request** to this main repository.
4.  Ensure changes are consistent across the stack (e.g., API updates in `eigen-kernel` reflected in `eigen-cli`).
5.  Explore open Issues and discussions.

## 📚 Documentation
*   **Architectural Decisions & Specifications:** See the `/eigen-rfcs/` directory.
*   **User & Developer Guides:** The source for the official website is in `/eigen-docs/`. The rendered site is available at [https://eigen-os.github.io](https://eigen-os.github.io) (when deployed).
*   **Component Documentation:** Each major component (`eigen-kernel/`, `eigen-lang/`, etc.) contains its own detailed `README.md` and source code documentation.

## 📄 License
This project is licensed under the **Apache License 2.0**. The full license text is available in the [LICENSE](LICENSE) file. Note that all components within this monorepo are collectively under this license unless explicitly stated otherwise.

---
*Eigen OS represents a paradigm shift towards the declarative orchestration of hybrid computing.*