# Allowed AST subset (MVP) — Eigen‑Lang v0.1

> **Status snapshot (as of 2026-05-09):** this document is synchronized with the current compiler implementation and architecture docs. It separates **implemented now** behavior from **TODO / missing** items so MVP state is auditable.

This document defines the **mandatory allowlist policy** for the Eigen‑Lang compiler frontend and documents the current security/determinism restrictions.

## Why allowlist?

Eigen‑Lang is a Python DSL, but the compiler must be safe and deterministic. The compiler parses source into Python AST and must **not** execute user code.

Even AST-only parsing can be abused for DoS (CPU/memory explosion), so frontend validation is based on:
- strict node-level policy,
- strict call/import policy,
- bounded resource limits,
- deterministic rejection behavior.

## 1) Hard bans (validation rejection)

Implemented baseline bans:
- Dynamic code execution primitives: `exec`, `eval`, `compile`.
- Dynamic/platform modules from forbidden roots: `os`, `sys`, `subprocess`.
- Non-allowlisted import roots (only Eigen‑Lang package imports are allowed in MVP).
- Runtime/dynamic Python control flow constructs (see section 2).

Security intent (partially implemented in broader docs, but not fully enforced as semantic categories yet):
- No dynamic imports, unsafe metaprogramming, arbitrary host I/O/network behavior.

TODO / missing formalization:
- Publish one canonical forbidden-call taxonomy with stable machine-readable reason codes across compiler + docs.
- Explicitly document/implement `UNIMPLEMENTED` vs `INVALID_ARGUMENT` split for recognized-but-not-supported language patterns.

## 2) AST node/control-flow policy

### Implemented now (compiler-enforced)

- Source must be valid UTF-8 + valid Python syntax.
- Exactly one function with `@hybrid_program` is required.
- Dynamic runtime control-flow nodes are currently rejected in MVP validation path:
  - `if`, `for`, `while`, `match` and related runtime-dependent branching/loops.
- Compiler accepts AST shapes needed for the current lowering subset (gate calls + simple parameter declarations) and rejects unsupported patterns by default.

### Target allowlist shape (docs-level MVP intent)

The intended minimal allowlist family remains:
- `Module`, `FunctionDef`, `arguments`, `Return`
- `ImportFrom` (Eigen‑Lang package only)
- `Assign`, `AnnAssign` (simple)
- `Expr` (call)
- `Name`, `Constant`
- `Call` (allowlisted targets only)
- bounded literal containers (`Dict`/`List`/`Tuple`)
- numeric `BinOp` / `UnaryOp`

### TODO / gaps

- Align and freeze exact per-node allowlist in tests + docs as a single normative matrix (implemented vs planned per node).
- Decide whether compile-time-constant control flow (`if const`, `for range(const)`) is admitted in MVP or moved explicitly to post‑MVP (current code rejects dynamic control flow broadly).

## 3) Allowed call targets (MVP)

Implemented baseline:
- Calls must map to Eigen‑Lang stdlib/DSL symbols used by the current lowering pipeline.
- Supported lowering subset currently includes recognized gate calls and parameter patterns used for deterministic AQO generation (`rx`, `ry`, `rz`, `cx`, `Param(...)`).
- Arbitrary host/runtime call targets are rejected by validation policy.

TODO / gaps:
- Publish and test a canonical allowlisted-call table linked to `standard-library.md` with implementation status per symbol.
- Document attribute-chain policy unambiguously (`eigen_lang.<symbol>` vs imported aliases) and enforce identically in all frontend paths.

## 4) Resource limits (mandatory)

Compiler must guard parser/AST resources.

Implemented runtime knobs:
- `EIGEN_COMPILER_MAX_SOURCE_BYTES` (default: `262144`)
- `EIGEN_COMPILER_MAX_AST_NODES` (default: `50000`)
- `EIGEN_COMPILER_MAX_AST_DEPTH` (default: `200`)

Validation behavior:
- Exceeding limits must return a structured validation error.

TODO / gaps:
- Ensure source-bytes limit enforcement is explicitly verified end-to-end in compiler path and conformance fixtures.
- Add/standardize bounded literal container size checks as explicit test cases.

## 5) Validation error contract

Implemented baseline:
- Validation failures are returned as `INVALID_ARGUMENT` with structured field violations.

Required structure:
- use `BadRequest.FieldViolation` with:
  - `field`
  - `description`

TODO / gaps:
- Freeze stable field naming and reason taxonomy across all negative fixtures.
- Add compatibility report section that tracks validation contract drift release-to-release.

## 6) What is still missing to fix the system state

To fully “зафиксировать состояние системы” for this document family, the next mandatory closure items are:

1. **Single source of truth matrix**
   - One table: AST node / call / import rule / status (`Implemented`, `Rejected`, `Planned`) and reference to conformance fixture.
2. **Conformance coverage parity**
   - Negative fixture per rejection class + positive fixture per allowed construct in MVP scope.
3. **Error-code determinism**
   - Stable mapping of validation categories to structured reason codes and gRPC statuses.
4. **Docs synchronization gate**
   - CI/doc-check step that prevents architecture/reference drift for Eigen‑Lang subset contracts.

Until these items land, the compiler remains functional for MVP baseline, but the language-surface contract is still partially under-specified at the documentation/compliance level.
