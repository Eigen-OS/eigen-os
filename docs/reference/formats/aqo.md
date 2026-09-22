# AQO (Abstract Quantum Operations) v1.0

## 1. Overview

**AQO (Abstract Quantum Operations)** is the canonical intermediate representation between the Eigen-Lang compiler and the runtime execution layer.

AQO is the contract boundary for:

- deterministic compilation,
- replayable execution,
- runtime validation,
- backend-agnostic transport,
- artifact persistence,
- scheduling and observability handoff.

AQO is intentionally strict: it must be stable enough to hash, replay, compare, and validate before execution.

The canonical AQO contract version for this document is `1.0.0`. Breaking changes require a major version bump.

AQO JSON is the source-of-truth encoding for fixtures, hashing, and contract tests. Transport layers may use alternative encodings, but they must preserve the canonical semantics.

---

## 2. Design goals

AQO v1.0 is designed to guarantee:

- deterministic parsing,
- deterministic serialization,
- stable hashing,
- backend portability,
- replayability,
- compatibility validation before execution,
- strict runtime validation,
- auditability and observability.

AQO does not contain credentials, runtime secrets, or authorization tokens.

AQO must always be treated as untrusted executable input.

---

## 3. Top-level structure

An AQO document is a JSON object.

### 3.1 Required fields

| Field | Type | Description |
|---|---|---|
| `version` | string | AQO contract version |
| `qubits` | integer | Total number of logical qubits |
| `operations` | array | Ordered operation list |

### 3.2 Optional fields

| Field | Type | Description |
|---|---|---|
| `parameters` | object | Symbolic parameter declarations |
| `metadata` | object | Non-semantic compiler/runtime metadata |
| `checksums` | object | Integrity and provenance hashes |
| `topology` | object | Distributed / backend topology hints |
| `annotations` | object | Compiler and runtime annotations |

Unknown top-level fields must be rejected unless a future version explicitly allows them.

---

## 4. Canonical AQO JSON example

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

## 5. Canonical serialization rules

Canonical AQO JSON serialization is required for:

- hashing,
- replay,
- signatures,
- idempotency,
- fixture generation,
- caching,
- audit logs.

Rules:

1. UTF-8 encoding only.
2. Object keys sorted lexicographically.
3. No insignificant whitespace.
4. Arrays preserve order.
5. Numbers must be serialized deterministically.
6. No trailing commas.
7. Duplicate keys are forbidden.
8. Floating-point values must be finite.
9. NaN and Infinity are forbidden.

Example canonical payload:

```json
{"operations":[{"op":"H","q":[0]}],"qubits":1,"version":"1.0.0"}
```

---

## 6. Operation format

Each operation is a JSON object.

### 6.1 Common fields

| Field | Type | Required | Description |
|---|---|---|---|
| `op` | string | yes | Opcode |
| `q` | integer[] | yes | Logical qubit indices |
| `c` | integer[] | conditional | Classical bit indices |
| `params` | object | optional | Operation parameters |
| `basis` | string | optional | Measurement basis |

### 6.2 Supported opcode set

The canonical opcode set includes:

- `RX`, `RY`, `RZ`
- `CX`, `CZ`, `SWAP`
- `CCX`, `CCZ`
- `X`, `Y`, `Z`, `H`, `S`, `T`
- `MEASURE`
- `RESET`

### 6.3 Parameter rules

Parameters are supplied through the `params` object.

Supported value types:

- integer,
- float,
- string symbolic identifier.

Validation rules:

- `RX` / `RY` / `RZ` must include `theta`
- non-parameterized gates must not include `params`
- `MEASURE` may include `basis`
- unknown parameter keys must be rejected
- unsupported symbolic expressions must be rejected

AQO forbids arbitrary expressions, inline functions, dynamic evaluation, and runtime scripting.

---

## 7. Measurement semantics

AQO uses deterministic classical bit indexing.

For `MEASURE`:

- `q` must contain at least one qubit,
- `c` must match the number of measured qubits,
- `basis`, when present, must be one of `X`, `Y`, or `Z`.

Canonical bit ordering is preserved across backends and runtimes.

---

## 8. Validation invariants

AQO validation must occur before execution.

### 8.1 Structural validation

The compiler/runtime must validate:

- valid JSON,
- required fields,
- correct field types,
- deterministic canonicalization,
- supported AQO version.

### 8.2 Semantic validation

The compiler/runtime must validate:

- qubit indices are within range,
- operation arity matches the opcode definition,
- required parameters exist,
- unsupported parameters are rejected,
- measurement constraints are satisfied,
- unsupported opcodes are rejected,
- invalid symbolic identifiers are rejected.

### 8.3 Resource validation

The runtime/backend may additionally validate:

- backend topology compatibility,
- gate support,
- qubit capacity,
- calibration compatibility,
- execution quotas,
- reservation ownership.

---

## 9. Determinism requirements

AQO v1.0 is deterministic by contract.

The following must be deterministic:

- parsing,
- canonical serialization,
- hashing,
- opcode interpretation,
- parameter interpretation,
- classical bit ordering,
- validation behavior.

Execution outcomes may still be probabilistic because quantum execution itself is probabilistic.

---

## 10. Compatibility and versioning

### 10.1 Version policy

- `1.x` must remain backward-compatible within the same major version.
- `2.0.0` or later may introduce breaking changes.
- breaking AQO changes require a version bump and explicit migration guidance.

### 10.2 Forward-compatible extensions

A future compiler may add new semantics only through documented optional fields or a new contract version.

Implementations must reject unknown top-level fields unless the version explicitly allows them.

### 10.3 Migration rules

When migrating from older AQO shapes:

- preserve canonical semantics,
- rewrite to the current contract before persistence when possible,
- keep compatibility notes in docs and fixtures,
- never silently reinterpret unknown fields as authoritative.

---

## 11. Error model

AQO-related failures map to platform errors as follows:

| Condition | Status |
|---|---|
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

All validation failures must occur before execution begins.

---

## 12. Security requirements

AQO does not contain secrets by design, but it must be treated as executable input.

Required guarantees:

- strict schema validation,
- bounds checking,
- deterministic parsing,
- opcode allow-list enforcement,
- parameter validation,
- payload size limits,
- recursion/depth limits,
- rejection of malformed JSON,
- rejection of duplicate keys.

AQO payloads must never be executed without validation.

---

## 13. Observability

Recommended observability fields:

| Field | Description |
|---|---|
| `aqo_hash` | canonical payload hash |
| `aqo_version` | AQO contract version |
| `aqo_size_bytes` | serialized payload size |
| `operation_count` | total operations |
| `qubit_count` | logical qubits |
| `transport_format` | JSON / transport encoding |

Observability values must remain bounded and must not leak secrets or unbounded identifiers.

Compiler pass traces, rewrite summaries, and lowering diagnostics belong in compiler metadata rather than as new AQO top-level fields.
