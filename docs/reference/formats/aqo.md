# AQO (Abstract Quantum Operations) v1.0

**AQO** is the intermediate representation (IR) of a quantum algorithm between the Eigen-Lang compiler and the runtime layer (kernel/driver). AQO provides deterministic and hardware-agnostic transaction formatting. Version 1.0 defines the JSON document structure describing the device topology and the sequence of quantum operations, as well as the baseline logical operation set and validation rules.

- **Top-level JSON fields:**

An AQO document contains the mandatory fields:

- `version` — format version,

- `qubits` — number of logical qubits (`integer >= 1`),

- `operations` — ordered list of operations.

In version 1.0, the `version` constant may be incremented (for example, `"1.0"`), while preserving the principle of a fixed schema version for deterministic parsing. Additional compilation metadata and checksums may also be included (see the QFS section).

- **Operation format:**

Each operation is represented as a JSON object with the following fields (mandatory fields are marked in bold):

- `op` (`string`) — operation opcode (e.g. `"RX"`, `"CX"`, `"MEASURE"`).

- `q` (`int[]`) — target qubit indices (zero-based).

- `c` (`int[]`, optional) — classical bit indices (used for measurement operations).

- `params` (`object`) — parameter map (`name → value`) for parameterized operations.

Example (from v0.1):

```json
{
  "op": "RZ",
  "q": [0],
  "params": {
    "theta": "p0"
  }
}
```

The `params` field accepts numeric values (`int` / `float`) and symbolic identifiers. Version 1.0 may introduce additional parameter keys for new operations and runtime semantics.

---

## Opcode Set (v1.0)

In addition to the MVP (`v0.1`) operations `RX`, `RY`, `RZ`, and `CX`, version 1.0 introduces a broader set of commonly used quantum gates:

### Single-Qubit Gates

- `X`

- `Y`

- `Z`

- `H` (Hadamard)

- Optional phase gates:

  - `S`

  - `T`

### Parameterized Rotations

- `RX`

- `RY`

- `RZ`

These operations require the parameter:

- `theta`

### Two-Qubit Gates

- `CX`

- `CZ`

- `SWAP`

### Multi-Qubit Gates

- `CCX` (Toffoli)

- `CCZ`

### Measurement

- `MEASURE`

Measurement defaults to the Z basis. The optional parameter:

```json
{
  "basis": "X"
}
```

may specify basis `"X"`, `"Y"`, or `"Z"`.

### Reset

- `RESET`

Resets the specified qubit(s) into the `|0⟩` state.

---

The new opcode set extends the baseline IR while preserving MVP compatibility:

- `RX`

- `RY`

- `RZ`

- `CX`

- `MEASURE`

- `RESET`

remain mandatory baseline operations, while the additional operations are implementation-dependent extensions

---

## Parameter Rules

Operation parameters are passed via the `params` object.

Version 1.0 continues to support:

- numeric literals (`integer`, `float`)

- symbolic identifiers

Examples:

```json
{"theta": 3.14}
```

```json
{"theta": "p0"}
```

Future versions may support symbolic expressions and functions, but version 1.0 intentionally preserves MVP determinism constraints.

Validation rules:

- `RX`, `RY`, `RZ` require `theta`

- `X`, `Y`, `Z`, `H`, `CX`, `CZ`, `SWAP`, etc. do not accept parameters

- `MEASURE` only accepts the optional `basis` parameter

---

## Measurement Rules

The `MEASURE` operation must satisfy:

```text
len(q) == len(c)
```

By default, measurements are performed in the Z basis unless explicitly overridden via:

```json
{
  "basis": "X"
}
```

or

```json
{
  "basis": "Y"
}
```

Measured bits are written into the classical indices defined in `c`.

---

## Canonical Bit Ordering

Execution results (`counts`) use canonical bitstring ordering:

- `c[0]` is the least significant bit (rightmost)

- `c[n-1]` is the most significant bit (leftmost)

Example:

```text
q0 -> c0 = 1
q1 -> c1 = 0
```

produces:

`"01"`

This normalization guarantees backend-independent result formatting.

---

## Validation Invariants

AQO v1.0 must satisfy the following invariants:

- all qubit indices `q[i] < qubits`

- operation arity must match the opcode definition

- `MEASURE` requires equal numbers of quantum and classical indices

- required parameters must not be omitted

- unknown opcodes must be rejected

Invalid AQO payloads must fail compilation/execution with:

`INVALID_ARGUMENT`

---

## Error Model

| **Condition** | **Status** |
|-------------------|-------------------|
| Invalid AQO JSON/schema | `INVALID_ARGUMENT` |
| Unknown opcode | `INVALID_ARGUMENT` |
| Invalid operation arity | `INVALID_ARGUMENT` |
| Unsupported AQO transport format | `UNIMPLEMENTED` |
| Backend incompatibility | `FAILED_PRECONDITION` / `UNAVAILABLE` |

---

## Security and Observability

AQO does not contain secrets by design, but it must be treated as executable input.

Required runtime guarantees:

- strict schema validation before execution

- no implicit trust of external AQO payloads

- deterministic parsing and normalization

Recommended observability:

- log AQO checksum/hash

- log payload size

- avoid full AQO JSON logging by default

- include AQO identifiers in job metadata and tracing systems

---

## Performance Considerations

- JSON AQO remains the canonical debugging and development format.

- `AQO_PROTO` is preferred for large circuits due to lower transport overhead.

- Deterministic AQO JSON generation remains mandatory in version 1.0.

- Driver Manager implementations may cache parsed AQO payloads by content hash to accelerate repeated executions.
