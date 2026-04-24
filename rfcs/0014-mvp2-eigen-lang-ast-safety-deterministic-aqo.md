# RFC 0014: MVP-2 Eigen-Lang AST Safety and Deterministic AQO

- **Status**: Draft
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-24
- **Target Milestone**: Phase 0 (MVP-2)
- **Tracking Issue**: (to be created)
- **Replaces / Related**: RFC 0011, RFC 0012, ADR 0004

## Summary

Specify MVP-2 compiler guarantees for Eigen-Lang source processing: AST-only parsing, strict safety restrictions, deterministic AQO v0.1 generation, and consistent error semantics.

## Motivation

Compiler behavior is a core contract in MVP-2. The project needs a precise policy for what source constructs are allowed, what must be rejected, and how determinism is validated across runs and environments.

## Goals

- Ensure compiler never executes untrusted user code.
- Freeze MVP-2 allowlist and forbidden construct policy.
- Guarantee deterministic AQO output for identical inputs.
- Standardize diagnostics for unsupported constructs and malformed programs.

## Non-Goals

- Supporting full Python semantics in MVP-2.
- JIT/runtime interpretation of user programs.
- Optimizer passes beyond deterministic MVP subset lowering.

## Guide-level Explanation

For `program.eigen.py`, the compiler:

1. Parses source with Python AST utilities.
2. Verifies exactly one `@hybrid_program` entrypoint.
3. Applies structural safety limits (size, depth, symbols).
4. Enforces allowed language subset.
5. Emits canonical AQO JSON with stable ordering.

Invalid programs are rejected with actionable diagnostics; valid programs produce byte-stable AQO artifacts.

## Reference-level Design

## Interfaces / APIs

- Input: source file path + JobSpec compile context.
- Output: AQO v0.1 JSON artifact and submission metadata.
- Failure behavior:
  - `INVALID_ARGUMENT` for syntax/validation/allowlist failures.
  - `UNIMPLEMENTED` for explicitly unsupported but recognized patterns.

## Data Models

- AQO output must conform to v0.1 reference format.
- Instruction subset for MVP-2 includes deterministic lowering of `RX`, `RY`, `RZ`, `CX`, `MEASURE`.
- Emission format requires stable key order and canonical serialization.

## Security and Privacy

- Prohibit `exec`, `eval`, unrestricted imports, direct filesystem/network I/O.
- Apply AST node-count and depth limits.
- Do not permit dynamic code loading or runtime reflection paths.

## Observability

- Compiler logs include reason codes for reject paths.
- Emit counters for `accepted_programs`, `rejected_programs`, and reject category.
- Trace span boundaries for parse/validate/lower stages.

## Performance

- Complexity target remains linear in AST node count for validation phases.
- Deterministic serialization should not add superlinear overhead.
- Conformance tests include representative chains for regression tracking.

## Testing Plan

- Golden tests: valid source → canonical AQO.
- Negative tests: forbidden constructs and malformed entrypoints.
- Determinism tests: repeated compilation produces identical hash.
- CI gate: conformance suite mandatory on pull requests.

## Implementation / Migration

1. Publish enforceable allowlist reference.
2. Align compiler validator with allowlist + limits.
3. Lock deterministic serializer behavior in tests.
4. Add/update conformance fixtures and CI checks.
5. Move RFC to Accepted when implementation is complete.

## Considered Alternatives

- **Runtime sandbox execution**: rejected for MVP-2 complexity/security risk.
- **Loose deterministic policy (semantic-only)**: rejected; byte-stability is required for predictable tests.

## Open Questions

- Should specific static loop forms be permitted in MVP-2 or deferred?
- Is separate compile-only external endpoint needed post-MVP?
