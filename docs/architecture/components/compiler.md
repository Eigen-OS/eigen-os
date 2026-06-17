# Eigen Compiler Architecture Specification

- **Document status:** Normative (source of truth)
- **Subsystem:** Compiler Service (Eigen OS)
- **Contract version:** `1.0.0`
- **Applies to:** System API → Compiler Service → AQO artifacts persisted to QFS
- **Last updated:** 2026-06-17

This document defines the compiler boundary for Eigen OS. The compiler is responsible for turning Eigen-Lang source into canonical AQO, validating that AQO against the contract, and emitting stable diagnostics and metadata.

---

## 1. Responsibilities

The compiler must:

1. Parse Eigen-Lang source into AST.
2. Validate the allowed language subset.
3. Lower the program into deterministic AQO intent.
4. Validate the final AQO payload against the AQO contract.
5. Emit stable hashes, lineage, and observability metadata.
6. Persist artifacts into QFS in a canonical layout.

The compiler must not execute user Python, import arbitrary modules, access host resources outside the workspace, or allow advisory ML output to bypass deterministic checks.

---

## 2. Contract versions

- **Eigen-Lang spec:** `1.0`
- **AQO format:** `1.0.0`
- **Compiler service contract:** `1.0.0`
- **Error model:** Eigen OS `1.0.0`

New compilation output must be AQO v1.0.0.

---

## 3. Inputs and outputs

### 3.1 Inputs

Compilation input is carried via the internal compile RPC and includes:

- `source_bytes` (UTF-8) or `source_ref` (QFS reference),
- target information,
- bounded compiler options,
- request context for trace, tenant, and project scope.

When both source forms are present, `source_bytes` is authoritative.

### 3.2 Outputs

The compiler must produce:

- canonical AQO JSON,
- compiler metadata,
- hashes and provenance information.

Optional transport encodings may exist, but they must preserve AQO semantics exactly.

---

## 4. Deterministic compilation guarantees

The compiler must guarantee that identical input yields identical AQO bytes and identical AQO hashes.

Determinism requirements:

- stable parameter naming,
- stable operation ordering,
- canonical JSON serialization,
- stable stage ordering,
- stable diagnostics ordering.

Any nondeterministic input must be explicit and recorded in request metadata.

---

## 5. Safety model

Eigen-Lang source is never executed directly.

The compiler:

1. parses source into AST,
2. validates the allowed AST subset,
3. builds internal IR,
4. emits deterministic AQO.

The compiler must reject:

- `exec`, `eval`, `compile`,
- dynamic imports,
- filesystem / network / subprocess access,
- dynamic control flow,
- reflection or metaprogramming outside the approved surface.

The compiler must run in an isolated sandbox profile selected explicitly by request/deployment context.

### 5.1 Workload-family profiles

Before lowering, the compiler resolves a deterministic workload-family profile from the normalized request, compiler options, and source shape. The supported profiles are:

- `QuantumJob`
- `HybridWorkflow`
- `DistributedJob`
- `BenchmarkJob`
- `PipelineJob`
- `ReplayJob`

Each profile owns required semantic checks, allowed rewrites, forbidden transformations, target/backend expectations, replay or benchmark constraints, and observability requirements. Profile selection is deterministic and explainable, and advisory ML outputs MUST NOT bypass it.

---

## 6. Compilation pipeline

The canonical compiler service stages are:

1. `parse`
2. `validate_ast`
3. `annotate`
4. `lower_to_ir`
5. `eigen_dpda`
6. `canonicalize_aqo`
7. `emit`

Within the lowering boundary, the compiler also exposes a deterministic pass pipeline that is serialized in compiler metadata as `compiler_passes_json`. The pass pipeline separates rewrite steps from lowering/validation steps:

1. `lower_to_ir`
2. `rewrite_ir`
3. `validate_lowering`
4. `canonicalize_aqo`
5. `emit`

Optional deterministic rewrite or hardware-adaptation work may be added as long as it remains replay-safe and does not change the meaning of canonical AQO. Workload-family specific validation happens before lowering and may reject a valid-looking source when the selected profile forbids it.

Pass ordering and pass outputs must remain stable for identical normalized inputs.

### Observability requirements

- Stage labels must be bounded and stable.
- Trace/request context must be preserved through compile stages.
- Metric labels must not include request IDs, trace IDs, tenant IDs, or project IDs.
- Duplicate / replay compiles must be observable.
- Stage failures must be attributable to a named stage and a structured violation.

---

## 7. AQO boundary

AQO is the authoritative IR boundary for the compiler.

Compiler output must only use AQO top-level fields defined by the AQO contract:

- `version`
- `qubits`
- `operations`
- `parameters`
- `metadata`
- `checksums`
- `topology`
- `annotations`

Any compiler-specific or workload-specific information must be stored in an allowed nested field, not as a new top-level AQO field.

### 7.1 Required invariants

- `version` must equal the current AQO contract version.
- `qubits` must be a positive integer.
- `operations` must be a non-empty ordered list.
- Every opcode must be supported.
- Operation arity must match the opcode definition.
- Qubit indices must be in range.
- Measurement shape must be valid.
- Optional objects must remain objects.

### 7.2 Allowed nested use

- `metadata` stores compiler provenance and non-semantic metadata.
- `checksums` stores stable provenance hashes.
- `topology` stores distributed or backend topology hints.
- `annotations` stores compiler or runtime annotations such as expectation or hybrid markers.

---

## 8. Neuro-symbolic assistance

The compiler may use a neuro-symbolic advisor, but it must remain advisory only.

- Deterministic validation and normalization are authoritative.
- Neural suggestions may rank or propose candidates.
- Neural output must never bypass semantic checks or AQO validation.
- The final AQO payload must be valid without any neural-only field.

---

## 9. Error model

Compilation failures map to structured platform errors:

- parse / validation failures → `INVALID_ARGUMENT`
- unsupported but future documented features → `UNIMPLEMENTED`
- missing source references → `NOT_FOUND`
- resource limits → `RESOURCE_EXHAUSTED`
- internal invariants → `INTERNAL`

Every violation must identify the field or stage involved.

---

## 10. Persistence and observability

The compiler must persist:

- source digest,
- AQO digest,
- request digest,
- request context snapshot,
- explainability lineage.

Observability records must be bounded and must not leak secrets.

---

## 11. Conformance expectations

A compliant compiler implementation must satisfy:

- deterministic AQO output,
- AQO contract validation,
- stable stage order,
- structured error mapping,
- replay-safe outputs,
- documentation and golden-fixture alignment.
