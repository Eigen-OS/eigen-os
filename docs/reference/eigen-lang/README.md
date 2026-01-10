# Eigen‑Lang Reference (v0.1)

This directory is the **source of truth** for the Eigen‑Lang specification.

- If you want to **change** Eigen‑Lang (syntax/semantics/stdlib/contracts): write or update an **RFC** first.
- If you want to **implement** Eigen‑Lang: follow the rules here and the conformance suite.

## Contents
- [`syntax.md`](syntax.md) — surface syntax and file conventions
- [`semantics.md`](semantics.md) — meaning of programs (hybrid DAG, quantum steps, measurements)
- [`allowed-subset.md`](allowed-subset.md) — **AST allowlist** and prohibited constructs (security/determinism)
- [`standard-library.md`](standard-library.md) — built‑in DSL functions (what is “the language” in MVP)
- [`mapping-to-aqo.md`](mapping-to-aqo.md) — mapping Eigen‑Lang constructs → AQO ops
- [`versioning.md`](versioning.md) — compatibility policy for Eigen‑Lang v0.x
- [`conformance.md`](conformance.md) — minimal conformance suite requirements

## Related contracts
- Job submission/packaging: `docs/reference/eigen-lang-submission.md`
- AQO format: `docs/reference/formats/aqo.md`
- Error rules: `docs/reference/error-model.md` + `docs/reference/error-mapping.md`
