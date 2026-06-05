# Eigen Compiler Architecture Specification

- **Document status:** Normative (source of truth)
- **Subsystem:** Compiler Service (Eigen OS)
- **Contract version:** `1.0.0`
- **Applies to:** System API → Kernel/QRTX → Compiler Service interactions, compiler artifacts persisted to QFS
- **Last updated:** 2026-05-28

This document defines the **canonical** compiler behavior and contracts for Eigen OS. It is written to match the Technical Specification (ТЗ) and to remove ambiguities so downstream code can be aligned to it.

## 0. Scope and non-goals

### In scope

- Deterministic compilation of **Eigen-Lang v1.0** source into **AQO v1.0** artifacts.
- Compiler safety model (AST-only, no user-code execution).
- Compiler service interfaces (internal gRPC), artifacts, error semantics.
- DPDA-based neuro-symbolic compilation architecture (Eigen-DPDA) as the target compiler core, including the required iteration cycle.
- Hardware-aware optimization hooks (GNN optimizer) as a **post-AQO** stage.

### Out of scope

- Public (external) compiler APIs (not exposed in `eigen.api.v1`).
- Vendor-specific backend compiler toolchains (those belong in drivers / provider SDKs).
- Full ML training pipelines (only the required integration points are defined here).

---

## 1. Canonical responsibilities

The compiler service is the semantic boundary between:

- **User programs** (Eigen-Lang source),
- **Runtime orchestration** (Kernel/QRTX),
- **Execution backends** (through Driver Manager).

The compiler MUST:

1. Parse Eigen-Lang source into an annotated AST.
2. Validate the allowed subset and enforce safety restrictions.
3. Produce **canonical, deterministic AQO v1.0** (JSON) as the primary IR artifact.
4. Optionally produce additional artifacts (AQO protobuf, QASM export) **without changing AQO**.
5. Validate AQO structure and invariants against the reference contract before persistence or downstream execution.
6. Emit structured diagnostics and deterministic error semantics.
7. Persist compilation artifacts and metadata into QFS in the canonical layout (see `qfs-layout.md`).

The compiler MUST NEVER:

- execute user Python code,
- import arbitrary modules,
- access the host filesystem outside the compilation workspace,
- access the network (unless explicitly enabled for **trusted** internal sources; disabled by default),
- spawn subprocesses.

The compiler safety model is AST-only and closed for v1.0:

- allowed imports are restricted to approved Eigen-Lang namespaces,
- only the entrypoint decorator `@hybrid_program(...)` is permitted,
- no arbitrary Python execution is allowed,
- no runtime code generation is allowed,
- no dynamic imports are allowed,
- no dynamic control flow is allowed,
- no forbidden builtins or reflective access are allowed.

---

## 2. Contract and versioning

### 2.1 Contract versions

- **Eigen-Lang spec:** `1.0`
- **AQO format:** `1.0`
- **Compiler service contract:** `1.0.0`
- **Error model:** Eigen OS `1.0.0` (`error-model.md`, `error-mapping.md`)

### 2.2 Backward compatibility

If legacy AQO `0.1` artifacts exist in QFS, the runtime MAY continue to execute them during a migration window, but:

- **New compilation output MUST be AQO v1.0**.
- Any compatibility mode MUST be explicit via a version field in artifacts and MUST be test-covered.

---

## 3. Inputs and outputs

### 3.1 Primary input: program source

Inputs to compilation are carried via the internal `CompileJob` (or equivalent) RPC and MUST include:

- `source_bytes` (UTF-8) **or** `source_ref` (QFS ref to the source file),
- `entrypoint` (default: `main`),
- `target` (string, e.g. `sim:local`, `cluster:auto`, `runtime:auto`),
- `compiler_options` (bounded map of strings),
- `request_context` (trace context, tenant/project scope via metadata).

**Source precedence** (when both provided):

1. `source_bytes` (authoritative)
2. `source_ref` (fallback)

### 3.2 Primary output artifacts

The compiler MUST produce and persist:

- `compiled/circuit.aqo.json` (**required**, canonical AQO v1.0 JSON, sorted keys, no insignificant whitespace)
- `compiled/metadata.json` (**required**, compiler metadata and hashes)

The compiler MAY additionally persist:

- `compiled/circuit.aqo.pb` (optional, AQO protobuf encoding)
- `compiled/circuit.qasm` (optional export, best-effort, explicitly marked as non-authoritative if incomplete)

### 3.3 Required metadata fields

`compiled/metadata.json` MUST contain at least:

- `compiler_contract_version`: `"1.0.0"`
- `eigen_lang_version`: `"1.0"`
- `aqo_version`: `"1.0"`
- `source_sha256`: `sha256:<hex>`
- `aqo_sha256`: `sha256:<hex>` (hash of the canonical AQO bytes)
- `created_at`: RFC3339 timestamp
- `entrypoint`: string
- `target`: string
- `options`: canonicalized compiler options (sorted keys)

It MAY contain:

- `qasm_sha256`
- `optimizer_report_ref` (QFS ref)
- `placement_map_ref` (QFS ref)
- `diagnostics_ref` (QFS ref)

---

## 4. Deterministic compilation guarantees (normative)

The compiler MUST guarantee:

```text
same_source_bytes
+ same_entrypoint
+ same_target
+ same_compiler_options (after canonicalization)
= identical_AQO_bytes
= identical_aqo_sha256
```

Determinism requirements:

- Canonical parameter naming is stable (no dependence on hash-map iteration order).
- Operation ordering is stable and reproducible.
- AQO JSON serialization is canonical (sorted keys, stable list ordering, no whitespace variability).
- Diagnostics ordering is stable (sorted by source location).

Any nondeterministic input (e.g. random seed) MUST be explicitly provided as an option and included in the metadata and request hash.

---

## 5. Safety model (AST-only)

### 5.1 Allowed model

- Parse source via a Python AST parser.
- Traverse AST with a strict allowlist.
- Extract only declarative constructs.
- Build an internal IR without executing any user code.
- Keep the accepted surface closed and deterministic.

### 5.2 Forbidden constructs (must fail with `INVALID_ARGUMENT`)

- `exec`, `eval`, `compile`
- dynamic imports or imports outside `eigen_lang` allowlist
- filesystem/network/subprocess access
- dynamic control flow (`if`, `for`, `while`, `match`) in v1.0
- reflection / metaprogramming (`getattr` with non-literal names, `globals`, `locals`, etc.)

### 5.3 Canonical validation outcomes

- Syntax and parse failures map to `INVALID_ARGUMENT`.
- Unsupported but documented-future features map to `UNIMPLEMENTED`.
- Missing source references map to `NOT_FOUND`.
- Resource limits map to `RESOURCE_EXHAUSTED`.
- Compiler-internal invariants map to `INTERNAL`.

### 5.4 Isolation requirements (per ТЗ)

The compiler MUST run in an isolated container / sandbox profile:

- no outbound network by default,
- read-only filesystem outside the compilation workspace,
- strict CPU/memory/time limits,
- no access to host credentials or secrets,
- explicit allowlisted environment variables only.

---

## 6. Compilation pipeline (normative stages)

The compiler is stage-oriented. The pipeline MUST include the following stages, with stable stage naming for observability:

1. **ingest**: decode/validate UTF-8; normalize line endings.
2. **parse**: build AST; reject syntax errors.
3. **validate_ast**: enforce allowlist; reject forbidden nodes/calls/imports.
4. **annotate**: build symbol table; annotate AST nodes with semantic tags.
5. **lower_to_ir**: build deterministic internal IR representation of the program intent.
6. **eigen_dpda**: produce AQO stream deterministically (see section 7).
7. **canonicalize_aqo**: normalize/validate AQO invariants (arity, indices, params).
8. **optional_optimize**: deterministic rewrite passes (if enabled; must be replay-safe).
9. **optional_hardware_adapt**: hardware hints / placement (post-AQO, advisory).
10. **emit**: write artifacts to QFS atomically; emit hashes.

The compiler MUST surface stage timing and failures in structured logs and traces (see section 11).

---

## 7. Eigen-DPDA neuro-symbolic core (required architecture)

This section is normative for the target compiler core as described in the Technical Specification (ТЗ).

### 7.1 Two-stage model

Eigen-DPDA combines:

- **DPDA (Deterministic Pushdown Automaton):** defines *allowed actions* at each compilation state and enforces correctness.
- **Neural model (Transformer/GNN):** scores allowed actions using context (AST + device hints + KB experience) and selects the best action.

**Important safety rule:** Neural outputs are advisory. Final decisions MUST be validated by the DPDA and the symbolic invariants.

### 7.2 Required DPDA compilation cycle

The DPDA compilation loop MUST behave as follows:

1. Parse Eigen-Lang into **annotated AST**.
2. Initialize DPDA with the AST root and compilation context.
3. Iterate until terminal state:

   - DPDA computes `allowed_actions` for the current state.
   - The model computes a score for each action given the context:
     - AST neighborhood / cursor,
     - target/backend hints,
     - historical KB features (if available),
     - policy constraints.
   - Select the highest-scoring action (tie-broken deterministically).
   - DPDA applies the action, updates stack/state, and emits zero or more AQO ops.

4. On terminal state, DPDA returns the full AQO stream plus compilation metadata.

The implementation MUST provide a deterministic fallback when the model is unavailable:

- **DPDA-only mode** where the action selection uses deterministic policy rules (e.g. fixed priority ordering).

### 7.3 Training and KB integration (interface-level requirements)

The compiler MUST be able to export training examples (without secrets) containing:

- input signature (normalized AST features),
- selected action sequence,
- resulting AQO hash,
- execution outcome metadata (fidelity/latency where available).

The KB integration is optional at runtime, but the interfaces MUST be present so training pipelines can ingest telemetry.

---

## 8. AQO generation requirements (v1.0)

The compiler MUST emit AQO v1.0 compliant with `aqo.md`.

Mandatory properties:

- `version`, `qubits`, `operations` exist.
- All indices are within bounds.
- Operation arity matches opcode definition.
- Parameters follow opcode rules.
- `MEASURE` invariants (`len(q) == len(c)`) hold.
- Unknown opcodes are rejected.

The compiler MUST ensure canonical bit ordering expectations are met by the end-to-end system by generating measurements consistent with the AQO contract (see `aqo.md`).

---

## 9. Optimization and hardware adaptation

### 9.1 Deterministic optimization (MVP-safe)

If optimization is enabled via compiler options, optimizations MUST be:

- deterministic,
- semantics-preserving,
- replay-safe.

Examples of allowed deterministic passes:

- canonical gate normalization,
- dead operation elimination (only when provably safe),
- deterministic gate fusion (no heuristic randomness).

### 9.2 Hardware-aware adaptation (GNN optimizer, post-AQO)

Hardware adaptation operates **after** canonical AQO generation.

Inputs (advisory):

- AQO graph,
- device topology graph,
- calibration metadata,
- noise/error models.

Outputs (advisory artifacts):

- placement map (logical → physical qubits),
- routing hints (e.g. SWAP plan),
- hardware profile annotations.

**Deterministic boundary:** Any non-deterministic model inference MUST NOT change the canonical AQO. Instead, it MUST be emitted as separate artifacts and applied by runtime policies that are themselves deterministic and audit-safe.

---

## 10. Service interfaces (internal gRPC)

The compiler is accessed via internal gRPC (`eigen.internal.v1`). The `.proto` files are the source of truth. The following methods MUST exist and behave as described:

- `CompileCircuit`: compile a single circuit-like program input into AQO artifacts.
- `CompileJob`: compile a full job submission (JobSpec + program) into AQO artifacts and metadata.

If `OptimizeCircuit` and `ValidateCircuit` exist in proto but are not implemented, they MUST return `UNIMPLEMENTED` deterministically until implemented or removed.

### 10.1 Idempotency and caching

Compilation may be cached by `(source_sha256, options_hash, target)`.

If caching is implemented:

- cache lookup MUST be deterministic,
- cache hits MUST return identical artifacts,
- cache metadata MUST be surfaced (e.g. `metadata.cache_hit: true`).

---

## 11. Observability (compiler telemetry)

The Technical Specification requires compilation visibility (CompilationMetrics, DPDA steps). The compiler MUST provide:

### 11.1 Traces (OpenTelemetry)

Spans MUST include:

- `compiler.ingest`
- `compiler.parse`
- `compiler.validate_ast`
- `compiler.annotate`
- `compiler.eigen_dpda`
- `compiler.emit`

Required span attributes:

- `job_id` (if known)
- `target`
- `aqo_version`
- `source_sha256` (redacted/hashed form is acceptable; do not emit raw source)
- `cache_hit` (boolean, if applicable)

### 11.2 Metrics (Prometheus)

At minimum, the compiler MUST expose:

- `eigen_compiler_contract_info{version="1.0.0"} 1` (contract marker)
- `eigen_compiler_compilations_total{result="succeeded|failed"}` (counter)
- `eigen_compiler_phase_duration_seconds{phase="<stage>"}` (histogram or summary; bounded phase label)
- `eigen_compiler_dpda_steps_total{result="succeeded|failed"}` (counter)
- `eigen_compiler_source_bytes` (histogram)
- `eigen_compiler_aqo_ops` (histogram)

Label rules:

- MUST NOT include `job_id`, `trace_id`, raw user identifiers, or any unbounded values.
- Any labels MUST be finite enums (`phase`, `result`, `target_class`).

### 11.3 Logs

Logs MUST be structured and correlation-friendly, including:

- `trace_id`, `span_id`,
- `job_id` when available,
- `source_sha256`, `aqo_sha256`,
- deterministic error codes on failure.

---

## 12. Error handling (canonical)

Errors MUST follow `error-model.md` and `error-mapping.md`.

### 12.1 Common compiler errors

- Syntax error / invalid UTF-8 / forbidden AST nodes: `INVALID_ARGUMENT`
- Exceeded resource limits: `RESOURCE_EXHAUSTED` (or `INVALID_ARGUMENT` if treated as validation; pick one policy and keep it consistent—default: `RESOURCE_EXHAUSTED` for hard size limits)
- Unsupported language feature: `UNIMPLEMENTED`
- Internal invariant violation: `INTERNAL`
- Missing source reference: `NOT_FOUND` (when `source_ref` points to a missing artifact)

Validation failures MUST include structured details equivalent to `google.rpc.BadRequest` field violations.

---

## 13. Resource limits and DoS resistance

The compiler MUST enforce bounded resource usage:

- `max_source_bytes`
- `max_ast_nodes`
- `max_ast_depth`
- `max_compile_wall_time`

Limits MUST be configurable per deployment and SHOULD be quota-aware in multi-tenant setups.

---

## 14. Conformance and CI requirements

A conformant compiler implementation MUST have CI that validates:

1. Deterministic AQO output for identical inputs (byte-for-byte).
2. Stable hashing (`source_sha256`, `aqo_sha256`).
3. Rejection of forbidden constructs with deterministic error codes.
4. AQO v1.0 schema invariants (including measurement invariants).
5. Internal RPC compatibility and `UNIMPLEMENTED` behavior for stubs.
6. Observability markers and required metric presence.
7. QFS artifact layout correctness (per `qfs-layout.md`).

Golden tests MUST be used for fixture-based stability.

---

## 15. Implementation notes (truthfulness)

This document is normative. If the repository currently emits AQO `0.1` or lacks some metrics, the code MUST be updated to match this document. The intended source of truth is:

- `aqo.md` for AQO format,
- internal proto files for RPC message shapes,
- this document for compiler semantics, stages, and determinism requirements.

---

## 16. Summary

The Eigen Compiler is a deterministic, sandboxed, stage-oriented compilation service that transforms Eigen-Lang v1.0 programs into AQO v1.0 artifacts. It is designed around the Eigen-DPDA neuro-symbolic architecture (DPDA + model scoring) with a strict deterministic safety boundary, produces canonical QFS artifacts, and exposes required observability for compilation timing and DPDA step visibility.

---

## Appendix A. Diagrams (normative)

### A.1 C4 — Context (Compiler Service)

![Context](https://i.imgur.com/nnLAemw.png)

<details>
<summary>code</summary>

```text
graph LR
  Client[System API / Kernel-QRTX] -->|internal gRPC: eigen.internal.v1| Compiler["Eigen Compiler Service\n(deterministic, sandboxed)"]
  Compiler -->|read/write artifacts| QFS["QFS\n(qfs://...)"]
  Compiler -->|optional advisory lookups| KB["Knowledge Base\n(optional)"]
  Compiler -->|optional model scoring| ModelReg["Model Registry\n(signed models)"]
  Compiler -->|telemetry| Obs["Observability\n(OTel, metrics, logs)"]

  subgraph Trust Boundaries
    Sandbox["Compiler Sandbox Profile\n(no network by default,\nro-fs outside workspace,\nCPU/Mem/Time limits)"]
  end
  Compiler --- Sandbox
```

</details>

**Normative notes:**

- Only **Kernel/QRTX** (or internal orchestrator) calls the compiler; there is **no public compiler API**.
- QFS is the **canonical persistence** for compilation artifacts and metadata.

---

### A.2 C4 — Container view (internal runtime slice)

![Container view](https://i.imgur.com/7JsYTt6.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Runtime["Eigen OS Runtime (internal)"]
    K["Kernel/QRTX"]
    C["Compiler Service"]
    QFS["QFS Service"]
    KB["Knowledge Base (optional)"]
    MR["Model Registry (optional)"]
    OTEL["OTel Collector / Metrics"]
  end

  K -->|"CompileJob / CompileCircuit\n(eigen.internal.v1)"| C
  C -->|"PUT artifacts (atomic)\nGET sources (optional)"| QFS
  C -->|"Query candidates (optional)"| KB
  C -->|"Fetch signed model (optional)"| MR
  C -->|"traces/metrics/logs"| OTEL
```

</details>

**Normative notes:**

- Compiler remains deterministic even if KB/model are unavailable: **DPDA-only fallback** MUST be used.

---

### 10.A.3 Component diagram — Compiler pipeline (stages are normative)

![Compiler pipeline](https://i.imgur.com/ZyiSfNG.png)

<details>
<summary>code</summary>

```text
flowchart TB
  subgraph Compiler["Compiler Service (single request)"]
    Ingest["ingest\nUTF-8 validate + line ending normalize"]
    Parse["parse\nAST build"]
    VAST["validate_ast\nallowlist enforcement"]
    Annot["annotate\nsymbols + semantic tags"]
    Lower["lower_to_ir\ndeterministic internal IR"]
    DPDA["eigen_dpda\nallowed_actions + deterministic tie-break"]
    Canon["canonicalize_aqo\nschema + invariants"]
    Opt["optional_optimize\ndeterministic passes only"]
    HW["optional_hardware_adapt\nadvisory only (post-AQO)"]
    Emit["emit\natomic QFS writes + hashes"]
  end

  Ingest --> Parse --> VAST --> Annot --> Lower --> DPDA --> Canon --> Opt --> HW --> Emit
```

</details>

**Normative notes:**

- `optional_hardware_adapt` MUST NOT change canonical AQO; it outputs **separate advisory artifacts** only.

---

### A.4 Component diagram — Eigen-DPDA core (decision safety boundary)

![Eigen-DPDA core](https://i.imgur.com/HR0AhZC.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph DPDA_Core["Eigen-DPDA core"]
    State["DPDA state + stack"]
    Allowed["allowed_actions(state)"]
    Model["Neural scorer (optional)\nTransformer/GNN"]
    Policy["Deterministic policy\n(DPDA-only mode)"]
    Select["select_action\n(deterministic tie-break)"]
    Apply["apply_action\n(update state/stack)\n+ emit AQO ops"]
  end

  State --> Allowed
  Allowed --> Model
  Allowed --> Policy
  Model --> Select
  Policy --> Select
  Select --> Apply --> State
```

</details>

**Normative notes:**

- Model outputs are advisory;** DPDA invariants are authoritative**.
- If model unavailable/invalid: **Policy path MUST be used**.

---

### A.5 Sequence — CompileJob happy path (QFS atomic artifact emission)

![CompileJob happy path](https://i.imgur.com/GEY0BAN.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
    autonumber
    participant K as Kernel/QRTX
    participant C as Compiler Service
    participant Q as QFS
    participant O as Observability

    K->>C: CompileJob(source_bytes|source_ref, entrypoint, target, options)<br/>+ trace context
    C->>O: Start spans (compiler.ingest..emit)

    alt source_ref provided
        C->>Q: GET qfs://.../source
        Q-->>C: source_bytes
    end

    Note over C: ingest → parse → validate_ast → annotate → lower_to_ir<br/>eigen_dpda (fallback)<br/>canonicalize_aqo (+ optimize)

    C->>Q: PUT staged artifacts (temp prefix)
    Q-->>C: ACK

    C->>Q: COMMIT/RENAME (atomic publish)
    Q-->>C: ACK

    C-->>K: CompileJobResponse(artifact_refs, hashes, cache_hit?)
    C->>O: End spans + metrics
```

</details>

**Normative notes:**

- `emit` MUST be **atomic**: either all required artifacts become visible, or none.

---

### A.6 Sequence — Deterministic caching (optional, but contract rules are normative if enabled)

![Deterministic caching](https://i.imgur.com/rATQ5FD.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant K as Kernel/QRTX
  participant C as Compiler Service
  participant Q as QFS

  K->>C: CompileJob(...)
  C->>C: compute source_sha256 + options_hash + target
  C->>C: cache_lookup(key)

  alt cache hit
    C->>Q: GET qfs://cache/<key>/compiled/metadata.json
    Q-->>C: metadata (includes aqo_sha256)
    C-->>K: CompileJobResponse(cache_hit=true, artifact_refs)
  else cache miss
    C->>C: run pipeline (deterministic)
    C->>Q: PUT qfs://cache/<key>/compiled/* (atomic)
    Q-->>C: ACK
    C-->>K: CompileJobResponse(cache_hit=false, artifact_refs)
  end
```

</details>

#### Normative notes:

- Cache hit MUST return **byte-identical** AQO artifacts for the same key.

---

### A.7 Sequence — Forbidden construct / validation failure (canonical error mapping)

![Forbidden construct / validation failure](https://i.imgur.com/LwP1YG2.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant K as Kernel/QRTX
  participant C as Compiler Service
  participant O as Observability

  K->>C: CompileJob(source_bytes,...)
  C->>O: span compiler.validate_ast
  C->>C: validate_ast detects forbidden node/call/import
  C-->>K: gRPC INVALID_ARGUMENT\n+ google.rpc.BadRequest(field_violations)\n+ ErrorInfo(reason="EIGEN_COMPILER_FORBIDDEN_AST")
  C->>O: log structured error\n(metrics: compilations_total{failed})
```

</details>

#### Normative notes:

- Validation failures MUST be deterministic and include structured `BadRequest` details.

---

### A.8 Deployment / isolation view — compiler sandbox profile (normative intent)

![Deployment](https://i.imgur.com/BsVBTCJ.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Pod["Kubernetes Pod: compiler-service"]
    C["compiler-service container"]
    SB["sandbox profile\n(no net by default)\nro-fs outside workspace\ncpu/mem/time limits"]
  end

  K["Kernel/QRTX"] -->|"internal gRPC"| C
  C -->|"QFS writes/reads\n(allowlisted egress only if required)"| QFS["QFS endpoint"]
  C --- SB
```

</details>

#### Normative notes:

- Network access is **disabled by default**; if QFS access requires network, the egress MUST be **allowlisted** and auditable.
- Only allowlisted environment variables are visible to the compiler process.
