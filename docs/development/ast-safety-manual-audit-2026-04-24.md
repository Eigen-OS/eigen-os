# Manual Security Audit — AST Safety Boundaries (MVP-2)

- **Date**: 2026-04-24
- **Scope**: `src/services/eigen-compiler/src/eigen_compiler/compiler.py`
- **Related RFC/ADR**: RFC 0014, ADR 0004
- **Audit type**: manual code audit + existing test coverage review

## Boundary definition audited

Compiler trust boundary:

1. accept untrusted source bytes,
2. parse with Python AST,
3. validate against MVP allowlist/limits,
4. emit deterministic AQO,
5. never execute user code.

## Checklist and findings

### 1) Runtime execution of user code
- **Check**: ensure no `exec`/`eval`/module execution path exists.
- **Result**: **PASS**.
- **Evidence**: compiler path uses `ast.parse(...)` and AST walkers only; no `importlib`, `exec`, or dynamic execution in compile path.

### 2) Import boundary restrictions
- **Check**: reject imports outside allowed roots.
- **Result**: **PASS**.
- **Evidence**: `_reject_forbidden_imports` enforces allowed prefix set and rejects disallowed roots.

### 3) Forbidden dynamic calls
- **Check**: reject direct dynamic code execution primitives and known dangerous module-root calls.
- **Result**: **PASS**.
- **Evidence**: `_reject_forbidden_calls` rejects `exec`/`eval`/`compile` and module-root calls on forbidden roots.

### 4) Structural DoS controls
- **Check**: enforce AST node/depth limits and clamp env-provided values.
- **Result**: **PASS**.
- **Evidence**: `_enforce_resource_limits` checks node/depth; `_compiler_limit` clamps to `>=1` and uses defaults on invalid env values.

### 5) Entrypoint ambiguity
- **Check**: reject zero or multiple `@hybrid_program` entrypoints.
- **Result**: **PASS**.
- **Evidence**: `_validate_single_entrypoint` enforces exactly one entrypoint.

### 6) Deterministic output
- **Check**: ensure stable AQO serialization.
- **Result**: **PASS**.
- **Evidence**: `json.dumps(..., sort_keys=True, separators=(",", ":"))`.

## Residual risk notes (non-blocking for MVP-2)

1. Call-attribute validation is intentionally minimal (module-root + call-name checks); this is acceptable for current MVP subset but should evolve to a stricter symbol resolver post-MVP.
2. Compiler currently rejects all dynamic control flow in MVP; future subset expansion should ship with explicit conformance fixtures first.

## Conclusion

Audit result: **MVP-2 AST safety boundary is acceptable for release readiness** with current constraints and conformance tests.
