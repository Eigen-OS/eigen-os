# ⚛️ Eigen OS — Contract‑First Operating System for Hybrid Quantum‑Classical Computing

[![Project Status](https://img.shields.io/badge/status-Product%201.0%20Alignment-blue)](https://github.com/Eigen-OS/eigen-os)
[![Target Version](https://img.shields.io/badge/target-1.0.0-purple)](https://github.com/Eigen-OS/eigen-os/milestone/1)
[![License](https://img.shields.io/badge/License-Apache_2.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![Rust](https://img.shields.io/badge/Rust-1.92+-orange)](https://www.rust-lang.org/)
[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://www.python.org/)

**Eigen OS** is an open, modular operating system for deterministic hybrid quantum‑classical workloads.  
It provides a single platform – from a declarative domain‑specific language down to real quantum hardware – while continuously learning and optimising itself based on accumulated operational data.

> 📄 **Specification version:** 1.3.0 (Target Standard)  
> 🧠 **Core principle:** Data‑centric self‑learning – the system becomes smarter with every run.

---

## 📌 Current Status (Product 1.0 alignment)

The project follows the **Product 1.0 Contract Alignment Plan** – a service‑by‑service, contract‑by‑contract implementation roadmap.

| Milestone | Status |
|-----------|--------|
| **Wave 0** – Baseline freeze & contract inventory | ✅ Completed |
| **Wave 1** – Public API, JobSpec, error model closure | ✅ Completed |
| **Wave 2** – Kernel/QRTX becomes lifecycle authority | ✅ Completed |
| **Wave 3** – Compiler, Eigen-Lang, and AQO closure | ✅ Completed |
| **Wave 4** – QFS data fabric maturity | ✅ Completed |
| **Wave 5** – Resource Manager and multi-device execution | ✅ Completed |
| **Wave 6** – Driver Manager and QDriver final contract | 🔄 In progress |
| **Waves 7–10** – Optimizer, Knowledge Base, Security, Observability, Release | ⏳ Planned |

All normative contracts described in `docs/reference/` are being implemented as versioned wire representations with conformance tests, canonical errors, and observability markers. The **target release** is **Product `1.0.0`** – a mature, contract‑first platform.

---

## 🎯 Vision & Mission

**Vision**  
Eigen OS acts as a semantic bridge between a high‑level user problem (chemistry, finance, ML) and unstable, heterogeneous quantum hardware. It hides the physics of qubits, compilation, and optimisation behind a simple declarative interface.

**Mission**  
Make quantum computing accessible to domain experts by automating compilation, mapping, and execution – while continuously improving through machine learning based on every submitted job.

**Key principles**
- **Hybrid‑first by design** – quantum and classical steps are interleaved seamlessly.
- **Interface‑based abstraction** – stable, versioned gRPC/Protobuf contracts connect all components.
- **Neuro‑symbolic adaptation** – hybrid AI models (Neuro‑DPDA, GNN) drive compilation and optimisation.
- **Data‑centric self‑learning** – every run enriches the Knowledge Base, which retrains the intelligent components.
- **Security by design** – Rust kernel, mTLS, JWT/OAuth2, audit, driver sandboxing.

---

## 🧱 Architecture Overview

![Architecture layers](docs/assets/arch-layers.png) *(conceptual diagram)*

| Layer | Components | Technologies |
|-------|------------|--------------|
| **User layer** | Eigen‑Lang DSL, System API (gRPC) | Python, JWT |
| **Kernel** | QRTX (scheduler), QFS (L1/L2/L3), Security Module, Observability | Rust, SQLite, S3/MinIO, Prometheus |
| **Runtime services** | Neuro‑DPDA, GNN Optimizer, Knowledge Base, Dataset Pipeline, Driver Manager | Python + PyTorch, FAISS |
| **Hardware abstraction** | QDriver API, pluggable drivers (Qiskit, Cirq, Braket, …) | gRPC, isolated containers |

For a detailed component breakdown, see [`docs/architecture/components.md`](docs/architecture/components.md).

### End‑to‑end flow (aligned with Product 1.0 contracts)

1. **User** writes a program in **Eigen‑Lang** and submits it via the **System API** (authenticated JWT, idempotency key, trace context).
2. **QRTX** (Rust kernel) validates the JobSpec, builds a DAG, and enqueues the job.
3. **Neuro‑DPDA** compiles Eigen‑Lang to **AQO** (platform‑independent IR), assisted by similar circuits from the Knowledge Base.
4. **GNN Optimizer** maps logical qubits to the physical topology of the target device, inserts SWAP gates, and emits a QASM circuit.
5. **Driver Manager** selects the appropriate QDriver and executes the circuit (simulator or real hardware).
6. **Results** are stored in **QFS Level 3** (CircuitFS) and recorded in the **Knowledge Base**.
7. **Continuous learning** – after a configurable number of new circuits, the Neuro‑DPDA and GNN are retrained on the fresh data.

---

## 🧠 Key Components (Product 1.0 focus)

### 1. Eigen‑Lang DSL

Declarative language embedded in Python. Allows expressing hybrid algorithms, parametrised circuits, and benchmarks without low‑level details.

```python
from eigen_lang import *

@hybrid_program(target="simulator", shots=4096, optimization_level=3)
def vqe_h2():
    H = make_molecular_hamiltonian("H2", basis="sto-3g")
    ansatz = create_hea_ansatz(n_qubits=H.n_qubits, depth=3)
    
    @cost_function
    def energy(params):
        return ExpectationValue(ansatz, H)
    
    from scipy.optimize import minimize
    res = minimize(energy, [0.1]*ansatz.num_params, method="COBYLA")
    return res.fun
```

#### Product 1.0 guarantees:

- Deterministic parsing and validation (allowlist of imports, decorators, built‑ins).
- Every compilation failure returns a canonical error code with structured details.
- The same source + same JobSpec options produce exactly the same AQO.

### 2. Eigen Kernel (Rust)

- **QRTX** – central scheduler with priority queues, DAG dependencies, and durable job state. All lifecycle mutations are owned by the kernel; the System API is a thin public gateway.
- **Quantum File System (QFS):**

    - **Level 3 (CircuitFS)** – long‑term object storage (S3/MinIO) for sources, AQO, QASM, results (Parquet), datasets.
    - **Level 2 (State Store)** – checkpoint storage for quantum states (statevector, MPS, shadows) in HDF5.
    - **Level 1 (Live Qubit Manager)** – atomic reservation of physical qubits, feed‑forward, telemetry collection.

- **Observability Stack** – Prometheus metrics, OpenTelemetry logs + traces, Grafana dashboards, structured audit events.
- **Security Module** – JWT/OAuth2 validation, RBAC/ABAC policy enforcement, secret management (Vault), mTLS for internal services.

### 3. Neuro‑Symbolic Compiler (Eigen‑DPDA)

Hybrid: deterministic push‑down automaton (PDA) + neural network (Transformer/GNN).
The PDA enumerates allowed compilation actions; the network selects the optimal action given the AST, device noise, and similar circuits from the Knowledge Base. Output is **AQO** (Abstract Quantum Operations).

### 4. GNN Optimizer

Takes an **AQO graph** (logical qubits + gates) and the **device topology** (physical qubits + error rates).
Two Graph Attention Networks compute embeddings, then a soft‑assignment (Sinkhorn) maps logical → physical qubits. Additional heads insert SWAP routes and predict final circuit error.

### 5. Knowledge Base (KB) – the system’s memory

Stores every compiled circuit, its compilation trace, and aggregated patterns.

- **Circuit Record** – hash, AST signature, compiler trace, fidelity, device ID, error.
- **Pattern Record** – reusable optimisation templates.
- **Indexes – vector** (FAISS) for semantic similarity, structural (DuckDB/SQLite) for filtering.
- **API** – `SearchSimilar`, `GetPattern`, `Ingest`.
- **Sources** – real jobs, synthetic datasets (QSBench), benchmarks, pattern miner.

### 6. Driver Manager & QDriver API

Unified gRPC interface for any quantum backend:

- `Initialize`, `Execute`, `GetStatus`, `Calibrate`, `Cancel`.
- Drivers are digitally signed, run in isolated containers, and access secrets only through the Security Module.
- Supported reference backend: built‑in simulator. Optional drivers for Qiskit, Cirq, Braket, IBMQ.

---

## 🚀 Quick Start (local development)

### Prerequisites

- Rust 1.92+, Python 3.12+, Docker & Docker Compose, Git.

### Setup

```bash
git clone https://github.com/Eigen-OS/eigen-os.git
cd eigen-os

# Launch all services via Docker Compose
./deploy/local/dev_env.sh up

# Generate Protobuf bindings
bash scripts/dev/generate-protos.sh

# Run Rust and Python tests
cargo test --manifest-path src/rust/Cargo.toml --workspace
pytest src/services/eigen-compiler/tests
pytest src/services/system-api/tests

# Start a public API skeleton server
python examples/python/public_api_skeleton_server.py
```

After startup:

- System API gRPC `endpoint: localhost:50051`
- Grafana: `http://localhost:3000` (admin/admin)
- MinIO Console: `http://localhost:9001`

### Submit your first job (using Eigen‑Lang)

```python
# my_first_job.py
from eigen_lang import hybrid_program, rx, cx, measure_all

@hybrid_program(target="simulator", shots=1024)
def bell_state():
    rx(0, 3.14159)
    cx(0, 1)
    return measure_all()

if __name__ == "__main__":
    result = bell_state()
    print(result.get_counts())
```

Run it – the CLI will automatically call the System API with idempotency and trace headers.

---

## 🔒 Security (built‑in, not bolted‑on)

- **Kernel in Rust** – memory safety, no buffer overflows or use‑after‑free.
- **Mutual TLS** for all internal RPC; **JWT/OAuth2** for external clients.
- **Driver sandboxing** – signed containers with minimal privileges.
- **Encryption at rest** (S3 SSE) and **in transit** (TLS 1.3).
- **Audit log** – immutable, tamper‑evident security events.
- **CI/CD gates** – SAST, DAST, container scanning, software bill of materials (SBOM).

---

## 📁 Repository Structure (Product 1.0 aligned)

```text
eigen-os/
├── docs/                      # Architecture, reference, ADRs, product plans
│   ├── architecture/          # Includes components.md, contract-map.md
│   ├── reference/             # API, JobSpec, error model, observability contracts
│   └── development/           # Product 1.0 alignment plan, inventory
├── proto/                     # gRPC/Protobuf contracts (public & internal)
├── specs/                     # JobSpec, AQO, QFS layout, Eigen‑Lang grammar
├── src/
│   ├── rust/                  # Kernel, QFS, Security Module, proto bindings
│   ├── services/              # Python services (compiler, optimizer, kb, driver‑manager, etc.)
│   └── eigen-lang/            # Python DSL implementation
├── examples/                  # Example programs and API usage
├── deploy/                    # Docker Compose, Helm charts for Kubernetes
├── monitoring/                # Grafana dashboards, Prometheus alerts
├── rfcs/                      # Proposals and architecture decision records
├── scripts/                   # Helper scripts (protos, tests, local dev)
└── tests/                     # Integration and end‑to‑end conformance tests
```

---

We follow a **contract‑first** process. Any change affecting a public or internal contract requires:

- An RFC (for significant changes) or an ADR (for architectural decisions).
- Updates to the corresponding proto files, reference docs, and conformance tests.
- A compatibility/migration note.

Start by reading:

- [`CONTRIBUTING.md`](https://github.com/Eigen-OS/eigen-os/blob/main/CONTRIBUTING.md)
- [`CODE_OF_CONDUCT.md`](https://github.com/Eigen-OS/eigen-os/blob/main/SECURITY.md)
- [`SECURITY.md`](https://github.com/Eigen-OS/eigen-os/blob/main/CODE_OF_CONDUCT.md)

---

## 📄 License

Apache License 2.0. See [LICENSE](https://github.com/Eigen-OS/eigen-os/blob/main/LICENSE).

---

### Eigen OS – building the bridge between classical and quantum futures. Join us.
