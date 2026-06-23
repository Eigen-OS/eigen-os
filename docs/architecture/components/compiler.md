# Eigen Compiler Architecture Specification

- **Document status:** Normative (source of truth)
- **Subsystem:** Compiler Service (Eigen OS)
- **Contract version:** `1.0.0`
- **Applies to:** System API → Compiler Service → AQO artifacts persisted to QFS
- **Last updated:** 2026-06-17

This document defines the compiler boundary for Eigen OS. The compiler turns Eigen-Lang source into canonical AQO, validates that AQO against the contract, and emits stable diagnostics and metadata.

The deterministic semantic rule engine is authoritative for legality, lowering preconditions, rewrite acceptance, and workload-profile resolution. The neuro-symbolic layer is advisory only: it may propose, rank, or explain, but it must never override the rule engine.

The boundary between the compiler, knowledge base, optimizer, driver-manager, and ML advisor is defined in:

- `docs/architecture/components/neuro-symbolic-core.md`

Companion docs:

- `docs/architecture/adr/compiler-rule-engine-and-advisory-boundary.md`
- `docs/reference/compiler-model-migration-notes.md`
- `docs/architecture/components/knowledge-base.md`
- `docs/reference/formats/aqo.md`
- `docs/reference/eigen-lang.md`

---

## 1. Responsibilities

The compiler must:

1. Parse Eigen-Lang source into AST.
2. Validate the allowed language subset.
3. Resolve the workload-family profile deterministically from normalized options and source shape.
4. Apply the semantic rule engine to validate legality, rewrite eligibility, lowering preconditions, and backend compatibility.
5. Lower the program into deterministic AQO intent.
6. Validate the final AQO payload against the AQO contract.
7. Emit stable hashes, lineage, observability metadata, and compiler pass diagnostics.
8. Persist artifacts into QFS in a canonical layout.

The compiler must not execute user Python, import arbitrary modules, access host resources outside the workspace, or allow advisory ML output to bypass deterministic checks.

---

## 2. Contract versions

- **Eigen-Lang spec:** `1.0`
- **AQO format:** `1.0.0`
- **Compiler service contract:** `1.0.0`
- **Error model:** Eigen OS `1.0.0`

New compilation output must be AQO v1.0.0.

The compiler metadata contract is also stable and deterministic. The canonical names used by the implementation are:

- `workload_profile`
- `compiler_passes_json`
- `compiler_replay_json`
- `compiler_replay_sha256`
- `backend_contract_json`
- `logical_graph_schema_json`
- `logical_graph_schema_sha256`

These are compiler metadata fields, not AQO top-level fields.

---

## 3. Inputs and outputs

### 3.1 Inputs

Compilation input is carried via the internal compile RPC and includes:

- `source_bytes` (UTF-8) or `source_ref` (QFS reference),
- target information,
- bounded compiler options,
- request context for trace, tenant, project, and replay scope.

When both source forms are present, `source_bytes` is authoritative.

Advisory hints from neuro-symbolic components may be present in request context or compiler metadata, but they are never authoritative.

### 3.2 Outputs

The compiler must produce:

- canonical AQO JSON,
- compiler metadata,
- hashes and provenance information,
- deterministic pass and rule-engine diagnostics,
- explainability lineage that records when advisory output influenced, did not influence, or was transformed into a deterministic compiler action.

Optional transport encodings may exist, but they must preserve AQO semantics exactly.

---

## 4. Deterministic compilation guarantees

The compiler must guarantee that identical input yields identical AQO bytes and identical AQO hashes.

Determinism requirements:

- stable parameter naming,
- stable operation ordering,
- canonical JSON serialization,
- stable stage ordering,
- stable diagnostics ordering,
- stable workload-profile resolution,
- stable pass pipeline serialization.

Any nondeterministic input must be explicit and recorded in request metadata.

---

## 5. Safety model

Eigen-Lang source is never executed directly.

The compiler:

1. parses source into AST,
2. validates the allowed AST subset,
3. builds internal IR,
4. applies the semantic rule engine,
5. emits deterministic AQO.

The compiler must reject dynamic execution primitives, dynamic imports, filesystem / network / subprocess access, dynamic control flow, and reflection or metaprogramming outside the approved surface.

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

### 5.2 Semantic rule engine

The semantic rule engine is the source of truth for compiler legality.
The authoritative neuro-DPDA / ML-advisor boundary for compiler integrations lives in `docs/architecture/components/neuro-symbolic-core.md`.

It owns:

- semantic constraint evaluation,
- rewrite acceptance and rejection,
- lowering preconditions,
- backend compatibility checks,
- rule attribution for violations,
- deterministic fallback behavior when an advisory suggestion is not admissible.

The rule engine must be rule-safe:

- a suggestion cannot produce invalid IR by itself,
- lowering cannot proceed until the rule engine approves the candidate,
- advisory output may be discarded, transformed, or accepted only through deterministic compiler actions,
- invalid or ambiguous suggestions must fail closed.

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

The semantic rule engine gates `validate_ast`, `rewrite_ir`, and `validate_lowering`. Advisory hints may influence ranking of rewrite candidates, but they do not change pass ordering, pass membership, or validation authority.

The compiler also emits a bounded symbolic candidate set for advisory review. Each candidate is produced by the symbolic core, has a stable `candidate_id`, a compact feature map, and a legality flag. The emitted candidate set is serialized in compiler metadata as `symbolic_candidate_set_json`.

The payload also contains `ranked_candidates`, a legal-candidate-only list ordered by deterministic compiler-side advisory ordering. The ML advisor is implemented as a separate sidecar service and does not participate in compiler correctness. Each ranked candidate MUST carry a `rank`, a `confidence` score, the bounded logical graph encoding that the advisor consumed, and an `explanation` object with a human-readable `why_preferred` summary plus bounded `influential_features` and `influential_subgraph` hooks. The ranking surface remains advisory only and may be replaced or disabled without changing AQO output or lowering correctness.

Ranking layers may only score candidates whose `legal` flag is `true`. They must not invent additional candidates, rename emitted IDs, or treat illegal candidates as admissible.

The compiler also emits one canonical logical graph schema for AST, IR, and DPDA-state structures. The schema is serialized in compiler metadata as `logical_graph_schema_json` and hashed as `logical_graph_schema_sha256`. It is the same schema used for training and inference, and it defines bounded node and edge fields, canonical labels, and deterministic ordering rules for all logical compiler graph representations.

The compiler also emits a stable tabular telemetry feature set for model training and online scoring parity. It is serialized in compiler metadata as `telemetry_feature_set_json` and hashed as `telemetry_feature_set_sha256`. The tabular schema version is `telemetry-tabular-v1` and it captures graph size, fanout, stage counts, historical success rate, latency, backend, and policy-state telemetry in a deterministic field order.

Optional deterministic rewrite or hardware-adaptation work may be added as long as it remains replay-safe and does not change the meaning of canonical AQO. Workload-family specific validation happens before lowering and may reject a valid-looking source when the selected profile forbids it.

Pass ordering and pass outputs must remain stable for identical normalized inputs.

### Observability requirements

- Stage labels must be bounded and stable.
- Trace/request context must be preserved through compile stages.
- Metric labels must not include request IDs, trace IDs, tenant IDs, or project IDs.
- Duplicate / replay compiles must be observable.
- Stage failures must be attributable to a named stage and a structured violation.
- Advisor influence must be recorded as accepted, rejected, or transformed into a deterministic compiler action.

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
- Advisor outcomes are recorded when they are accepted, rejected, or transformed into a deterministic compiler action.
- Advisors can be swapped or disabled without breaking the compiler.

When the symbolic core enumerates candidates for ranking, the compiler must expose only the bounded candidate set that it produced. The model may rank those candidates, but it must not invent or relabel candidates and it must not use illegal candidates as ranking inputs.

The compiler must preserve determinism even when the advisor is enabled.

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
- explainability lineage,
- workload profile,
- pass pipeline snapshot,
- deterministic replay bundle with symbolic rule attribution,
- advisor influence outcome when present.

Observability records must be bounded and must not leak secrets.

---

## 11. Migration notes

The compiler model is still AQO v1.0.0, so there is no AQO schema migration.

What changed is the compiler contract surface and the way decisions are attributed:

- semantic legality is now attributed to the deterministic rule engine,
- workload-family profiles are part of compile-time normalization,
- advisory ML output is never authoritative,
- compiler pass ordering is explicit in metadata,
- explainability now records when a suggestion was accepted, rejected, or transformed into a deterministic compiler action.

Callers should treat compiler diagnostics and metadata as the source of truth for semantics, not advisor scores or heuristic hints.

---

## 12. Conformance expectations

A compliant compiler implementation must satisfy:

- deterministic AQO output,
- AQO contract validation,
- stable stage order,
- structured error mapping,
- replay-safe outputs,
- workload-profile resolution,
- semantic rule-engine attribution,
- advisor optionality,
- documentation and golden-fixture alignment.
