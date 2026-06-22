# Compiler model migration notes

- **Applies to:** Compiler architecture, AQO reference, Eigen-Lang reference
- **Status:** Informational migration guidance
- **Date:** 2026-06-17

## What changed

The compiler now treats the semantic rule engine as authoritative. The neuro-symbolic layer is advisory only and must not be used as a source of truth for legality or lowering.

The compiler also records the resolved workload-family profile and the deterministic pass pipeline in metadata.

## What did not change

- AQO remains `1.0.0`.
- Eigen-Lang syntax remains the same.
- The top-level AQO schema does not gain new fields.
- Compiler suggestions remain optional and can be disabled without breaking the compiler.

## Migration guidance

- Treat compiler diagnostics and metadata as authoritative.
- Do not infer semantic validity from advisor scores.
- Use the recorded workload profile and pass pipeline when debugging compile-time failures.
- Expect advisor influence to appear only as accepted, rejected, or transformed into deterministic compiler actions.

## Related docs

- `docs/architecture/components/compiler.md`
- `docs/architecture/components/neuro-symbolic-core.md`
- `docs/architecture/adr/compiler-rule-engine-and-advisory-boundary.md`
- `docs/reference/formats/aqo.md`
- `docs/reference/eigen-lang.md`
