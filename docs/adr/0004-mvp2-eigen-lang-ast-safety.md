# ADR 0004: MVP-2 Eigen-Lang AST safety and deterministic AQO generation

- **Status:** Accepted
- **Date:** 2026-04-24
- **Deciders:** Core architecture maintainers

## Context

Compiler implementation for MVP-2 must stay safe (no code execution) and deterministic (repeatable AQO output).

## Decision

1. Compilation is **AST-only** via `ast.parse`; executing user code is forbidden.
2. Compiler enforces a strict MVP subset:
   - exactly one `@hybrid_program` entrypoint,
   - bounded AST complexity (node/depth limits),
   - forbidden unsafe constructs (`exec`, unsupported imports, raw I/O patterns).
3. Output format is AQO v0.1 with deterministic JSON serialization.
4. Unsupported syntax or safety violations map to `INVALID_ARGUMENT`.

## Consequences

- Compiler behavior is reproducible and safe for MVP.
- Golden AQO fixtures become a reliable compatibility mechanism.
- Language extensions require explicit RFC/ADR updates.

## Related

- MVP-2 plan: `docs/development/mvp-2-compilation-pipeline.md`
- Eigen-Lang reference: `docs/reference/eigen-lang/README.md`
- AQO reference: `docs/reference/formats/aqo.md`