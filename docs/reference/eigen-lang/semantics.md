# Eigen‑Lang semantics (v0.1)

> **Status snapshot (as of 2026-05-09):** this document is synchronized with `docs/architecture/*` and current Eigen‑Lang reference docs. It separates **implemented now** semantics from **TODO / missing** contract items required to freeze the system state.

Eigen‑Lang programs define a **hybrid quantum-classical workflow contract** that compiles into AQO-compatible artifacts.

## 1) Program model

### Implemented now

The semantic model used in MVP is:
- source (`program.eigen.py`) + `job.yaml` are validated by compiler frontend policy,
- accepted source is lowered into deterministic AQO output,
- runtime executes hybrid stages as orchestrated steps (compile → execute → collect → report).

At language-contract level, `minimize(...)` is the canonical hybrid intent. In current MVP implementation/docs, full production loop lowering is still partial and represented as baseline deterministic behavior plus runtime orchestration contracts.

### Contract intent (normative)

Entrypoint denotes a hybrid DAG with:
- **quantum nodes**: prepare/transform/measure circuits,
- **classical nodes**: parameter update/reduction/objective computation,
- **edges**: explicit data dependencies.

### TODO / missing

- Freeze one normative “program-shape” matrix (`supported`, `rejected`, `planned`) with direct conformance fixture links.
- Close the gap between “DAG intent” wording and currently implemented lowering subset for hybrid loops.

## 2) Determinism and reproducibility

### Implemented now

Given identical:
- program source bytes,
- compiler/runtime-relevant `job.yaml` options,
- referenced artifact hashes,

the compiler must produce deterministic AQO output for the supported subset.

Validation behavior is deterministic (stable class of rejection for same input), with errors surfaced as structured `INVALID_ARGUMENT` for frontend violations.

### TODO / missing

- Freeze machine-readable rejection reason taxonomy across compiler docs/tests.
- Publish reproducibility checklist that explicitly covers env knobs impacting parser/AST limits.

## 3) Language/runtime boundary semantics

### Implemented now

- Compiler output and submission contracts carry runtime options/metadata through existing envelopes.
- Runtime-side execution semantics are defined in orchestration/runtime contracts (kernel/system-api/driver-manager paths).
- Quantum execution consumes compiled circuit/task representation + backend options and returns measurement-oriented results + metadata.

### TODO / missing

- Publish one canonical boundary contract table: which fields are compiler-owned, runtime-owned, echoed, or transformed.
- Explicitly mark unsupported boundary behaviors with stable error/status mapping.

## 4) Control-flow semantics (MVP status)

### Implemented now

Current compiler validation path rejects runtime/dynamic Python control flow patterns (`if/for/while/match/...`) outside the accepted lowering subset.

### Docs-level intent requiring closure

Other docs still describe possible compile-time-constant control flow as optional MVP behavior; this is **not yet frozen as implemented semantic surface** and must be treated as planned/under-specified until conformance-backed.

### TODO / missing

- Resolve and freeze whether compile-time-constant control flow is in MVP or explicitly post‑MVP.
- Add positive/negative fixtures proving chosen behavior.

## 5) Measurement/result semantics

### Implemented now

- Canonical quantum result surface remains counts-oriented (`bitstring -> integer`) with metadata.
- Result retrieval and artifact persistence semantics are specified by runtime/QFS/result contracts.

### TODO / missing

- Freeze canonical bit-ordering/mapping policy reference and require it in all result envelopes.
- Add strict conformance tests for cross-backend result-shape invariants.

## 6) Error semantics

### Implemented now

- Frontend syntax/validation errors: `INVALID_ARGUMENT` with structured field violations.
- Runtime/backend failures: mapped via runtime error contracts (`UNAVAILABLE`, `RESOURCE_EXHAUSTED`, `FAILED_PRECONDITION`, `INTERNAL`, etc., depending on failure class).

### TODO / missing

- Document deterministic `UNIMPLEMENTED` vs `INVALID_ARGUMENT` split for recognized-but-unsupported language patterns.
- Publish one end-to-end error mapping table from Eigen‑Lang semantic category → gRPC status → domain code.

## 7) What is missing to fully fix and freeze system state

1. **Semantic compatibility matrix**
   - Unified table across `syntax.md`, `semantics.md`, `standard-library.md`, `allowed-subset.md` with status + fixture IDs.
2. **Conformance parity gate**
   - Positive fixture for each documented “implemented” semantic claim and negative fixture for each rejection class.
3. **Deterministic diagnostics contract**
   - Stable reason-code taxonomy and field naming, versioned and release-drift checked.
4. **Compiler/runtime boundary ledger**
   - Explicit ownership and transformation rules for metadata/options/results between compiler output and runtime execution layers.
5. **Docs sync enforcement**
   - CI/doc check that blocks contradictory semantic claims across architecture/reference docs.

Until these items are complete, the MVP baseline remains operational, but language semantics are still partially under-specified at the contract/compliance level.
