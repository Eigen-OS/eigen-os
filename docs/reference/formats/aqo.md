# AQO v0.1 — Abstract Quantum Operations Format (MVP baseline)

> Status snapshot (as of 2026-05-09): this spec is synchronized with current architecture docs and repository behavior. Implemented behavior is marked explicitly; target-state gaps are listed as `TODO`.

## 1) Summary

AQO (Abstract Quantum Operations) is the compiler/runtime IR exchanged between `eigen-compiler`, `eigen-kernel (QRTX)`, and `driver-manager`, and persisted in QFS artifacts.

**Implemented now**
- Deterministic AQO v0.1 JSON emission is the canonical MVP path.
- AQO is transported via internal gRPC `CircuitPayload` (`format` + `bytes`).
- Driver-manager consumes AQO JSON and normalizes execution output to counts + metadata.

**TODO / not fully implemented yet**
- Full production parity for AQO protobuf (`AQO_PROTO`) across all runtime paths.
- Stable contract for advanced AQO extensions (control flow, observables, noise ops).
- Unified compatibility matrix for every backend/driver vs AQO features.

## 2) Purpose and scope

AQO decouples Eigen‑Lang from hardware-specific circuit formats and enables:
- deterministic compilation artifacts,
- optimizer/analysis passes,
- backend-agnostic execution,
- reproducible persistence in QFS.

### In scope (MVP)
- Gate-level circuit IR for supported deterministic compiler subset.
- Symbolic/numeric parameters.
- Measurement mapping to classical bits.
- Validation and compatibility invariants for runtime consumption.

### Out of scope (MVP)
- Full OpenQASM3 feature parity.
- Pulse-level or timing-level vendor controls.
- General-purpose classical IR.

## 3) Runtime interfaces that carry AQO

### 3.1 Compiler output contract
Compiler returns compile response with:
- `ir_format` enum (`AQO_JSON`, `AQO_PROTO`, `QASM3_TEXT`, `BACKEND_NATIVE`),
- `ir_bytes`,
- metadata map (including AQO hash-related fields where enabled).

### 3.2 Kernel → Driver Manager contract
Kernel sends `CircuitPayload { format, bytes }` to Driver Manager (internal gRPC).

### 3.3 Persistence contract (QFS)
AQO is persisted as compiled artifact under the job artifact directory. Current docs mention both naming variants in circulation:
- `compiled.aqo.json` / `compiled.aqo.pb` (pipeline-oriented naming),
- `circuit.aqo.json` / `circuit.aqo.pb` (format-layout naming).

`TODO`: finalize one canonical naming scheme (and migration note) across all runtime, API, and format docs.

## 4) AQO JSON data model (normative for MVP)

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

### 4.1 Top-level fields
1. `version` — must be `"0.1"` for MVP.
2. `qubits` — total logical qubits (`int >= 1`).
3. `operations` — ordered operation list.

### 4.2 Operation fields
- `op` (`string`) — opcode.
- `q` (`int[]`) — zero-based qubit indices.
- `c` (`int[]`, optional) — classical indices (used by `MEASURE`).
- `params` (`map<string, number|string>`, optional) — gate parameters.

### 4.3 MVP opcode set
- Single-qubit rotations: `RX`, `RY`, `RZ`
- Two-qubit entangling: `CX`
- Measurement: `MEASURE`
- Reset (optional support): `RESET`

### 4.4 Parameter rules
- Numeric values: integer/float.
- Symbolic values: identifier pattern `[a-zA-Z_][a-zA-Z0-9_]*`.
- `RX/RY/RZ` require `theta`.

### 4.5 Measurement rule
- `MEASURE` supports `basis` in `params` (`X|Y|Z`), default is `Z`.
- `len(q)` must equal `len(c)`.

## 5) Canonical bitstring ordering for counts

When execution returns `counts: map<bitstring,int64>`, canonical encoding is:
- output bitstring order: `c[n-1] ... c[1] c[0]`,
- `c[0]` is rightmost (least-significant classical bit).

Example: `q0->c0=1`, `q1->c1=0` yields key `"01"`.

This ordering is the normalization target for Driver Manager independent of backend native conventions.

## 6) Validation invariants (MVP conformance)

1. **Qubit bounds**: every `q[i] < qubits`.
2. **Opcode arity**:
   - `RX/RY/RZ/RESET`: exactly 1 qubit,
   - `CX`: exactly 2 qubits,
   - `MEASURE`: 1..N qubits + same number of classical bits.
3. **Classical write uniqueness**: no duplicate `c` destinations within one measurement op.
4. **Parameter legality**:
   - `RX/RY/RZ`: require `theta`,
   - `CX/RESET`: no params,
   - `MEASURE`: only optional basis semantics for MVP.
5. **Version gating**: unsupported `version` → reject as `INVALID_ARGUMENT`.

## 7) Error model and status mapping

- Malformed AQO JSON/protobuf: `INVALID_ARGUMENT`.
- Unknown opcode / invalid arity: `INVALID_ARGUMENT`.
- Unsupported payload format in runtime path: `UNIMPLEMENTED`.
- Backend/runtime incompatibility discovered at execution stage: `FAILED_PRECONDITION` or `UNAVAILABLE` depending on root cause.

## 8) Security, observability, and performance

### Security
AQO does not carry secrets by design, but must be treated as executable input:
- strict validation before execution,
- no implicit trust of external AQO refs.

### Observability
- log AQO hash and payload size,
- avoid full AQO payload logging by default,
- include AQO-related identifiers in job metadata for traceability.

### Performance
- JSON is canonical and debug-friendly baseline.
- `AQO_PROTO` is intended for large circuits and wire efficiency.
- Driver-manager may cache parsed AQO by content hash.

## 9) Current gaps to close

1. Define and publish one canonical QFS filename convention for AQO artifacts.
2. Lock protobuf schema details and enforce JSON↔protobuf conformance tests in CI.
3. Specify forward-compatibility behavior for unknown fields consistently across parser implementations.
4. Document backend capability flags tied to AQO features (`RESET`, non-Z basis measurement, future ops).
5. Extend conformance pack with backend-normalization fixtures for bit ordering.

## 10) Test expectations

- Round-trip tests: JSON ↔ protobuf (where protobuf path is enabled).
- Determinism/golden tests: stable AQO bytes and hash for identical inputs.
- Validation tests: bounds/arity/parameter checks.
- E2E tests: compiler → kernel → driver-manager with normalized counts.

## 11) References

- RFC 0005: AQO format contract.
- RFC 0006: Driver API and `CircuitPayload` transport.
- RFC 0007: Kernel/QFS runtime artifact lifecycle.
- Architecture docs:
  - `docs/architecture/overview.md`
  - `docs/architecture/contract-map.md`
  - `docs/architecture/data-flow.md`
