# MVP Scope & Requirements

## Summary

Defines the Minimal Viable Product (MVP) scope for Eigen OS Phase 0. The MVP delivers an end‑to‑end quantum workflow execution system capable of running simple VQE‑style hybrid algorithms on a local simulator via a unified command‑line interface.

## In Scope (MVP)

### 1. Core Services

- **system‑api (Python)**: Public gRPC API gateway, authentication/authorization, request validation

- **eigen‑kernel (Rust)**: QRTX scheduler, task state machine, execution pipeline, QFS access

- **eigen‑compiler (Python)**: AST‑only compilation from Eigen‑Lang to AQO

- **driver‑manager (Python)**: Plugin‑based driver management with simulator backend

### 2. User Interface

- **eigen‑cli (Rust)**: Command‑line interface with `submit`, `status`, `result`, `compile`, `visualize` commands

- **JobSpec v0.1**: YAML‑based job specification format

- **program.eigen.py**: Python DSL with `@hybrid_program` decorator

### 3. Data & Storage

- **CircuitFS (QFS‑L3)**: Local filesystem storage for job artifacts

- **AQO v0.1**: Abstract Quantum Operations format (JSON canonical)

- **Standardized artifact layout**: Predictable paths per `job_id`

### 4. Integration Points

- **Public gRPC API (eigen_api.v1)**: `JobService`, `DeviceService`

- **Internal gRPC APIs**: `KernelGateway`, `CompilationService`, `DriverManagerService`

- **Simulator backend**: Local quantum circuit simulator via QDriver API

### 5. Observability

- **Basic metrics**: Prometheus metrics for API, kernel, driver‑manager

- **Structured logging**: JSON logs with `trace_id`, `job_id`, `service`

- **Trace propagation**: OpenTelemetry‑compatible headers

### 6. Security

- **API‑key authentication**: Static token validation at system‑api

- **Role‑based permissions**: Basic `jobs:*`, `devices:list` roles

- **Network isolation**: Internal services on private network

## Out of Scope (Post‑MVP)

### Phase 1+ Features

- **Real hardware drivers**: IBM Quantum, AWS Braket, etc.

- **Advanced QFS**: StateStore (L2), LiveQubitManager (L1)

- **Neuro‑symbolic compiler**: AI‑based optimization passes

- **Hardware optimizer**: GNN‑based qubit mapping

- **Web dashboard**: Graphical user interface

- **Multi‑tenant scheduling**: Advanced fairness, quotas

- **High availability**: Multi‑node deployment, failover

- **Advanced monitoring**: SLOs, alerting, multi‑tenant dashboards

- **Workflow orchestration**: DAG‑based multi‑job workflows

- **Advanced security**: OIDC integration, hardware isolation

## Functional Requirements

### FR‑1: Job Submission

- **FR‑1.1**: CLI accepts `job.yaml` with Eigen‑Lang source and target `sim:local`

- **FR‑1.2**: System‑api validates request and forwards to kernel

- **FR‑1.3**: Kernel creates job record and begins pipeline execution

### FR‑2: Compilation Pipeline

- **FR‑2.1**: Kernel calls compiler with Eigen‑Lang source

- **FR‑2.2**: Compiler parses AST (no execution), validates syntax and imports

- **FR‑2.3**: Compiler produces AQO JSON v0.1 with basic operations (RX/RY/RZ/CX/MEASURE)

- **FR‑2.4**: Artifacts stored in CircuitFS at canonical paths

### FR‑3: Execution Pipeline

- **FR‑3.1**: Kernel requests device allocation (simulator)

- **FR‑3.2**: Driver‑manager loads simulator plugin, executes circuit

- **FR‑3.3**: Results normalized to counts format, stored in CircuitFS

- **FR‑3.4**: Kernel updates job state to DONE

### FR‑4: Results Retrieval

- **FR‑4.1**: Client can poll `GetJobStatus` or stream `StreamJobUpdates`

- **FR‑4.2**: When DONE, client can fetch results via `GetJobResults`

- **FR‑4.3**: Results include measurement counts and execution metadata

### FR‑5: Device Management

- **FR‑5.1**: `ListDevices` returns simulator as available device

- **FR‑5.2**: `GetDeviceStatus` shows simulator as ONLINE

- **FR‑5.3**: `ReserveDevice` reserves scheduler slot (stub for MVP)

### FR‑6: Basic Observability

- FR‑6.1: All services emit structured logs with correlation IDs

- FR‑6.2: Metrics available at `/metrics` endpoints

- FR‑6.3: Trace context propagated through gRPC calls

## Non‑Functional Requirements

### NFR‑1: Performance

- **NFR‑1.1**: End‑to‑end latency < 5 seconds for 5‑qubit circuit (p95)

- **NFR‑1.2**: Compilation time < 1 second for 100‑line Eigen‑Lang program

- **NFR‑1.3**: System‑api request latency < 100ms (p95)

### NFR‑2: Scalability

- **NFR‑2.1**: Kernel supports concurrent execution of 10+ jobs

- **NFR‑2.2**: System‑api handles 100+ concurrent connections

- **NFR‑2.3**: CircuitFS stores 1000+ job artifacts

### NFR‑3: Reliability

- **NFR‑3.1**: Job state persisted across service restarts

- **NFR‑3.2**: Artifacts remain accessible after job completion

- **NFR‑3.3**: Failed jobs provide clear error messages

### NFR‑4: Usability

- **NFR‑4.1**: CLI provides clear, actionable error messages

- **NFR‑4.2**: JobSpec YAML is human‑readable and well‑documented

- **NFR‑4.3**: All services have Docker‑based deployment

### NFR‑5: Security

- **NFR‑5.1**: No secrets stored in plaintext

- **NFR‑5.2**: Internal services inaccessible from public network

- **NFR‑5.3**: User code execution isolated (AST‑only parsing)

## Acceptance Criteria

### AC‑1: End‑to‑end VQE Execution

**Scenario**: User submits a simple VQE job for H₂ molecule
```text
Given: User has valid API token
And: User creates `program.eigen.py` with @hybrid_program
And: User creates `job.yaml` with target: "sim:local"
When: User runs `eigen-cli submit --job job.yaml --watch`
Then: Job completes with DONE status
And: Results show measurement counts
And: All artifacts stored in CircuitFS
```

### AC‑2: Compilation Validation

**Scenario**: User compiles program locally without submission
```text
Given: User has eigen‑cli installed
When: User runs `eigen-cli compile --job job.yaml --out circuit.aqo.json`
Then: AQO JSON file is generated
And: AQO validates against v0.1 schema
And: No network calls are made
```

### AC‑3: Device Discovery

**Scenario**: User lists available quantum devices
```text
Given: User has valid API token
When: User runs `eigen-cli devices list`
Then: "sim:local" appears as ONLINE device
And: Device details include simulator backend type
```

### AC‑4: Job Status Monitoring

**Scenario**: User monitors job progress via streaming
```text
Given: Job is submitted with job_id
When: User runs `eigen-cli status <job_id> --watch`
Then: User sees state transitions: PENDING → COMPILING → RUNNING → DONE
And: Terminal state appears exactly once
```

### AC‑5: Error Handling

**Scenario**: User submits invalid Eigen‑Lang program
```text
Given: User creates program with syntax error
When: User submits job
Then: Job fails with ERROR status
And: Error message indicates line/column of syntax error
And: No partial artifacts remain in system
```

### AC‑6: Artifact Persistence

**Scenario**: User retrieves results after job completion
```text
Given: Job completed successfully 24 hours ago
When: User runs `eigen-cli result <job_id>`
Then: Results are returned identical to original execution
And: Artifacts are retrievable from CircuitFS
```

## Limitations

### L‑1: Algorithm Support

- Only VQE/QAOA‑style parameterized circuits

- No mid‑circuit measurement feedback

- No classical control flow (if/for) in quantum code

- Limited to single‑entrypoint programs

### L‑2: Device Support

- Simulator only (no real hardware)

- Single simulator backend (no vendor choice)

- No device calibration or noise modeling

### L‑3: Scalability Limits

- Single‑host deployment only

- No high availability or failover

- Limited concurrent job execution

- No distributed CircuitFS

### L‑4: Security Limitations

- API‑key authentication only (no OIDC)

- No hardware‑level isolation

- Limited sandboxing of user code

- No audit logging beyond basic events

### L‑5: Observability Limits

- No advanced alerting

- No long‑term metric retention

- Limited trace sampling

- No custom dashboard

## Success Metrics

### Quantitative

- **M‑1**: End‑to‑end job success rate > 95%

- **M‑2**: P95 job completion time < 10 seconds (5‑qubit circuit)

- **M‑3**: API availability > 99% (weekly measurement)

- **M‑4**: Zero critical security vulnerabilities

### Qualitative

- **Q‑1**: Documentation enables new users to run first job in < 15 minutes

- **Q‑2**: Error messages help users diagnose 80% of common issues

- **Q‑3**: API design receives positive feedback from 3+ external reviewers

## Deployment Requirements

### Development

- Docker Compose for local development

- All services run on single host

- Simulator backend included in distribution

### Testing

- Unit tests for all services (> 80% coverage)

- Integration tests for end‑to‑end workflow

- Golden tests for AQO serialization

- Compatibility tests for JobSpec parsing

### Distribution

- Docker images for all services

- Binary releases for eigen‑cli

- Python package for compiler library

- Example jobs and documentation

---

**References:**

    RFC 0002: System architecture boundaries

    RFC 0003: JobSpec v0.1

    RFC 0004: Public gRPC API

    RFC 0010: eigen‑cli MVP

    RFC 0011: Eigen‑Lang submission format