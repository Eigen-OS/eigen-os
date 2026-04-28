# Eigen-Lang submission format (MVP-2)

## Canonical artifact set

MVP-2 submission uses exactly two user-facing artifacts:

1. `job.yaml` (JobSpec v0.1)
2. Eigen-Lang source resolved from either:
   - `spec.program` (inline source), or
   - `spec.program_path` (safe relative path, default `program.eigen.py`)

## Contract at submit boundary

`SubmitJobRequest` carries source in `eigen_lang` fields:

- `eigen_lang.source` (raw bytes)
- `eigen_lang.entrypoint` (default `main`)
- `eigen_lang.sha256` (deterministic hash of source bytes)

This mapping is deterministic and covered by positive/negative fixture tests.

## Compiler safety model

Compiler is AST-only and never executes user code.

Validation rejects:

- forbidden imports outside allowed Eigen-Lang module roots,
- forbidden calls (`exec`, `eval`, `compile`),
- dynamic runtime control flow (`if/for/while/match/...` in MVP subset),
- invalid entrypoint shape (exactly one `@hybrid_program` required),
- AST size/depth beyond configured limits.

## Deterministic AQO output

For the same input source and compiler config, output AQO JSON is stable via canonical serialization (`sort_keys=True`, compact separators), enabling repeatable hashes and golden tests.

### Runtime-intelligence hints and diagnostics (Phase-4)

Compiler AQO metadata includes deterministic runtime-intelligence fields:

- `metadata.runtime_intelligence_hints.version` = `1.0.0`
- `metadata.runtime_intelligence_hints.diagnostics_version` = `1.0.0`
- `metadata.execution_annotations.version` = `1.0.0`
- `metadata.execution_annotations.explainability_id` (stable explainability identifier for workflow linking)

Compile-time diagnostics reject unsupported runtime targets and policy conflicts in a deterministic order, using `RUNTIME_INTELLIGENCE_DIAGNOSTIC` with field-level violations.

## Storage contract (QFS)

Per job, the pipeline persists source bundle and compiled artifacts in CircuitFS paths (`job.yaml`, `program.eigen.py`, `compiled.aqo.json`, results/metadata artifacts).

## References

- `docs/reference/jobspec.md`
- `docs/reference/eigen-lang/allowed-subset.md`
- `rfcs/0013-mvp2-jobspec-parser-submit-contract.md`
- `rfcs/0014-mvp2-eigen-lang-ast-safety-deterministic-aqo.md`
