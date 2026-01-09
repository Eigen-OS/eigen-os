# RFC 0012: Eigen‑Lang v0.1 (MVP) — language scope, semantics, safety, compatibility

- **Status:** Discussion
- **Authors:** NYankovich
- **Created:** 2026-01-09
- **Target milestone:** Phase 0 (MVP)
- **Tracking issue:** (TBD)
- **Supersedes / Related:** RFC 0011 (Eigen‑Lang submission format), RFC 0004 (Public API), RFC 0006 (QDriver/DriverManager), AQO v0.1

## Summary
Define Eigen‑Lang v0.1 as a **Python DSL** for describing hybrid quantum workflows.  
This RFC freezes what is “the language” in MVP: entrypoint contract, execution model, allowed subset, determinism rules, mapping targets (AQO/QASM), and compatibility policy.

## Motivation
Eigen‑Lang becomes a user‑facing contract as soon as external users write programs. Mature ecosystems formalize such changes through proposal processes (e.g., Python PEPs, Rust RFCs) to capture rationale and avoid accidental breaking changes.

## Goals (MVP)
- Minimal, teachable DSL to express:
  - parameterized circuits
  - measurement + counts
  - simple hybrid optimization loop (VQE‑style pattern)
- Safe and deterministic compilation:
  - AST parsing only (no execution)
  - strict allowlist + resource limits
- Canonical execution IR:
  - AQO JSON (canonical), optional QASM emission

## Non‑Goals (MVP)
- Running arbitrary Python on the server
- Dynamic runtime control flow driven by measurement results inside user code
- v1.0 stability guarantees
- KB/GNN/HWE integration (Post‑MVP)

## Guide-level explanation
Users write `program.eigen.py` with exactly one `@hybrid_program` entrypoint and submit it with `job.yaml`. The compiler parses/validates the file and emits AQO; the Kernel orchestrates execution and returns results.

## Reference-level explanation
### Entrypoint
- Exactly one `@hybrid_program` entrypoint per file.
- Entrypoint can be specified in JobSpec.
- Multiple entrypoints → INVALID_ARGUMENT.

### Safety model
Compiler parses AST and **must not execute** user code. Python’s `ast` parsing is for analysis and does not execute code, but untrusted inputs can still cause resource exhaustion; therefore strict limits + allowlist are mandatory.

### Determinism
Same source + job options + referenced inputs (by hash) → identical AQO JSON output (stable hash).

### Mapping target
Canonical output is AQO JSON v0.1. Optional QASM output is allowed as an extra artifact. Mapping rules live in `docs/reference/eigen-lang/mapping-to-aqo.md`.

### Errors
- Validation: INVALID_ARGUMENT + BadRequest.FieldViolation
- Unsupported: UNIMPLEMENTED (preferred)
- Runtime backend failures: per global error mapping

### Versioning
In v0.x:
- patch: no intentional breaking changes
- minor: breaking allowed with migration notes; compatibility mode if feasible  
All user-visible changes require RFC + reference doc updates + conformance updates.

## Drawbacks
- Restrictive subset reduces flexibility.
- Conformance suite requires maintenance.
- v0.x can still break users (managed via RFC + migration docs).

## Rationale and alternatives
- Execute user Python in sandbox: rejected for MVP (complex + risky).
- Custom syntax: deferred; Python DSL is fastest for MVP.

## Prior art
- Rust RFC template and process emphasize RFC writeup for major changes.
- Python PEPs define enhancement proposals as design docs with spec + rationale.
- Diátaxis separates reference from explanations; language spec belongs in reference.

## Unresolved questions
- Canonical bitstring ordering for counts (must be frozen globally).
- Whether static `if/for` is MVP or Post‑MVP.
- Whether CompilationService is public in MVP or internal only.

## Testing plan
Conformance suite required:
- golden source→AQO
- banned constructs → INVALID_ARGUMENT
- deterministic output hash

## Rollout plan
1) Accept this RFC.
2) Treat `docs/reference/eigen-lang/*` as source of truth.
3) Implement allowlist + limits.
4) Add conformance tests to CI.
