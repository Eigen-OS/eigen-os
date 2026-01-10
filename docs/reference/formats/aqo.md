# AQO v0.1 — Abstract Quantum Operations Format (MVP)

## Summary

Defines the minimal intermediate representation (IR) used between compiler and kernel, and as an artifact in QFS. AQO bridges Eigen‑Lang and concrete backends while enabling optimization and persistence.

## Motivation

AQO decouples Eigen‑Lang from hardware‑specific implementations. It must be stable enough to persist in QFS, feed optimization passes, and be executable by multiple backends via driver plugins.

## Goals

- Minimal operation set for VQE/QAOA‑style MVP

- Deterministic serialization (JSON canonical + protobuf)

- Room for future control‑flow and error‑mitigation operations

- Clean mapping to QASM3 and vendor‑native formats

## Non‑Goals

- Full OpenQASM3 parity

- Vendor‑specific pulse‑level control (Phase 2+)

- Classical computation IR (except simple parameters)

## Guide‑level explanation

AQO represents a quantum circuit as a list of operations with explicit qubit references and parameters. MVP supports:

- **Single‑qubit rotations**: `RX`, `RY`, `RZ`

- **Entangling**: `CX`

- **Measurement**: `MEASURE`

- **Reset**: `RESET` (optional)

- **Classical parameters**: Symbolic names resolved at runtime

AQO artifacts are stored in QFS under `circuit_fs/<job_id>/compiled.aqo.{json|pb}`.

## Reference‑level design

### Interfaces / APIs

Compiler returns `CompileCircuitResponse` containing:

- `ir_format` enum (`AQO_JSON`, `AQO_PROTO`, `QASM3_TEXT`, `BACKEND_NATIVE`)

- `ir_bytes`

- `metadata` map

Kernel passes `CircuitPayload` (format + bytes) to driver‑manager (RFC 0006).

### Data model

**AQO JSON (normative for MVP)**
```json
{
  "version": "0.1",
  "qubits": 4,
  "operations": [
    {"op": "RZ", "q": [0], "params": {"theta": "p0"}},
    {"op": "RY", "q": [0], "params": {"theta": 1.570796}},
    {"op": "CX", "q": [0, 1]},
    {"op": "MEASURE", "q": [0, 1], "c": [0, 1]}
  ]
}
```

**Rules**

1. **Versioning**: Top‑level `version` must be "`0.1`" for MVP

2. **Qubits**: `qubits` is total logical qubits in register

3. **Operations**: `operations` is an ordered list

4. **Qubit indices**: `q` array contains integer indices (0‑based)

5. **Classical bits**: `c` array for measurement results (optional)

6. **Parameters**:

    - Numeric: `float` or integer

    - Symbolic: string matching `[a-zA-Z_][a-zA-Z0-9_]*`

7. **Measurement**: Optional `basis` field ("`X`", "`Y`", "`Z`", default "`Z`")

8. **Reset**: `RESET` operation takes qubit indices, no parameters

**AQO Protobuf (optional)**
```proto
message AqoCircuit {
  string version = 1;
  int32 qubits = 2;
  repeated Operation operations = 3;
}

message Operation {
  string op = 1;  // "RX", "RY", "RZ", "CX", "MEASURE", "RESET"
  repeated int32 q = 2;  // qubit indices
  repeated int32 c = 3;  // classical bit indices (for MEASURE)
  map<string, string> params = 4;  // param_name → string value
}
```

## Error model

- **Invalid opcodes/arity**: Compiler error (`INVALID_ARGUMENT`)

- **Unsupported format**: Driver returns `UNIMPLEMENTED`

- **Malformed JSON/Protobuf**: `INVALID_ARGUMENT` with location details

## Security & privacy

AQO contains no secrets. Treat as executable artifact; validate before running.

## Observability

- Compiler/kernel log AQO hash and size

- Do **not** log full AQO by default (can be large)

- Include `aqo_hash` in job metadata

## Performance notes

- Prefer protobuf for large circuits (>1000 operations)

- JSON is canonical and human‑debuggable for MVP

- Driver‑manager should cache parsed circuits when possible

## Validation rules

1. **Qubit bounds**: All `q[i]` must be `< qubits`

2. **Classical bits**: `c[i]` must be unique per measurement (no duplicate writes)

3. **Gate arity**:

    - `RX/RY/RZ/RESET`: exactly 1 qubit

    - `CX`: exactly 2 qubits

    - `MEASURE`: 1‑N qubits, same number of classical bits

4. **Parameters**:

    - `RX/RY/RZ`: require "`theta`" parameter

    - `CX/RESET`: no parameters

    - `MEASURE`: optional "`basis`" parameter

## Testing plan

- **Round‑trip tests**: JSON ↔ protobuf conversion

- **Conformance tests**: Per‑operation validation rules

- **Golden tests**: Source → AQO JSON hash stability

- **Integration**: Compiler → Kernel → Driver‑manager execution

## Rollout / Migration

- MVP fixes v0.1 op set

- Extensions require minor version bump (0.2) with backward compatibility

- Unknown fields in JSON must be ignored (forward compatibility)

## Alternatives considered

- **OpenQASM3 as only IR**: Rejected — need higher‑level IR for optimization passes

- **Existing IRs (MLIR)**: Postponed — too complex for MVP

- **Vendor‑specific formats only**: Rejected — breaks hardware abstraction

## Open questions

- **Control‑flow ops**: Should classical `if/for` be in v0.2?

- **Observables**: How to represent expectation values cleanly?

- **Noise operations**: When to add `DEPOLARIZE`, `AMPLITUDE_DAMPING`?

---

**References:**

    RFC 0004: Public gRPC API (CompilationService)

    RFC 0006: QDriver API (CircuitPayload format)

    RFC 0007: QRTX MVP (QFS storage paths)