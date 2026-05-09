# Mapping Eigen‑Lang → AQO (MVP v0.1)

Eigen‑Lang compiles to **AQO** (Abstract Quantum Operations), but in the current repository state this mapping is intentionally **narrow, deterministic and safety-first**.

> Status snapshot aligned with architecture refresh: 2026-05-09.

## 1) What is implemented now (contract baseline)

The production baseline for `eigen-compiler` in MVP is:

- parse source via Python `ast` without executing user code;
- require exactly one `@hybrid_program` entrypoint;
- reject dynamic control flow and non-allowlisted constructs;
- deterministically lower the supported subset into canonical AQO JSON bytes.

This corresponds to the architecture/component docs where compiler behavior is explicitly documented as AST-only deterministic AQO lowering.

## 2) Canonical AQO payload in MVP

- **Canonical interchange format**: AQO JSON (`AQO_JSON`).
- **Operation subset guaranteed today**: `RX`, `RY`, `RZ`, `CX`, terminal `MEASURE`.
- **Determinism**: identical input + options must produce byte-stable AQO JSON (required for conformance and hashing workflows).

Reference format contract: `docs/reference/formats/aqo.md`.

## 3) Concrete mapping rules (current implementation)

### 3.1 Entrypoint / program shape

- Exactly one function decorated with `@hybrid_program` is required.
- If zero or more than one are found, compilation fails validation (`INVALID_ARGUMENT` at RPC layer).

### 3.2 Parameters

- `Param("name")` assignment patterns are recognized and mapped to symbolic AQO parameters (`"theta": "name"`) where used by supported gate calls.

### 3.3 Gates and measurement

The implemented lowering subset is:

- `rx(theta=...)` → `{"op":"RX","q":[...],"params":{"theta":...}}`
- `ry(theta=...)` → `{"op":"RY","q":[...],"params":{"theta":...}}`
- `rz(theta=...)` → `{"op":"RZ","q":[...],"params":{"theta":...}}`
- `cx(...)` → `{"op":"CX","q":[control,target]}`
- terminal measurement is appended as `{"op":"MEASURE", ...}` over inferred qubit range.

### 3.4 Hybrid markers (metadata-level)

`minimize(...)` and `ExpectationValue(...)` are currently detected primarily as hybrid-intent markers (metadata/planning hints), not as a complete semantic expansion into AQO-native optimization/observable IR.

## 4) System state fixation: what is missing now

To keep docs honest against implementation, the following items are still **not implemented end-to-end** in the compiler mapping path:

1. Full Eigen‑Lang surface → AQO semantic coverage (typed/frontend-complete lowering).
2. Native/complete observable mapping for `ExpectationValue(...)` beyond MVP marker behavior.
3. Production hybrid-loop lowering for `minimize(...)` with full optimizer semantics in compiler output contract.
4. Advanced AQO output variants and optimization passes (`OptimizeCircuit` currently `UNIMPLEMENTED`).
5. Broader qubit addressing/routing-aware lowering (current subset is intentionally constrained).

## 5) Cross-file consistency notes

During architecture refresh, related docs/components should be read together when changing this mapping page:

- `docs/architecture/components/compiler.md` — source of truth for implemented compiler responsibilities and TODO gaps.
- `docs/reference/eigen-lang/allowed-subset.md` and `conformance.md` — language envelope + deterministic conformance obligations.
- `docs/reference/formats/aqo.md` — AQO format contract and validation invariants.

If behavior changes in code, update these documents atomically to avoid contract drift.
