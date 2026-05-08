# Eigen Compiler (current state snapshot)

## Responsibility

`eigen-compiler` currently implements an **MVP AST-only compiler** for Eigen-Lang (Python DSL subset) into AQO JSON.

Implemented now:
- Parse input with Python `ast.parse` (no user code execution).
- Validate safety/shape constraints:
  - exactly one `@hybrid_program` entrypoint,
  - forbidden imports/calls,
  - dynamic control-flow rejection,
  - AST node/depth resource limits.
- Lower supported gate subset to deterministic AQO v0.1 JSON (`RX`, `RY`, `RZ`, `CX`, terminal `MEASURE`).
- Serve internal gRPC compile endpoints.

TODO (not implemented yet):
- Full typed frontend (lexer/parser/type checker/symbol model as separate subsystems).
- Plugin-based syntax/semantic extension architecture.
- Neuro-symbolic/knowledge-base enrichment path.
- Incremental compilation and cross-job AST cache.

## RFC / ADR alignment

Implemented and aligned:
- **ADR 0004** (AST-only safety + deterministic AQO behavior baseline).
- **RFC 0014** (MVP safety policy and deterministic compilation behavior).
- **RFC 0005** (AQO v0.1 output contract for supported op subset).

TODO (alignment gaps to close later):
- Add explicit counters/reason-code taxonomy required by RFC 0014 observability section.
- Document/implement `UNIMPLEMENTED` split for “recognized-but-unsupported language patterns” where applicable.
- Expand deterministic contract evidence (hash/byte-stability checks) at service-level docs.

## Interfaces

### Public/Internal RPC surface

Implemented in service:
- `CompileCircuit`
- `CompileJob`
- `OptimizeCircuit` → returns `UNIMPLEMENTED`
- `ValidateCircuit` → returns `UNIMPLEMENTED`

TODO:
- Separate validation-only endpoint semantics and conformance profile.
- Optimization pipeline behind `OptimizeCircuit`.

### Input contract (implemented)

- Source payload (`source`) or `source_ref` in protobuf oneof.
- `options` map is accepted; distributed options are parsed into metadata fields.
- Validation returns `INVALID_ARGUMENT` with field violations for malformed/unsafe inputs.

TODO:
- Resolve/implement external source dereference flow for `source_ref`.
- Formalize/lock options schema and option versioning.

### Output contract (implemented)

- `CompileCircuitResponse.circuit.format = AQO_JSON`.
- `CompileCircuitResponse.circuit.data = canonical AQO JSON bytes`.
- `metadata` includes compiler/runtime attributes (including distributed option echo fields when present).

TODO:
- Additional output formats (AQO protobuf / QASM3 / backend-native).
- Annotated AST and symbol/type artifacts in public contract.

## Implemented language/security subset

Implemented checks:
- UTF-8 + Python syntax required.
- Exactly one `@hybrid_program` function required.
- Forbidden module roots (`os`, `sys`, `subprocess`) and non-allowlisted import roots rejected.
- Forbidden calls (`exec`, `eval`, `compile`) and prohibited dynamic I/O patterns rejected.
- Dynamic runtime control-flow nodes rejected (`if/for/while/match/...`).
- Resource limits from env:
  - `EIGEN_COMPILER_MAX_SOURCE_BYTES` (documented in README; TODO enforce directly in compiler path),
  - `EIGEN_COMPILER_MAX_AST_NODES`,
  - `EIGEN_COMPILER_MAX_AST_DEPTH`.

TODO:
- Complete formal allowlist spec in architecture docs for all permitted constructs.
- Rich semantic/type diagnostics (beyond structural safety + limited lowering checks).

## AQO lowering (implemented)

Implemented lowering behavior:
- Detects `Param("name")` assignment patterns and maps symbolic theta.
- Lowers recognized calls:
  - `rx(theta=...)` → `{"op":"RX","q":[0],...}`
  - `ry(theta=...)` → `{"op":"RY","q":[0],...}`
  - `rz(theta=...)` → `{"op":"RZ","q":[0],...}`
  - `cx(...)` → `{"op":"CX","q":[0,1]}`
- Appends terminal measurement over inferred qubit range.

TODO:
- Broaden qubit addressing model beyond fixed positions used in MVP lowering.
- Add observable/expectation native IR mapping completeness.
- Add optimizer passes (constant folding, dead code elimination, routing-aware rewrites).

## State and storage

Implemented now:
- Service is effectively stateless between requests.
- No persistent AST cache, symbol-table persistence, or filesystem cache contract in service code.
- Structured RPC lifecycle logging (`rpc_start` / `rpc_end`) with trace context extraction.

TODO:
- Reintroduce/implement persistent or shared cache design (if needed).
- QFS stage artifact layout for frontend internals (tokens/AST snapshots/etc.).
- Config-file driven frontend behavior (`configs/default/frontend.yaml`) for compiler service.

## Failure modes (actual + planned)

Implemented now:
- Syntax/UTF-8 errors → `INVALID_ARGUMENT` violations.
- Safety/allowlist/resource violations → `INVALID_ARGUMENT` violations.
- Unsupported RPC methods (`OptimizeCircuit`, `ValidateCircuit`) → `UNIMPLEMENTED`.

TODO:
- Distinguish semantic categories in machine-readable error codes.
- Partial-compilation/degradation modes.
- Plugin failure isolation model (plugins not yet present).
- Knowledge-base/neuro-compiler fallback matrix (integrations not yet present).

## Observability

### Metrics

Implemented now:
- gRPC request lifecycle logs with method/job_id/trace fields.
- Trace context extraction from `traceparent` and `trace_id` metadata.

TODO:
- Prometheus metrics promised by historical doc version.
- Full OpenTelemetry spans for parse/validate/lower phases.
- Compiler dashboard/alert SLO definitions backed by emitted metrics.

## Health/readiness

Implemented now:
- No explicit componentized readiness model in current compiler service module.

TODO:
- Readiness/liveness probes with dependency checks.
- Resource watermark checks and failure signaling.

## Notes for future updates

When expanding this component doc later, keep every new capability explicitly tagged as one of:
1. **Implemented** (with code reference), or
2. **TODO** (with missing behavior clearly listed).

This keeps architecture documentation auditable against RFC/ADR status and prevents silent scope drift.
