# Eigen Compiler Architecture Specification

Status snapshot: updated on 2026-05-25 based on implemented repository state, RFCs, ADRs, compiler contracts, integration tests, and architectural roadmap.

This document is the canonical specification of the Eigen Compiler subsystem.

The document explicitly distinguishes:

- implemented behavior,
- mandatory behavior required by the technical specification,
- planned but not yet implemented capabilities.

This document supersedes informal MVP-only descriptions and defines the target production architecture while preserving current implementation truthfulness.

---

## 1. Purpose

The Eigen Compiler is the canonical compilation subsystem of Eigen OS responsible for transforming high-level hybrid quantum-classical programs into deterministic executable intermediate representations.

The compiler acts as the semantic boundary between:

- user-defined declarative programs,
- distributed runtime orchestration,
- heterogeneous quantum hardware backends.

The compiler MUST provide:

- deterministic compilation,
- safe AST-only processing,
- backend-independent IR generation,
- optimization pipelines,
- hardware-aware transformation,
- observability and auditability,
- extensibility through modular compiler stages.

---

## 2. Architectural Role

The compiler is a runtime service positioned between:

- `system-api`,
- `eigen-kernel`,
- `driver-manager`,
- hardware optimization pipelines.

The compiler receives validated program specifications and produces:

- AQO intermediate representation,
- metadata artifacts,
- optimization hints,
- hardware placement annotations,
- validation diagnostics.

The compiler MUST NEVER execute user code.

---

## 3. Current Implementation Status

### 3.1 Implemented

Implemented in the current repository:

| **Capability** | **Status** |
|---|---|
| AST-only parsing | Implemented |
| Python `ast.parse` frontend | Implemented |
| Deterministic AQO lowering | Implemented |
| Safety validation | Implemented |
| Restricted Eigen-Lang subset | Implemented |
| Internal gRPC compile service | Implemented |
| AQO JSON v0.1 output | Implemented |
| Structured validation errors | Implemented |
| Trace propagation | Implemented |
| Deterministic compilation baseline | Implemented |

---

### 3.2 Partially Implemented

| **Capability** | **Status** |
|---|---|
| Distributed compiler metadata | Partial |
| Compiler observability | Partial |
| AQO metadata annotations | Partial |

---

### 3.3 Planned

| **Capability** | **Status** |
|---|---|
| Typed frontend | Planned |
| Neuro-symbolic DPDA compiler | Planned |
| Transformer-assisted optimization | Planned |
| Knowledge-base optimization | Planned |
| GNN hardware optimizer | Planned |
| Incremental compilation | Planned |
| Plugin architecture | Planned |
| Multi-target backend lowering | Planned |
| QASM3 backend generation | Planned |
| Compiler caching | Planned |

---

## 4. Core Architectural Principles

### 4.1 Deterministic Compilation

The compiler MUST guarantee:

```text
same_source
+ same_options
+ same_input_references
= identical_AQO_output
```

Determinism applies to:

- AQO structure,
- operation ordering,
- parameter mapping,
- metadata ordering,
- canonical serialization.

---

### 4.2 AST-Only Safety Model

The compiler MUST NEVER:

- execute Python bytecode,
- import runtime modules dynamically,
- evaluate expressions,
- invoke external processes.

Compilation is restricted to:

- parsing,
- validation,
- symbolic transformation,
- deterministic lowering.

---

### 4.3 Backend Independence

AQO MUST remain backend-neutral.

Hardware-specific optimization MUST occur after canonical AQO generation.

---

### 4.4 Modular Pipeline

The compiler architecture MUST remain stage-oriented.

Mandatory stages:

1. Source ingestion
2. Parsing
3. Validation
4. Semantic analysis
5. IR generation
6. Optimization
7. Hardware adaptation
8. AQO serialization

---

## 5. Compiler Architecture

### 5.1 High-Level Pipeline

```text
Source
  ↓
Parser
  ↓
AST Validator
  ↓
Semantic Analyzer
  ↓
Eigen-DPDA Core
  ↓
AQO Generator
  ↓
Optimizer Pipeline
  ↓
Hardware Optimizer (GNN)
  ↓
AQO Output
```

---

### 5.2 Frontend Layer

#### Responsibility

The frontend is responsible for:

- source decoding,
- syntax parsing,
- AST construction,
- structural validation,
- semantic extraction.

#### Implemented

Implemented now:

- Python AST parsing,
- UTF-8 validation,
- restricted AST traversal,
- decorator detection,
- import restrictions,
- forbidden-call validation.

#### Planned

Planned frontend capabilities:

- formal lexer/parser,
- typed symbol tables,
- semantic type checker,
- module graph support,
- incremental AST caching,
- compiler plugin hooks.

---

## 6. Eigen-Lang Processing

### 6.1 Supported MVP Subset

Implemented subset:

| **Feature** | **Status** |
|---|---|
| `@hybrid_program` | Implemented |
| `rx()` | Implemented |
| `ry()` | Implemented |
| `rz()` | Implemented |
| `cx()` | Implemented |
| `Param()` | Implemented |
| terminal measurement | Implemented |

---

### 6.2 Forbidden Constructs

The following are rejected:

| **Construct** | **Status** |
|---|---|
| `exec` | Rejected |
| `eval` | Rejected |
| `compile` | Rejected |
| `subprocess` | Rejected |
| `unrestricted imports` | Rejected |
| dynamic runtime control flow | Rejected |

---

### 6.3 Dynamic Control Flow

Currently rejected:

- `if`
- `for`
- `while`
- `match`

This restriction exists to preserve:

- deterministic lowering,
- bounded compilation complexity,
- safety guarantees.

Future controlled symbolic flow MAY be introduced through explicit compiler IR constructs.

---

## 7. Eigen-DPDA Neuro-Symbolic Compiler Core

### 7.1 Purpose

The Eigen-DPDA subsystem is the long-term neuro-symbolic compilation core of Eigen OS.

Its responsibility is to combine:

- formal deterministic automata,
- symbolic program reasoning,
- neural optimization models,
- learned transformation strategies.

---

### 7.2 Architectural Model

The Eigen-DPDA architecture combines:

| **Layer** | **Purpose** |
|---|---|
| Symbolic DPDA | Deterministic compilation correctness |
| Transformer models | Optimization prediction |
| Knowledge base | Pattern reuse |
| Rule engine | Safety and semantic constraints |

---

### 7.3 Deterministic Boundary

Neural models MUST NEVER violate:

- AQO correctness,
- semantic equivalence,
- compiler safety invariants,
- determinism guarantees.

Neural outputs are advisory.

Final compilation decisions MUST remain validated by symbolic stages.

---

### 7.4 Planned Capabilities

Planned Eigen-DPDA features:

- learned circuit rewriting,
- optimization prediction,
- parameter initialization heuristics,
- ansatz selection,
- topology-aware rewrite planning,
- cost-model prediction,
- distributed compilation optimization.

---

### 7.5 Knowledge Base Integration

The compiler architecture includes a persistent optimization knowledge base.

Target stored mappings:

```text
task_signature
→ optimal_circuit_pattern
→ execution_metrics
→ hardware_performance
```

The knowledge base is intended for:

- optimization reuse,
- neural training datasets,
- hardware adaptation learning,
- compilation acceleration.

Not yet implemented.

---

## 8. AQO Intermediate Representation

### 8.1 Purpose

AQO (Abstract Quantum Operations) is the canonical intermediate representation between:

- compiler,
- kernel,
- runtime services,
- hardware adapters.

---

### 8.2 Current AQO Version

Implemented version:

```text
AQO v0.1
```

---

### 8.3 Current Supported Operations

Implemented operations:

| **Operation** | **Status** |
|---|---|
| `RX` | Implemented |
| `RY` | Implemented |
| `RZ` | Implemented |
| `CX` | Implemented |
| `MEASURE imports` | Implemented |

---

### 8.4 Current Output Format

Implemented format:

```text
canonical JSON serialization
```

Planned formats:

- protobuf AQO,
- binary AQO,
- backend-native IR,
- QASM3 output.

---

## 9. Optimization Pipeline

### 9.1 Current State

Current optimization behavior is minimal and deterministic.

Implemented:

- structural normalization,
- canonical AQO generation.

Not implemented:

- rewrite optimization,
- routing optimization,
- algebraic simplification,
- gate fusion,
- dead code elimination.

---

### 9.2 Planned Optimization Stages

Target optimization pipeline:

1. Constant folding
2. Symbolic simplification
3. Dead operation elimination
4. Gate fusion
5. Circuit depth reduction
6. Hardware routing adaptation
7. Noise-aware optimization
8. Scheduling-aware rewriting

---

## 10. GNN Hardware Optimizer

### 10.1 Purpose

The GNN Hardware Optimizer is the planned hardware-aware optimization subsystem of Eigen OS.

Its responsibility is to adapt AQO execution plans to real hardware topology and noise characteristics.

### 10.2 Architectural Role

The optimizer operates after canonical AQO generation.

Inputs:

- AQO graph,
- hardware topology graph,
- calibration metadata,
- connectivity constraints,
- error models.

Outputs:

- optimized qubit placement,
- routing plans,
- swap minimization,
- hardware-adapted execution plans.

---

### 10.3 GNN Model Responsibilities

The GNN subsystem is intended to predict:

| **Capability** | **Purpose** |
|---|---|
| qubit placement | topology optimization |
| routing strategy | minimize swap overhead |
| gate scheduling | reduce decoherence |
| backend adaptation | vendor-specific optimization |
| noise-aware remapping | execution fidelity improvement |

---

### 10.4 Deterministic Safety Boundary

The GNN optimizer MUST remain bounded by symbolic validation.

The optimizer MAY recommend transformations but MUST NOT:

- violate AQO semantics,
- alter observable meaning,
- bypass compiler correctness checks.

---

### 10.5 Implementation Status

| **Capability** | **Status** |
|---|---|
| Architectural contracts | topology optimization |
| ADR alignment | minimize swap overhead |
| Production execution path | reduce decoherence |
| Training infrastructure | vendor-specific optimization |
| Runtime inference integration | execution fidelity improvement |

---

## 11. Interfaces

### 11.1 Internal gRPC Services

Implemented services:

| **RPC** | **Status** |
|---|---|
| CompileCircuit | Implemented |
| CompileJob | Implemented |

Current placeholder services:

| **RPC** | **Status** |
|---|---|
| OptimizeCircuit | Returns `UNIMPLEMENTED` |
| ValidateCircuit | Returns `UNIMPLEMENTED` |

---

### 11.2 Planned API Expansion

Future compiler APIs MAY include:

- optimization-only requests,
- validation-only requests,
- AST inspection,
- compiler hints,
- hardware profile selection,
- distributed compile sessions.

---

## 12. Input Contracts

### 12.1 Implemented Inputs

Implemented request inputs:

| **Field** | **Status** |
|---|---|
| `source` | Implemented |
| `source_ref` | Parsed only |
| `options` map | Implemented |

---

### 12.2 Planned Input Extensions

Planned additions:

- compiler profiles,
- optimization policies,
- hardware constraints,
- distributed compilation hints,
- caching directives.

---

## 13. Output Contracts

### 13.1 Implemented Outputs

Implemented outputs:

| **Artifact** | **Status** |
|---|---|
| AQO JSON | Implemented |
| metadata map | Implemented |
| validation violations | Implemented |

---

### 13.2 Planned Outputs

Planned outputs:

- typed IR,
- annotated AST,
- optimization reports,
- placement maps,
- compilation traces,
- symbolic analysis artifacts.

## 14. Resource Limits

### 14.1 Current Limits

Implemented environment-based limits:

| **Variable** | **Purpose** |
|---|---|
| `EIGEN_COMPILER_MAX_SOURCE_BYTES` | source size limit |
| `EIGEN_COMPILER_MAX_AST_NODES` | AST node limit |
| `EIGEN_COMPILER_MAX_AST_DEPTH` | AST depth limit |

---

### 14.2 Planned Enforcement

Future work:

- unified policy enforcement,
- per-tenant quotas,
- distributed resource budgeting.

---

## 15. State and Storage

### 15.1 Current State Model

Implemented now:

- stateless request handling,
- no persistent compiler cache,
- no persistent AST storage.

---

### 15.2 Planned Persistent Systems

Planned systems:

- AST cache,
- compilation cache,
- distributed artifact storage,
- optimization knowledge base,
- incremental compilation state.

---

## 16. Failure Handling

### 16.1 Implemented Failures

Implemented failure categories:

| **Failure** | **Behavior** |
|---|---|
| syntax errors | INVALID_ARGUMENT |
| UTF-8 errors | INVALID_ARGUMENT |
| forbidden imports | INVALID_ARGUMENT |
| resource limit violations | INVALID_ARGUMENT |
| unsupported RPCs | UNIMPLEMENTED |

---

### 16.2 Planned Failure Taxonomy

Planned structured categories:

- semantic errors,
- optimization failures,
- plugin failures,
- hardware adaptation failures,
- neural inference failures.

---

## 17. Observability

### 17.1 Implemented

Implemented:

- structured RPC lifecycle logging,
- trace propagation,
- correlation metadata.

---

### 17.2 Planned

Planned observability:

- Prometheus metrics,
- OpenTelemetry spans,
- compilation phase timing,
- optimization telemetry,
- neural inference metrics,
- compiler SLO dashboards.

---

## 18. Security Invariants

The compiler MUST obey the following invariants.

### 18.1 No User Code Execution

User code MUST NEVER execute inside compiler processes.

### 18.2 Deterministic Output

Equivalent inputs MUST produce identical AQO outputs.

### 18.3 Restricted Runtime Surface

The compiler MUST reject:

- unsafe imports,
- filesystem access,
- network access,
- subprocess execution.

### 18.4 Neural Safety Boundary

Neural optimization systems MUST remain subordinate to symbolic validation.

---

## 19. Technology Stack

| **Component** | **Technology** |
|---|---|
| Compiler runtime | Python 3.12+ |
| AST frontend | Python AST |
| RPC layer | gRPC |
| Serialization | Protocol Buffers + JSON |
| Planned ML stack | PyTorch / JAX |
| Planned GNN stack | PyTorch Geometric / DGL |

---

## 20. Conclusion

The Eigen Compiler is the deterministic neuro-symbolic compilation subsystem of Eigen OS.

The current implementation already provides:

- safe AST-only compilation,
- deterministic AQO generation,
- restricted Eigen-Lang support,
- structured validation,
- service-oriented compiler APIs.

The target architecture extends this foundation into:

- a full neuro-symbolic compiler pipeline,
- transformer-assisted optimization,
- knowledge-driven compilation,
- GNN-based hardware adaptation,
- distributed intelligent optimization.

This document is the canonical specification for the compiler subsystem, including both currently implemented behavior and approved architectural targets.
