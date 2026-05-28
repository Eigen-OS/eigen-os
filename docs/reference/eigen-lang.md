# Eigen-Lang Reference Guide v1.0

**Document status:** Stable
**Subsystem:** Eigen Compiler & Hybrid Runtime
**Contract version:** `1.0.0`
**Applies to:** Eigen OS 1.0

---

## 1. Overview

**Eigen-Lang** is the declarative hybrid programming language of Eigen OS used to define quantum-classical workloads.

Eigen-Lang is intentionally:

- deterministic,
- statically analyzable,
- sandbox-safe,
- reproducible,
- compiler-friendly,
- backend-independent.

Eigen-Lang programs compile into **AQO** (Abstract Quantum Operations), which acts as the canonical intermediate representation between the language frontend and runtime execution layers.

The language defines:

- syntax,
- semantic rules,
- validation guarantees,
- allowed AST subset,
- standard library contracts,
- AQO mapping behavior,
- deterministic compilation guarantees,
- compatibility rules,
- conformance expectations.

This document is the normative specification for Eigen-Lang v1.0.

The canonical source-of-truth implementation includes:

- `compiler/eigen_lang/`
- `docs/reference/formats/aqo.md`
- `tests/conformance/eigen_lang/`
- `proto/eigen/api/v1/`
- compiler validation fixtures and golden AQO snapshots.

---

## 2. Design Goals

Eigen-Lang is designed around the following principles:

| **Principle** | **Requirement** |
|----------|----------|
| Deterministic compilation | identical source + config → identical AQO |
| Declarative semantics | users define intent, not execution scheduling |
| Restricted execution | arbitrary Python execution forbidden |
| Static analyzability | compiler validates entire AST before execution |
| Backend independence | language does not encode backend-specific execution |
| Safe sandboxing | no filesystem/network/process access |
| Stable contracts | SemVer-governed language evolution |
| Reproducibility | canonical AQO generation mandatory |

---

## 3. File Format

Eigen-Lang source files SHOULD use: `*.eigen.py`

UTF-8 encoding is mandatory.

Files MUST:

- contain exactly one `@hybrid_program` entrypoint,
- avoid dynamic imports,
- avoid runtime code generation,
- avoid side-effect execution.

---

## 4. Program Structure

### 4.1 Minimal Example

```python
from eigen_lang import (
    hybrid_program,
    Param,
    Observable,
    ExpectationValue,
    rx,
    ry,
    rz,
    cx
)

@hybrid_program(
    compiler="eigen",
    target="simulator",
    shots=1024,
    optimization_level=2
)
def main():
    theta = Param("theta", 0.1)

    rx(0, theta)
    ry(1, 0.2)
    cx(0, 1)
    rz(1, theta)

    return {
        "energy": ExpectationValue(
            observable=Observable(Z=0)
        )
    }
```

---

### 4.2 Entrypoint Rules

Exactly one function MUST be decorated with:

```python
@hybrid_program(...)
```

Compilation fails if:

- zero entrypoints exist,
- multiple entrypoints exist.

The entrypoint function:

- MUST use a valid Python identifier,
- MAY contain arguments,
- MUST remain statically analyzable.

---

## 5. Compiler Security Model

Eigen-Lang source code is NEVER executed directly.

The compiler:

1. parses source into AST,
2. validates allowed constructs,
3. builds internal IR,
4. emits deterministic AQO.

The compiler MUST NOT:

- execute arbitrary Python,
- evaluate runtime imports,
- access host resources,
- perform filesystem access,
- perform network access,
- spawn subprocesses.

Eigen-Lang therefore behaves as a restricted declarative DSL using Python syntax.

---

## 6. Allowed Imports

Only imports from approved Eigen-Lang namespaces are allowed.

Examples:

```python
from eigen_lang import rx, ry, rz
```

```python
from eigen_lang.optimizers import minimize
```

Forbidden imports include:

```python
import os
import sys
import subprocess
import socket
```

Violation MUST fail compilation with: `INVALID_ARGUMENT`

---

## 7. Allowed AST Subset

### 7.1 Allowed Nodes

The following AST nodes are allowed:

| **AST Node** | **Purpose** |
|----------|----------|
| `Module` | file root |
| `FunctionDef` | entrypoint |
| `arguments` | function args |
| `Return` | return values |
| `ImportFrom` | restricted imports |
| `Assign` | assignments |
| `AnnAssign` | typed assignments |
| `Expr` | expressions |
| `Name` | identifiers |
| `Constant` | literals |
| `Call` | approved function calls |
| `List` | fixed containers |
| `Tuple` | fixed containers |
| `Dict` | fixed containersy |
| `BinOp` | limited arithmetic |
| `UnaryOp` | limited arithmetic |

---

### 7.2 Forbidden Nodes

The following constructs are forbidden:

| **Construct** | **Reason** |
|----------|----------|
| `If` | nondeterministic branching |
| `For` | dynamic iteration |
| `While` | dynamic execution |
| `Match` | runtime dispatch |
| `Lambda` | dynamic closures |
| `Try` | dynamic control flow |
| `ClassDef` | runtime mutation |
| `With` | resource access |
| `Await` | async runtime |
| `Yield` | generators |
| `Exec` | arbitrary execution |
| `Eval` | arbitrary execution |

Dynamic imports are forbidden.

Undeclared identifiers are forbidden.

---

## 8. Determinism Guarantees

Eigen-Lang compilation MUST be deterministic.

Identical:

- source,
- compiler version,
- settings,
- target config,
- optimization config,
- seed,

MUST produce byte-identical AQO output.

This includes:

- operation ordering,
- parameter ordering,
- metadata ordering,
- checksum generation,
- AQO serialization.

---

## 9. Resource Limits

The compiler MUST enforce strict limits.

### 9.1 Required Limits

| **Limit** | **Required** |
|----------|----------|
| Maximum source size | 262144 bytes |
| Maximum AST depth | 200 |
| Maximum operation count | dynamic executionimplementation-defined |
| Maximum symbol length | implementation-defined |
| Maximum import count | bounded |

---

## 10. Error Model

Validation failures return structured deterministic errors.

### 10.1 Error Envelope

```json
{
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "Eigen-Lang validation failed",
    "details": [
      {
        "field": "function",
        "message": "Missing @hybrid_program entrypoint"
      }
    ]
  }
}
```

---

### 10.2 Stable Error Semantics

Errors MUST be:

- deterministic,
- reproducible,
- stable within MAJOR versions.

The same invalid input MUST always produce the same error class.

---

## 11. Standard Library

Only the official Eigen-Lang standard library is supported.

---

## 12. Decorators

### 12.1 `@hybrid_program`

Mandatory entrypoint decorator.

Example:

```python
@hybrid_program(
    compiler="eigen",
    target="simulator",
    shots=1024,
    optimization_level=2,
    seed=42
)
```

#### Required Semantics

Decorator arguments form part of the canonical `JobSpec`.

Supported fields include:

| **Field** | **Type** |
|----------|----------|
| `compiler` | string |
| `target` | string |
| `shots` | integer |
| `optimization_level` | integer |
| `seed` | integer |
| `noise_model` | string |
| `metadata` | dict |

Unknown fields MAY be rejected.

---

### 12.2 Additional Decorators

Supported auxiliary decorators:

| **Decorator** | **Purpose** |
|----------|----------|
| `@quantum_circuit` | static circuit template |
| `@ansatz` | parameterized ansatz |
| `@cost_function` | optimization target |
| `@benchmark` | benchmark specification |

---

## 13. Standard Types

### 13.1 `Param`

```python
Param(name, initial_value)
```

Defines symbolic parameters.

---

### 13.2 `Observable`

Defines measurement observables.

Example:

```python
Observable(Z=0, X=1)
```

---

### 13.3 Registers

```python
QubitRegister(n)
ClassicalRegister(n)
```

---

## 14. Quantum Operations

### 14.1 Mandatory Gate Set

The following gates MUST be supported:

| **Gate** | **AQO Opcode** |
|----------|----------|
| `rx` | `RX` |
| `ry` | `RY` |
| `rz` | `RZ` |
| `cx` | `CX` |

---

### 14.2 Additional Supported Gates

| **Gate** |
|----------|
| `h` |
| `x` |
| `y` |
| `z` | 
| `cz` | 
| `swap` | 
| `ccx` | 

Support MAY depend on backend capability.

Unsupported gates MUST fail deterministically.

---

## 15. Hybrid Runtime Functions

### 15.1 `ExpectationValue`

```python
ExpectationValue(observable=Observable(...))
```

Defines observable evaluation.

---

### 15.2 `minimize`

```python
minimize(cost_fn, initial_params, method="COBYLA")
```

Defines classical optimization orchestration.

---

### 15.3 `load_dataset`

```python
load_dataset(source, format="parquet")
```

Dataset loading declaration.

Runtime execution remains sandbox-controlled.

---

## 16. AQO Mapping

Eigen-Lang compiles into AQO v1.0.

Normative AQO contract:

- `docs/reference/formats/aqo.md`

### 16.1 Gate Mapping

Example:

```python
rx(0, theta)
```

maps to:

```json
{
  "op": "RX",
  "q": [0],
  "params": {
    "theta": "theta"
  }
}
```

---

### 16.2 Measurement Mapping

Measurements compile into AQO `MEASURE` operations.

Measurement ordering MUST remain deterministic.

---

### 16.3 Metadata

Generated AQO metadata MUST include:

| **Field** | **Purpose** |
|----------|----------|
| `aqo_sha256` | canonical checksum |
| `compiler_version` | compiler reproducibility |
| `spec_version` | language version |
| `generated_at` | optional timestamp policy |
| `target` | backend target |

Timestamps MUST NOT affect deterministic AQO hashing.

---

## 17. Distributed Execution Metadata

Optional distributed metadata MAY include:

- topology hints,
- partition hints,
- distributed execution metadata,
- execution group identifiers.

All distributed metadata fields MUST include explicit version markers.

---

## 18. Conformance Suite

Eigen-Lang implementations MUST pass the conformance suite.

### 18.1 Golden Tests

Golden AQO fixtures validate:

- deterministic compilation,
- stable serialization,
- stable metadata,
- operation ordering.

---

### 18.2 Negative Tests

Negative fixtures validate:

0 forbidden AST rejection,
- invalid imports,
- invalid decorators,
- invalid parameters,
- invalid gates.

---

### 18.3 Deterministic Hash Validation

The same source MUST generate identical:

- AQO JSON,
- protobuf AQO,
- hashes,
- metadata.

---

## 19. Security Requirements

Eigen-Lang MUST be treated as executable declarative input.

Required guarantees:

- strict AST validation,
- sandbox-safe parsing,
- deterministic compilation,
- bounded resource consumption,
- no host execution,
- no filesystem access,
- no network access,
- no subprocess execution.

Compiler crashes MUST NOT expose host internals.

---

## 20. Observability Requirements

Compiler telemetry SHOULD include:

| **Signal** | **Purpose** |
|----------|----------|
| compile latency | performance |
| validation failures | diagnostics |
| AQO hash | reproducibility |
| compiler version | compatibility |
| spec version | auditing |

Full source logging SHOULD be disabled by default.

---

## 21. Versioning Policy

Eigen-Lang uses SemVer.

### 21.1 MAJOR

Breaking changes:

- syntax removal,
- AST changes,
- semantic changes,
- AQO mapping changes.

---

### 21.2 MINOR

Backward-compatible additions:

- optional decorators,
- optional metadata,
- additional gates,
- additional observables.

---

### 21.3 PATCH

Clarifications and bug fixes only.

---

## 22. Compatibility Guarantees

Eigen OS guarantees:

- stable language semantics within MAJOR versions,
- deterministic compilation,
- stable AQO mapping,
- stable validation semantics,
- reproducible compilation behavior.

---

## 23. Migration Rules

New features MUST:

- include RFC approval,
- include conformance tests,
- include golden fixtures,
- preserve backward compatibility within MAJOR version.

Deprecated features MUST remain supported for at least one MINOR release unless a security exception applies.
