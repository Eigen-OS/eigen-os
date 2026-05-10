# Eigen-Lang Submission Contract (MVP-2 / Phase-5 Snapshot)

- Phase: MVP-2 (+ Phase-4/5 metadata extensions)
- Status date: **2026-05-10**
- Scope: canonical packaging from `job.yaml`/source files to public `SubmitJobRequest`, compiler intake, and persisted submission artifacts.

## Purpose

This document records the **current actual state** of the Eigen-Lang program submission contract into the system and clearly lists what is still missing to achieve a completely "frozen" submission contract.

Normative sources:

- `docs/reference/jobspec.md` (JobSpec v0.1 mapping)
- `docs/reference/api/grpc-public.md` (`SubmitJobRequest` surface)
- `docs/reference/formats/qfs-layout.md` (artifact persistence)
- `docs/reference/eigen-lang/*` (language subset/semantics/conformance/versioning)

## Canonical user-facing artifact set

MVP-2 submission uses exactly two user-facing artifacts:

1. `job.yaml` (JobSpec v0.1)
2. Eigen-Lang source resolved from either:
   - `spec.program` (inline source), or
   - `spec.program_path` (safe relative path, default `program.eigen.py`)
## Submit boundary contract (`SubmitJobRequest`)

`SubmitJobRequest` carries Eigen-Lang payload in `program.eigen_lang`:

- `eigen_lang.source` — raw source bytes.
- `eigen_lang.entrypoint` — default `main` when not explicitly set in JobSpec.
- `eigen_lang.sha256` — deterministic hash over the exact submitted source bytes.
  
JobSpec canonical mapping:

- `metadata.name` → `name`
- `spec.target` → `target`
- `spec.priority` → `priority` (default `50`)
- `spec.compiler_options` → `compiler_options`
- `spec.metadata` → `metadata` (+ internal snapshot fields)
- `spec.dependencies` → `dependencies`
- `spec.program`/`spec.program_path` → `eigen_lang.source`
- `spec.entrypoint` → `eigen_lang.entrypoint`

## Validation and safety model

Compiler/frontend validation is AST-only and never executes user code.

Validation rejects:

- forbidden imports outside allowed Eigen-Lang roots;
- forbidden calls (`exec`, `eval`, `compile`);
- dynamic runtime control flow outside MVP subset (`if/for/while/match/...` where disallowed by subset);
- invalid entrypoint/decorator shape (single valid `@hybrid_program` path);
- AST size/depth beyond configured limits;
- unsafe `spec.program_path` values (absolute paths, `..` traversal).

Validation failures are surfaced as `INVALID_ARGUMENT` with field-level violations.

## Deterministic compiler output

For the same source bytes + compiler configuration, canonical AQO JSON output is stable via deterministic serialization. This enables:

- repeatable SHA/hash results,
- stable golden fixtures,
- deterministic diagnostics ordering.

### Runtime-intelligence metadata (Phase-4)

AQO metadata includes deterministic runtime-intelligence fields:

- `metadata.runtime_intelligence_hints.version = "1.0.0"`
- `metadata.runtime_intelligence_hints.diagnostics_version = "1.0.0"`
- `metadata.execution_annotations.version = "1.0.0"`
- `metadata.execution_annotations.explainability_id` (stable identifier)

Unsupported runtime targets and policy conflicts are reported deterministically via `RUNTIME_INTELLIGENCE_DIAGNOSTIC` with field-level violations.

### Distributed metadata/hints (Phase-5)

Compiler metadata carries distributed execution contract fields:

- `metadata.distributed.execution_metadata_version = "1.0.0"`
- `metadata.distributed.topology_hints_version = "1.0.0"`
- `metadata.distributed.enabled = true|false`
- `metadata.distributed.target` (required when enabled)
- `metadata.distributed.partition_count` (optional; defaults to `1` when enabled)
- `metadata.distributed.queue_provider` (optional: `memory|redis|sqs`)
- `metadata.distributed.topology_hint` (optional: `data_parallel|pipeline`)

When distributed mode is enabled, AQO includes:

- `distributed_execution.version = "1.0.0"`
- `distributed_execution.target`
- `distributed_execution.partition_count`
- `distributed_execution.hints.version = "1.0.0"`
- `distributed_execution.hints.topology_hint`

## Persistence contract (QFS/CircuitFS)

Submission/compile pipeline persists artifacts in per-job QFS scope:

- `input/job.yaml`
- `input/program.eigen.py`
- `compiled/circuit.aqo.json`
- optional compile/result/log/meta helpers per QFS layout contract

This replaces older flat examples (`job.yaml`, `compiled.aqo.json` at root) for new jobs; readers should remain tolerant to legacy shapes where documented.

## Current gaps / what is still missing

To fully harden submission as a long-term frozen contract, the following are still open:

1. **Idempotency is still convention-based**
   - No first-class idempotency field in `SubmitJobRequest`; current practice relies on metadata keys/hash conventions.
2. **Entrypoint/decorator legality matrix is not fully centralized**
   - Rules are described across subset/syntax/conformance docs but not yet consolidated in a single normative table with exhaustive examples.
3. **Cross-surface conformance suite is incomplete**
   - No unified test profile that jointly verifies JobSpec parsing → gRPC payload → compiler diagnostics → QFS artifacts as one end-to-end normative suite.
4. **Program source provenance envelope is not standardized**
   - Source hash exists, but no frozen artifact envelope (`hash/size/path/media-type`) shared across API + compiler + QFS.
5. **Distributed submission policy profile is not fully explicit**
   - Phase-5 keys are present, but policy/SLO and replay/retention expectations for distributed submission flows are still documented as broader system gaps.
6. **Migration policy from legacy layouts is not version-tagged per submission artifact**
   - Read compatibility is described, but per-artifact migration markers are not yet formalized.

## Recommended follow-up hardening tasks

1. Add a single normative “submission conformance matrix” appendix with positive/negative fixtures and exact field-level violations.
2. Introduce an internal/public `ArtifactHandle`-style schema for source and compiled artifacts (`hash`, `size`, `path`, `format`).
3. Document canonical idempotency behavior for `SubmitJob` (preferred key, fallback, conflict semantics).
4. Add explicit compatibility table for legacy submission artifact layouts and deprecation timelines.

## References

- `docs/reference/jobspec.md`
- `docs/reference/api/grpc-public.md`
- `docs/reference/formats/qfs-layout.md`
- `docs/reference/eigen-lang/allowed-subset.md`
- `docs/reference/eigen-lang/syntax.md`
- `docs/reference/eigen-lang/semantics.md`
- `docs/reference/eigen-lang/conformance.md`
- `docs/reference/eigen-lang/versioning.md`
