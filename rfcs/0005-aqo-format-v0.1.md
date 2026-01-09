# RFC 0005: AQO (Abstract Quantum Operations) format v0.1

- **Status:** Discussion
- **Authors:** NYankovich
- **Created:** 2026-01-08
- **Target milestone:** Phase 0 (MVP)
- **Tracking issue:** (TBD)
- **Supersedes / Related:** 0004,0007,0006

## Summary

Defines the minimal intermediate representation (IR) used between compiler and kernel, and as an artifact in QFS.

## Motivation

AQO is the bridge that decouples Eigen-Lang from concrete backends. It must be stable enough to persist and to feed optimizers and drivers.

## Goals

- Define a minimal operation set for VQE/QAOA-style MVP.
- Define a deterministic serialization (JSON + protobuf bytes).
- Provide room for future control-flow and error mitigation ops.

## Non-Goals

- Full OpenQASM3 parity.
- Vendor-specific pulse-level control (Phase 2+).

## Guide-level explanation

AQO is a list of operations with explicit qubit references and parameters.
MVP supports:
- single-qubit rotations: RX/RY/RZ
- entangling: CX
- measurement: MEASURE
- reset: RESET (optional)
- classical parameters: symbolic names resolved at runtime

AQO artifacts are stored in QFS under `circuit_fs/<job_id>/compiled.aqo.{json|pb}`.

## Reference-level design

### Interfaces / APIs

Compiler returns `CompileCircuitResponse` containing:
- `ir_format` enum (AQO_JSON, AQO_PROTO, QASM3_TEXT, BACKEND_NATIVE)
- `ir_bytes`
- `metadata` map
Kernel passes `CircuitPayload` to driver-manager (RFC 0006).

### Data model

### AQO JSON (normative for MVP)

```json
{
  "version": "0.1",
  "qubits": 4,
  "operations": [
    {"op": "RZ", "q": [0], "params": {"theta": "p0"}},
    {"op": "RY", "q": [0], "params": {"theta": 1.570796}},
    {"op": "CX", "q": [0,1]},
    {"op": "MEASURE", "q": [0,1], "c": [0,1]}
  ]
}
```

Rules:
- `q` are integer indices into a logical register.
- Params may be numeric or symbolic strings.
- `MEASURE` may include `basis` (default Z) as optional.


### Error model

Invalid opcodes/arity are compiler errors (INVALID_ARGUMENT). Drivers may reject unsupported payload formats (UNIMPLEMENTED).

### Security & privacy

AQO contains no secrets. Treat it as executable artifact; validate before running.

### Observability

Compiler and kernel log AQO hash and size. Do not log full AQO by default (can be large).

### Performance notes

Prefer protobuf for large circuits; JSON is canonical and human-debuggable.

## Testing plan

Round-trip tests JSON↔protobuf; conformance tests per op (arity, param rules).

## Rollout / Migration

MVP fixes v0.1 op set. Extensions require minor bump (0.2) with backwards compatibility.

## Alternatives considered

- Use OpenQASM3 as only IR (rejected: need higher-level IR).
- Use existing IRs (MLIR) in MVP (postponed).

## Open questions

- Do we need classical control-flow ops in v0.2 for mid-circuit measurement?
- How to represent observables/expectation values cleanly?
