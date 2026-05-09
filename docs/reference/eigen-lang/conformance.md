# Eigen‑Lang conformance suite (MVP v0.1)

This document fixes the **current conformance baseline** for Eigen‑Lang and explicitly records what is still missing.

## Scope and purpose

Conformance protects the MVP language surface from silent drift and verifies that compiler behavior is reproducible.

The current suite validates:
- parser/validator safety behavior for the supported Python subset,
- deterministic AQO JSON emission and stable payload hashing,
- core metadata contracts used by downstream runtime components.

## Current implementation snapshot

The suite is currently implemented in the compiler service tests:

- Golden fixtures: `src/services/eigen-compiler/tests/golden/*/`
  - `program.eigen.py` — source fixture
  - `expected.aqo.json` — canonical AQO JSON output
- Negative fixtures: `src/services/eigen-compiler/tests/negative/*/request.json`
  - RPC input + expected gRPC status + expected BadRequest field violations
- Test runner: `src/services/eigen-compiler/tests/test_conformance_suite.py`

## What is covered now (implemented)

### 1) Deterministic compilation
- Same input must produce byte-identical AQO JSON.
- AQO JSON must match the fixture golden output.

### 2) Stable integrity metadata
- `metadata["aqo_sha256"]` must match the SHA‑256 of emitted AQO bytes.
- Hash value must remain stable across repeated compilations of identical input.

### 3) No synthetic gate inflation
- Compiler must not invent non-source quantum gates in MVP.
- For empty program body (`pass`), only terminal `MEASURE` is expected.

### 4) Distributed metadata determinism (MVP contract)
- `distributed.*` options are normalized into deterministic AQO `distributed_execution` fields.
- Metadata version markers are required and stable:
  - `distributed.execution_metadata_version`
  - `distributed.topology_hints_version`

### 5) Validation error contract
- Invalid requests must return gRPC status `INVALID_ARGUMENT` where expected.
- Structured `google.rpc.BadRequest.field_violations` must match fixture-declared fields.
- Negative fixtures currently include:
  - missing input,
  - missing job_id,
  - invalid syntax,
  - dynamic control flow,
  - unsupported language usage,
  - unsupported distributed target.

## CI enforcement

- CI runs `pytest` for `src/services/eigen-compiler` on pushes to `main` and pull requests.
- `tests/test_conformance_suite.py` is part of that gate and must stay green.

## Known conformance gaps (missing / TODO)

The items below are **not fully covered by conformance yet** and should be treated as next-priority additions:

1. **Feature-level matrix coverage**
   - No explicit per-feature matrix for all documented Eigen‑Lang surface areas in `syntax.md`, `semantics.md`, and `standard-library.md`.

2. **UNIMPLEMENTED boundary checks**
   - Missing dedicated suite cases that prove recognized-but-unsupported patterns map to `UNIMPLEMENTED` (where contractually required), rather than generic validation errors.

3. **Options schema conformance depth**
   - Distributed options are partially covered, but no complete contract suite exists for option normalization/versioning across the whole compiler options namespace.

4. **AQO semantic completeness checks**
   - Current golden fixtures are small and do not yet provide broad operator/parameter/qubit-addressing conformance matrix coverage.

5. **Cross-service contract conformance**
   - The suite is compiler-local; there is no dedicated end-to-end conformance layer proving System API → Kernel → Compiler expectations for Eigen‑Lang contract behavior.

6. **Performance/resource-limit conformance evidence**
   - There are no explicit conformance cases asserting boundary behavior for all configured compiler resource limits.

## Required process for golden updates

Golden fixtures are strict and require explicit review discipline.

When changing any `expected.aqo.json`:

1. Intentionally change compiler behavior.
2. Re-run conformance locally:
   - `cd src/services/eigen-compiler && pytest tests/test_conformance_suite.py`
3. Verify every golden diff is semantically intended (not formatting churn).
4. In PR description, add a **Golden Update** section listing:
   - changed fixture dirs,
   - reason for each change,
   - backward-compatibility impact.
5. Require explicit reviewer approval for golden diffs before merge.

## Related architecture alignment

This snapshot aligns with current architecture docs that mark the compiler as an AST-only deterministic MVP with explicit implemented/TODO separation. As compiler capabilities evolve, this conformance document must be updated in lockstep with:
- `docs/architecture/components/compiler.md`
- `docs/architecture/overview.md`
- `docs/architecture/contract-map.md`
