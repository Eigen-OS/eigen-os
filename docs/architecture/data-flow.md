# Eigen OS — Data Flow Specification (MVP)

## 1. Overview

This document describes the end-to-end data flow within Eigen OS for the Minimum Viable Product (MVP). It details how data moves through the system, transforming from high-level user intent into executable quantum operations and, ultimately, computed results.

The primary focus is on two critical workflows:

1. **Linear Job Execution**: The fundamental path of submitting, compiling, executing, and retrieving results for a single quantum circuit.

2. **Hybrid Iterative Loop**: The extended flow for variational algorithms like the Variational Quantum Eigensolver (VQE), which involves classical optimization of quantum circuit parameters.

### 1.1. Conceptual Data Flow

The following diagram illustrates the high-level stages of data transformation and the main system components involved.

```text
flowchart TD
    A[User: JobSpec & Eigen-Lang] --> B[System API]
    B -- SubmitJob --> C{Kernel QRTX}
    
    C -- Validate --> D[CircuitFS]
    C -- Enqueue --> E{Orchestration Pipeline}
    
    subgraph E [Kernel Orchestration Pipeline]
        F[Compile<br>AST → AQO]
        G[Allocate<br>Device & Qubits]
        H[Execute<br>on Backend]
        I[Process<br>Results]
    end
    
    E --> J[Results & Artifacts]
    J --> D
    
    D --> K[User: Get Results]
    
    L[Classical Optimizer] -- New Parameters --> E
    I -- Expectation Value --> L
    
    style F fill:#e1f5fe
    style H fill:#f3e5f5
    style L fill:#f1f8e9
```

**Flow Summary:**

- **Solid Lines (Linear Job)**: Data moves from user submission through orchestration to final results.

- **Dashed Lines (Hybrid Loop)**: A classical optimizer receives quantum results, calculates new parameters, and feeds them back into the pipeline for the next iteration.

### 2. Component & Data Format Reference

Before detailing the flows, here are the key components and data formats they exchange.

| **Component** | **Primary Responsibility** | **Key Inputs** | **Key Outputs** | **Relevant RFC** |
|---|---|---|---|---|
| `eigen-cli` | User interaction, local file packaging. | `job.yaml`, `program.eigen.py` | `SubmitJobRequest` (gRPC) | RFC 0010, RFC 0003 |
| **System API** | Public gateway, auth, routing. | `SubmitJobRequest` | `KernelJob` (internal gRPC) | RFC 0004 |
| **Kernel (QRTX)** | Central orchestrator, state machine, storage. | `KernelJob` | Calls to Compiler & Driver Manager | RFC 0007 |
| **Compiler Service** | Source parsing, circuit generation. | Eigen-Lang source | `AQO` (Abstract Quantum Operations) | RFC 0011, RFC 0005 |
| **Driver Manager** | Driver lifecycle, backend abstraction. | `CircuitPayload` (contains AQO) | `ExecutionResult` (counts) | RFC 0006 |
| **QFS (CircuitFS)** | Persistent artifact storage. | All intermediate artifacts | Stored files (JSON, QASM, etc.) | RFC 0007 |

---

| **Data Format** | **Description** | **Typical Representation** | **Purpose** |
|---|---|---|---|
| `JobSpec` | User job description. | `job.yaml` file | Define program, target, options. |
| **Eigen-Lang** | Hybrid quantum-classical DSL. | 	`program.eigen.py` file | Express the computational problem. |
| `AQO` | Platform-independent intermediate representation. | JSON or Protobuf | Bridge between compiler and hardware backends. |
| `CircuitPayload` | Wrapper for executable circuit. | Protobuf message (`format` + `bytes`) | Transport AQO to the Driver Manager. |
| `ExecutionResult` | Raw results from backend. | Protobuf message (`counts` map) | Structured measurement results. |
| `JobResults` | Final, enriched results for user. | JSON stored in QFS | Final output of a job. |

## 3. Primary Flow: Linear Job Execution

### 3.1. Step-by-Step Sequence
```text
sequenceDiagram
    actor User
    participant CLI as eigen-cli
    participant API as System API
    participant Kernel as Kernel (QRTX)
    participant Compiler as Compiler Service
    participant DManager as Driver Manager
    participant Backend as Simulator (e.g., Qiskit Aer)
    participant QFS as QFS (CircuitFS)

    Note over User, QFS: 1. SUBMISSION & VALIDATION
    User->>CLI: eigen submit --job vqe-h2.yaml
    CLI->>CLI: Read & parse job.yaml, program.eigen.py
    CLI->>API: SubmitJob(SubmitJobRequest)
    API->>API: Authenticate/Authorize request
    API->>Kernel: EnqueueJob(KernelJob)
    Kernel->>Kernel: Create Job Record, assign ID
    Kernel->>QFS: Store original job.yaml / source
    Kernel-->>API: JobAccepted(job_id)
    API-->>CLI: SubmitJobResponse(job_id)
    CLI-->>User: Job submitted: job_id=job_123

    Note over User, QFS: 2. COMPILATION
    Kernel->>Compiler: Compile(source, target, options)
    Compiler->>Compiler: Parse AST, validate, optimize
    Compiler->>Compiler: Generate AQO
    Compiler-->>Kernel: CompileResponse(AQO_JSON)
    Kernel->>QFS: Store compiled.aqo.json

    Note over User, QFS: 3. EXECUTION
    Kernel->>Kernel: Allocate resource (sim:local)
    Kernel->>DManager: ExecuteCircuit(job_id, device_id, CircuitPayload(AQO), shots)
    DManager->>DManager: Load simulator driver
    DManager->>Backend: execute(circuit, shots) [Vendor SDK]
    Backend-->>DManager: raw results
    DManager->>DManager: Normalize to counts map
    DManager-->>Kernel: ExecuteCircuitResponse(counts, metadata)
    Kernel->>QFS: Store results.json
    Kernel->>Kernel: Update Job State → DONE

    Note over User, QFS: 4. RESULT RETRIEVAL
    User->>CLI: eigen results job_123
    CLI->>API: GetJobResults(job_id)
    API->>Kernel: GetJobResults(job_id)
    Kernel->>QFS: Fetch results.json
    Kernel-->>API: JobResults
    API-->>CLI: JobResults
    CLI-->>User: Display results
```

### 3.2. Detailed Data Transformation

#### Step 1: Submission & Packaging

1. **User Input**: A `job.yaml` file and a `program.eigen.py` file.
```yaml
# job.yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: h2-ground-state
spec:
  program: |
    @hybrid_program(target="sim:local", shots=1024)
    def main():
        # ... Eigen-Lang code ...
  target: sim:local
  compiler_options:
    optimization_level: "1"
```

2. **CLI Action**: `eigen-cli` reads both files. The `program` field can be inlined (as above) or passed as a reference. It constructs a `SubmitJobRequest` Protobuf message.

3. **System API**: Validates the request, performs authentication, and forwards it as a `KernelJob` message to the Kernel. The auth context (`x-eigen-sub`) is added to the metadata.

4. **Kernel (QRTX)**: Creates a job record with state `PENDING` and stores the original source files in QFS under `circuit_fs/job_123/`.

#### Step 2: Compilation (Eigen-Lang → AQO)

1. **Kernel** transitions the job state to `COMPILING` and calls the **Compiler Service** via gRPC.

2. **Compiler** receives the source. Its workflow is strictly **AST-based (no execution)**:

- **Parse**: Uses Python's `ast.parse()` on the source code.

- **Validate**: Checks for a single `@hybrid_program` decorator and enforces import allowlists (RFC 0012).

- **Transform**: Converts high-level constructs (e.g., `ExpectationValue`) into circuit operations.

- **Generate**: Outputs the circuit in **AQO v0.1 JSON** format.
```json
{
  "version": "0.1",
  "qubits": 4,
  "operations": [
    {"op": "RY", "q": [0], "params": {"theta": "p0"}},
    {"op": "CX", "q": [0, 1]},
    {"op": "MEASURE", "q": [0, 1], "c": [0, 1]}
  ]
}
```

3. The compiled `AQO` is returned to the Kernel, which stores it in QFS.

#### Step 3: Execution (AQO → Results)

1. **Kernel** transitions the job to `QUEUED`, then to `RUNNING`. It resolves the target `sim:local` to a device ID and calls the **Driver Manager**.

2. **Driver Manager** receives a `CircuitPayload` message containing the AQO bytes and a format enum (`AQO_JSON`). It loads the appropriate driver plugin (e.g., `SimulatorDriver`).

3. **Driver** translates the AQO into the backend's native format (e.g., a Qiskit `QuantumCircuit` object) and calls the vendor SDK's `execute` method.

4. **Backend** (Simulator) runs the circuit for the specified number of shots and returns raw data (e.g., a dictionary of bitstrings).

5. **Driver Manager** normalizes this data into a structured `ExecutionResult` with a `counts` map, execution time, and metadata.
```json
{
  "counts": {"00": 512, "11": 512},
  "execution_time_sec": 0.45,
  "metadata": {"backend": "qiskit_aer_simulator"}
}
```

6. **Kernel** receives the result, stores it in QFS as `results.json`, and transitions the job state to `DONE`.

#### Step 4: Result Retrieval

1. The user queries for results via `eigen-cli results job_123`.

2. The request traverses back through the **System API** and **Kernel**, which reads the final `results.json` from **QFS** and returns it in a `JobResults` response.

## 4. Hybrid Loop Flow: Variational Quantum Eigensolver (VQE)

This flow extends the linear flow with a classical feedback loop, which is essential for hybrid algorithms.
```text
flowchart TD
    A[Start: Initial Parameters] --> B[Quantum Sub-Job]
    B --> C{Execute Circuit<br>on Backend}
    C --> D[Compute Expectation Value<br>⟨ψ(θ)|H|ψ(θ)⟩]
    D --> E{Classical Optimizer<br>COBYLA, SPSA...}
    E --> F{Check Convergence?}
    
    F -- No --> G[Generate New Parameters]
    G --> B
    
    F -- Yes --> H[Return Final Result:<br>Min Energy, Optimal Params]
```

**Key Difference from Linear Flow**: Steps B-D (the "Quantum Sub-Job") are essentially the entire Linear Job Flow (compile + execute), but they are repeated in a loop with different input parameters each iteration.

### 4.2. Eigen OS Orchestration of a VQE Loop

The system does not interpret or manage the classical optimization loop internally in MVP. Instead, it provides the mechanism for the loop to run. There are two primary patterns:

#### Pattern A: External Orchestration (MVP Default)

- **Description**: A classical script (e.g., in Python, running on the user's machine) acts as the "orchestrator". It uses the Eigen OS SDK (`eigen-cli` or a gRPC client) to submit each iteration as a separate job.

- **Data Flow:**

1. Orchestrator sets initial parameters `θ_i`.

2. It creates a **JobSpec**, **embedding** `θ_i` **as constants** in the `spec.inputs` map or directly in the source code.

3. It calls `eigen-cli submit` and polls for `JobResults`.

4. From the results (`counts`), it calculates the expectation value `⟨H⟩`.

5. The classical optimizer (e.g., SciPy) running locally produces new parameters `θ_i+1`.

6. Steps 2-5 repeat until convergence.

**System Role**: Eigen OS is treated as a **stateless job execution service**. Each iteration is independent.

#### Pattern B: Parametrized Job with Callback (Future)

- **Description (Post-MVP)**: A single "parent" job is submitted, which defines the variational ansatz and optimizer. The Kernel manages the iteration loop, submitting "child" quantum execution jobs internally.

- **Data Flow:**

1. User submits one **VQE Job**.

2. Kernel identifies it as a hybrid loop, starts a **Classical Runner** task.

3. For each iteration, the Classical Runner:

    - Generates a parameterized **AQO** (with symbolic params).

    - Calls the Driver Manager with the **AQO and concrete parameters** `θ_i`.

    - Receives `counts`, computes `⟨H⟩`.

    - Runs optimizer logic to get `θ_i+1`.

4. Final energy and parameters are stored as the job result.

**MVP Implementation Note**: For Phase 0 (MVP), **Pattern A (External Orchestration) is the supported and expected model**. This keeps the Kernel's responsibility focused and well-defined. Pattern B is a target for Phase 1+.

## 5. Observability Data Flow

Telemetry data flows in parallel to the main business logic, providing insights into system health and performance.
```text
    Main Flow Components              Observability Pipeline
    ──────────────────────────────────────────────────────────
    [eigen-cli]                      ───> [Stdout Logs]
           │                                   │
           v                                   v
    [System API] ───[traceparent]──> [Structured Logs] ───> [Loki]
           │              │                         │
           v              v                         v
    [Kernel]    ───[metrics]──────> [Prometheus]   │
           │              │                         │
           v              v                         v
    [Compiler]  ───[logs/spans]──> [OpenTelemetry Collector]
           │                                   │
           v                                   v
    [Driver Manager]                         [Grafana]
           │
           v
    [Backend]
```

- **Trace Propagation**: A unique `trace_id` (via the `traceparent` header) is generated at the first API call and passed through all gRPC calls (RFC 0008). This allows linking all logs and events related to a single user request (`job_id`).

- **Logging**: Each service emits structured JSON logs containing `trace_id`, `job_id`, `service`, and event-specific data. These are aggregated for search and analysis.

- **Metrics**: System components expose Prometheus metrics (e.g., `eigen_api_request_duration_seconds`, `eigen_kernel_job_state_transitions_total`). These are scraped periodically to monitor throughput, latency, and error rates.

- **Correlation**: In Grafana dashboards, a user can start from a high-level job error, use the `trace_id` to find the corresponding logs from the Kernel, Compiler, and Driver Manager, and pinpoint the exact failure stage.

---

**Version**: 1.0
**Status**: Draft
**Compatibility**: Eigen OS MVP (Phase 0)
**Related Documents**: [RFC 0002: Architecture Boundaries](https://github.com/Eigen-OS/eigen-os/blob/main/rfcs/0002-%20architecture-boundaries.md), [RFC 0007: QRTX MVP](https://github.com/Eigen-OS/eigen-os/blob/main/rfcs/0007-qrtx-mvp.md), [MVP Contract Map](https://github.com/Eigen-OS/eigen-os/blob/main/docs/architecture/contract-map.md)