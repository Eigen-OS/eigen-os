# RFC 0011: Eigen-Lang submission format v0.1 (user sources → compiler → AQO)

- **Status:** Discussion
- **Authors:** NYankovich
- **Created:** 2026-01-08
- **Target milestone:** Phase 0 (MVP)
- **Related:** RFC 0003 (JobSpec), RFC 0004 (gRPC API), RFC 0005 (AQO), RFC 0007 (QRTX)

## Summary

Defines the canonical way a user provides **Eigen-Lang** to Eigen OS in MVP, and how that source is packaged, validated, stored, and compiled **without executing user Python**.

## Motivation

Without a strict definition of “user source”, the CLI, System API, compiler, and kernel will drift:
- different entrypoint discovery rules
- inconsistent hashing/dedup
- unsafe “execution” of user code
- irreproducible results

## Goals

- One canonical submission artifact set: `program.eigen.py` + `job.yaml`.
- Deterministic packaging: source bytes + sha256.
- Server-side compilation is **AST-only** (parse/validate/transform), not execution.
- Clear precedence rules for runtime options: CLI flags > JobSpec > source defaults.

## Non-Goals

- A separate non-Python Eigen syntax (`.eigen`) in MVP.
- Full sandboxing / secure multi-tenant execution (Phase 1+).
- Large-data upload through gRPC.

## Canonical artifacts

### 1) program.eigen.py
A Python file using Eigen-Lang DSL.

Rules (MVP):
- Exactly **one** entrypoint function decorated with `@hybrid_program`.
- Imports are restricted to `eigen_lang.*` (and other allowlisted pure modules).
- No filesystem/network I/O.
- Forbidden: `exec`, `eval`, dynamic imports, subprocess, sockets.

### 2) job.yaml (JobSpec v0.1)
Contains runtime settings, target, compiler options, and input references.
See RFC 0003.

### 3) Input references
Large inputs (datasets, binaries) are referenced by URI (e.g., `s3://`, `https://`, `file://`) and optional hash.

## Packaging into SubmitJobRequest

### SubmitJobRequest.program oneof (proposed)
At the public API boundary, program is carried as a `oneof`:

- `eigen_lang_source { bytes source; string entrypoint; string sha256; }`
- `qasm3_source { bytes source; string sha256; }` (optional)
- `aqo_ref { string qfs_ref; string sha256; }` (optional)

MVP MUST support `eigen_lang_source`.

### Determinism & dedup
CLI SHOULD compute sha256 of source bytes and pass it.
Server MAY deduplicate by `(subject, sha256)` within a retention window.

## Compiler behavior (AST-only)

Compiler MUST:
1) `ast.parse(source)` and validate syntax
2) enforce allowlist of AST nodes and imports
3) locate the `@hybrid_program` entrypoint (by name or decorator)
4) transform into annotated internal AST
5) compile quantum parts to AQO (RFC 0005), optionally emit QASM3 for debugging

Compiler MUST NOT execute the module or call user-defined functions.

## Storage contract (QFS / CircuitFS)

Kernel stores:
- `circuit_fs/<job_id>/program.eigen.py` (original bytes)
- `circuit_fs/<job_id>/job.yaml` (resolved JobSpec)
- `circuit_fs/<job_id>/compiled.aqo.json`
- `circuit_fs/<job_id>/compiled.qasm` (optional)
- `circuit_fs/<job_id>/results.json`
- `circuit_fs/<job_id>/meta.json` (hashes, versions, timestamps)

## Precedence of options

- CLI flags override JobSpec.
- JobSpec overrides defaults declared in source decorators.
- Compiler options are immutable once the job is accepted.

## Testing plan

- Unit: parser/validator rejects forbidden nodes and imports.
- Unit: entrypoint discovery (exactly one `@hybrid_program`).
- Golden: source + options → AQO JSON hash is stable.
- Integration: submit job → compile → execute (sim) → results.

## Alternatives considered

- Execute user Python in a sandbox: rejected for MVP due to complexity and non-determinism.
- Custom `.eigen` syntax in MVP: postponed.

## Open questions

- Exact allowlist of AST nodes for MVP (appendix TBD).
- Whether `CompilationService` is public in MVP or internal-only (see RFC 0004).
