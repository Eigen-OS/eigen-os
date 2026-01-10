# Allowed AST subset (MVP) — Eigen‑Lang v0.1

This document defines the **mandatory allowlist** for the compiler frontend.

## Why allowlist?
Eigen‑Lang is a Python DSL, but the compiler must be safe and deterministic. The compiler **parses** code (AST) and must not execute it. Python’s `ast` module is designed for analysis (no name lookups, no execution), but parsing untrusted code can still be abused for DoS (CPU/memory). The compiler must enforce strict limits and a whitelist.

## 1) Hard bans (reject with INVALID_ARGUMENT)
- `exec`, `eval`, `compile`
- `importlib`, dynamic imports
- file/network I/O (`open`, `socket`, `requests`, etc.)
- `subprocess`, `os.system`, `ctypes`
- metaprogramming: decorators other than Eigen‑Lang ones

## 2) Allowed Python AST nodes (minimal MVP)
Allowed node families:
- Module, FunctionDef, arguments, Return
- ImportFrom (only `eigen_lang` package)
- Assign, AnnAssign (simple)
- Expr (call)
- Name, Constant
- Call (only to allowed symbols)
- Dict/List/Tuple (bounded sizes)
- BinOp/UnaryOp (numeric only)

Optional (can be Post‑MVP):
- If (compile‑time constants only)
- For (only `range(constant)`)

Everything else is rejected by default.

## 3) Allowed call targets
Allowed calls must resolve to:
- Eigen‑Lang stdlib symbols (see `standard-library.md`)
- constructors of declared DSL types (QubitRegister, Param, Observable, etc.)

No arbitrary attribute chains; allow only `eigen_lang.<symbol>` or imported symbols from `eigen_lang`.

## 4) Resource limits (mandatory)
- max source bytes (e.g., 256 KB)
- max AST nodes (e.g., 50k)
- max nesting depth (e.g., 200)
- max literal container size

If exceeded → return a clear validation error (choose status code consistently).

## 5) Validation error structure
Use BadRequest.FieldViolation in error details: field + description. 
