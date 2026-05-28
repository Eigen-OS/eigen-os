# AQO (Abstract Quantum Operations) v1.0

## 1. Overview

**AQO (Abstract Quantum Operations)** is the canonical intermediate representation (IR) between the Eigen-Lang compiler and the runtime execution layer (Kernel, Scheduler, Driver Manager, and device adapters).

AQO provides:

- deterministic and hardware-agnostic quantum program representation,
- stable replay semantics,
- transport-safe execution payloads,
- backend-independent normalization,
- reproducible compilation and scheduling behavior.

AQO is an executable contract artifact and is part of the platform compatibility surface.

The canonical AQO specification version for this document is:

- AQO Contract Version: `1.0.0`

Breaking AQO changes require a MAJOR version bump.

The AQO schema is transport-independent and may be encoded as:

- canonical JSON (`AQO_JSON`) — normative/debug format,
- protobuf/binary (`AQO_PROTO`) — optimized runtime transport format.

JSON AQO remains the source-of-truth representation for replay, hashing, fixtures, and contract tests.

---

## 2. Design Goals

AQO v1.0 is designed to guarantee:

- deterministic parsing,
- deterministic serialization,
- stable hashing,
- backend portability,
- replayability,
- compatibility validation before execution,
- strict runtime validation,
- auditability and observability.

AQO intentionally does not contain:

- credentials,
- runtime secrets,
- authorization tokens,
- tenant-private execution state.

However, AQO MUST always be treated as untrusted executable input.

---

## 3. Top-Level Document Structure

An AQO document is a JSON object.

### 3.1 Required Fields

| **Field** | **Type** | **Description** |
|-------------|------------|-----------|
| `version` | string | AQO contract version |
| `qubits` | integer | Total number of logical qubits |
| `operations` | array | Ordered operation list |

---

### 3.2 Optional Fields

| **Field** | **Type** | **Description** |
|-------------|------------|-----------|
| `metadata` | object | Non-semantic metadata |
| `parameters` | object | Symbolic parameter declarations |
| `checksums` | object | Integrity hashes |
| `topology` | object | Optional topology constraints |
| `annotations` | object | Compiler/runtime annotations |

Unknown top-level fields MUST be rejected unless explicitly allowed by the contract version.

---

## 4. Canonical AQO JSON Example

```json
{
  "version": "1.0.0",
  "qubits": 2,
  "operations": [
    {
      "op": "H",
      "q": [0]
    },
    {
      "op": "CX",
      "q": [0, 1]
    },
    {
      "op": "MEASURE",
      "q": [0, 1],
      "c": [0, 1]
    }
  ]
}
```

---

## 5. Canonical Serialization Rules

Canonical AQO JSON serialization is REQUIRED for:

- hashing,
- replay,
- signatures,
- idempotency,
- fixture generation,
- caching,
- audit logs.

Canonicalization rules:

1. UTF-8 encoding only.
2. Object keys sorted lexicographically.
3. No insignificant whitespace.
4. Arrays preserve original order.
5. Numbers serialized deterministically.
6. No trailing commas.
7. Duplicate keys are forbidden.
8. Floating-point values MUST be finite.
9. NaN and Infinity are forbidden.

Example canonical payload:

```json
{"operations":[{"op":"H","q":[0]}],"qubits":1,"version":"1.0.0"}
```

---

## 6. Operation Format

Each operation is a JSON object.

### 6.1 Common Fields

| **Field** | **Type** | **Required** | **Description** |
|-----------|-----------|-----------|-----------|
| `op` | string | yes | Opcode |
| `q` | integer[] | yes | Logical qubit indices |
| `c` | integer[] | conditional | Classical bit indices |
| `params` | object | optional | Operation parameters |
| `metadata` | object | optional | Non-semantic annotations |

---

### 6.2 Example

```json
{
  "op": "RZ",
  "q": [0],
  "params": {
    "theta": "p0"
  }
}
```

---

## 7. Opcode Set (v1.0)

### 7.1 Mandatory Baseline Operations

The following operations are REQUIRED for all AQO v1.0 compliant runtimes:

| **Opcode** | **Arity** |
|----------|----------|
| `RX` | 1 |
| `RY` | 1 |
| `RZ` | 1 |
| `CX` | 2 |
| `MEASURE` | 1..N |
| `RESET` | 1..N |

---

### 7.2 Standard Single-Qubit Gates

| **Opcode** | **Parameters** |
|----------|----------|
| `X` | none |
| `Y` | none |
| `Z` | none |
| `H` | none |
| `S` | none |
| `T` | none |

---

### 7.3 Parameterized Rotations

| **Opcode** | **Required Parameters** |
|----------|----------|
| `RX` | theta |
| `RY` | theta |
| `RZ` | theta |

---

### 7.4 Two-Qubit Gates

| **Opcode** |
|----------|
| `CX` |
| `CZ` |
| `SWAP` |

---

### 7.5 Multi-Qubit Gates

| **Opcode** |
|----------|
| `CCX` |
| `CCZ` |

---

## 7.6 Measurement

| **Opcode** |
|----------|
| `MEASURE` |

Default measurement basis: `Z`

Optional basis override:

```json
{
  "basis": "X"
}
```

Allowed values:

- `"X"`
- `"Y"`
- `"Z"`

---

### 7.7 Reset

| **Opcode** |
|----------|
| `RESET` |

Resets target qubits into: `|0⟩`

---

## 8. Parameter Rules

Parameters are supplied via the `params` object.

Supported value types:

| **Type** | **Allowed** |
|----------|----------|
| integer | yes |
| float | yes |
| string symbolic identifier | yes |

---

### 8.1 Examples

Numeric parameter:

```json
{
  "theta": 3.1415926535
}
```

Symbolic parameter:

```json
{
  "theta": "p0"
}
```

---

### 8.2 Validation Rules

| **Rule** | **Requirement** |
|----------|----------|
| `RX`/`RY`/`RZ` | MUST include `theta` |
| Non-parameterized gates | MUST NOT include parameters |
| `MEASURE` | only optional `basis` allowed |
| Unknown parameter keys | MUST be rejected |
| Unsupported symbolic expressions | MUST be rejected |

AQO v1.0 intentionally forbids:

- arbitrary expressions,
- inline functions,
- dynamic evaluation,
- runtime scripting.

---

## 9. Classical Bit Semantics

AQO uses deterministic classical bit indexing.

### 9.1 Measurement Invariant

```text
len(q) == len(c)
```

is REQUIRED for `MEASURE`.

---

### 9.2 Canonical Bit Ordering

Execution results use canonical bit ordering:

| **Bit** | **Meaning** |
|----------|----------|
| `c[0]` | least significant bit (rightmost) |
| `c[n-1]` | most significant bit (leftmost) |

Example:

```text
q0 -> c0 = 1
q1 -> c1 = 0
```

Produces: `"01"`

This normalization is mandatory across all backends.

---

## 10. Validation Invariants

AQO validation MUST occur before compilation and execution.

### 10.1 Structural Validation

The runtime/compiler MUST validate:

- valid JSON,
- valid schema,
- required fields,
- correct field types,
- deterministic canonicalization,
- supported AQO version.

---

### 10.2 Semantic Validation

The runtime/compiler MUST validate:

- all qubit indices satisfy:

```text
0 <= q[i] < qubits
```

- operation arity matches opcode definition,
- required parameters exist,
- unsupported parameters are rejected,
- measurement constraints are satisfied,
- unsupported opcodes are rejected,
- invalid symbolic identifiers are rejected.

---

### 10.3 Resource Validation

The runtime/backend MAY additionally validate:

- backend topology compatibility,
- gate support,
- qubit capacity,
- calibration compatibility,
- execution quotas,
- reservation ownership.

---

## 11. Determinism Requirements

AQO v1.0 is deterministic by contract.

The following MUST be deterministic:

- parsing,
- canonical serialization,
- hashing,
- opcode interpretation,
- parameter interpretation,
- classical bit ordering,
- validation behavior.

AQO execution outcomes MAY still be probabilistic due to quantum execution semantics.

---

## 12. Transport Formats

### 12.1 AQO_JSON

Canonical JSON representation.

Required for:

- fixtures,
- debugging,
- replay,
- auditing,
- hashes,
- signatures.

---

### 12.2 AQO_PROTO

Binary/protobuf transport representation.

Intended for:

- internal service communication,
- high-throughput execution,
- reduced payload size.

`AQO_PROTO` MUST preserve semantic equivalence with canonical AQO JSON.

---

## 13. Error Model

AQO-related failures MUST map to standardized platform errors.

| **Condition** | **Status** |
|----------|----------|
| Invalid AQO JSON | `INVALID_ARGUMENT` |
| Invalid schema | `INVALID_ARGUMENT` |
| Unknown opcode | `INVALID_ARGUMENT` |
| Invalid arity | `INVALID_ARGUMENT` |
| Missing parameter | `INVALID_ARGUMENT` |
| Unsupported AQO version | `FAILED_PRECONDITION` |
| Unsupported transport format | `UNIMPLEMENTED` |
| Backend incompatibility | `FAILED_PRECONDITION` |
| Backend unavailable | `UNAVAILABLE` |
| Payload too large | `RESOURCE_EXHAUSTED` |
| Execution timeout | `DEADLINE_EXCEEDED` |

All validation failures MUST occur before execution begins.

---

## 14. Security Requirements

AQO does not contain secrets by design, but MUST be treated as executable input.

### 14.1 Required Security Guarantees

All AQO consumers MUST implement:

- strict schema validation,
- bounds checking,
- deterministic parsing,
- opcode allow-list enforcement,
- parameter validation,
- payload size limits,
- recursion/depth limits,
- rejection of malformed JSON,
- rejection of duplicate keys.

AQO payloads MUST NEVER be executed without validation.

---

### 14.2 Forbidden Behavior

Implementations MUST NOT:

- dynamically execute AQO as code,
- evaluate arbitrary expressions,
- allow embedded scripting,
- trust client-supplied metadata,
- bypass validation for internal callers.

---

## 15. Observability Requirements

Recommended observability fields:

| **Field** | **Description** |
|----------|----------|
| `aqo_hash` | canonical payload hash |
| `aqo_version` | AQO contract version |
| `aqo_size_bytes` | serialized payload size |
| `operation_count` | total operations |
| `qubit_count` | logical qubits |
| `transport_format` | JSON/PROTO |

---

### 15.1 Logging Rules

Recommended:

- log AQO checksum/hash,
- log payload size,
- log operation count,
- log validation failures,
- log backend compatibility failures.

Forbidden by default:

- full AQO payload logging,
- parameter dumps in production logs,
- raw payload persistence without retention policy.

---

## 16. Performance Considerations

### 16.1 Canonical JSON

AQO JSON remains the normative representation for:

- debugging,
- replay,
- fixtures,
- audit systems.

---

### 16.2 Binary Transport

`AQO_PROTO` is recommended for:

- large circuits,
- internal RPC traffic,
- high-throughput scheduling.

---

### 16.3 Caching

Driver/runtime implementations MAY cache:

- parsed AQO payloads,
- validated IR,
- compiled artifacts,
- topology checks,

using deterministic content hashes.

---

## 17. Compatibility and Versioning

AQO follows Semantic Versioning.

| **Change Type** | **Version Impact** |
|----------|----------|
| Breaking schema change | MAJOR |
| Backward-compatible extension | MINOR |
| Clarification/fix | PATCH |

---

### 17.1 Compatibility Rules

AQO v1.0 consumers:

- MUST reject unsupported MAJOR versions,
- MAY ignore explicitly allowed optional metadata fields,
- MUST preserve deterministic semantics.

---

## 18. Compliance Requirements

A compliant AQO v1.0 implementation MUST:

- support all mandatory baseline operations,
- implement canonical serialization,
- implement deterministic validation,
- implement required error mappings,
- preserve canonical bit ordering,
- reject invalid AQO payloads,
- support replay-safe hashing semantics.

Golden fixtures and replay tests SHOULD be used to ensure compatibility stability.
