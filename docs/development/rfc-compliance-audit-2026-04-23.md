# Docs ↔ Code Compliance Audit (MVP)

Date: 2026-04-24

## Scope

- Documentation reviewed under `docs/` with focus on MVP contracts:
  - `docs/requirements/mvp-scope.md`
  - `docs/development/mvp-definition-of-done.md`
  - `docs/architecture/contract-map.md`
  - `docs/reference/api/grpc-public.md`
- Implementation reviewed in:
  - `src/services/system-api`
  - `src/services/eigen-compiler`
  - `src/services/driver-manager`
  - `src/rust/apps/cli`
  - `proto/eigen/api/v1`

## Executive Summary

Current status: **partially compliant**.

- The repository has a solid MVP skeleton: public proto contracts, working System API smoke tests, AST-only compiler checks, and basic CLI submit/status/watch/results flow.
- However, several docs currently overstate implementation completeness (especially around full MVP command surface, kernel orchestration, RBAC authorization, and strict error semantics).
- Conclusion for MVP closeout: **docs need one reconciliation pass** so “done” claims match the actual shipped behavior.

## Compliance Matrix

### 1) CLI surface vs MVP docs

**Doc expectation**
- MVP scope states CLI commands include `submit`, `status`, `result`, `compile`, `visualize`.

**Code reality**
- Implemented commands are `submit`, `status`, `watch`, `results` (`result` alias), `help`, `version`.
- `compile` and `visualize` are not implemented.

**Status**: ❌ Drift (docs ahead of code)

---

### 2) System API orchestration model vs MVP docs

**Doc expectation**
- System API forwards validated requests to kernel; kernel handles pipeline.

**Code reality**
- `system-api` runs an in-memory stub job store and synthetic updates/results in `grpc_impl.py`.
- No kernel gRPC client integration in submit/status/results path.

**Status**: ❌ Drift (docs ahead of code)

---

### 3) Job status semantics and NOT_FOUND behavior

**Doc expectation**
- Unknown `job_id` should map to `NOT_FOUND` in public API error table.

**Code reality**
- `GetJobStatus` for missing job returns synthetic QUEUED status instead of gRPC `NOT_FOUND`.
- `GetJobResults` for missing job returns synthetic DONE + stub counts/metadata instead of `NOT_FOUND`.

**Status**: ❌ Drift (contract semantics mismatch)

---

### 4) Job lifecycle states in acceptance criteria

**Doc expectation**
- Acceptance criteria call out `PENDING → COMPILING → RUNNING → DONE` state visibility.

**Code reality**
- Default stream updates are `QUEUED → RUNNING → DONE`.
- No explicit `PENDING`/`COMPILING` state emitted in default path.

**Status**: ⚠️ Partial

---

### 5) Security model (authn vs authz)

**Doc expectation**
- MVP scope and API docs describe role-based permissions (`jobs:*`, `devices:*`) in addition to authn.

**Code reality**
- `security.py` enforces authentication mode (`allow_all` or static bearer token).
- No role extraction/authorization policy checks per method.

**Status**: ❌ Drift (docs ahead of code)

---

### 6) Compiler safety claims

**Doc expectation**
- AST-only compilation and restricted subset.

**Code reality**
- Compiler parses source via AST, rejects forbidden imports/calls and dynamic control flow, enforces AST limits, and emits deterministic AQO JSON.

**Status**: ✅ Aligned

---

### 7) Proto/CI contract checks

**Doc expectation**
- Buf lint and breaking checks are part of CI.

**Code reality**
- CI workflow includes `buf lint` and `buf breaking` job against `main`.

**Status**: ✅ Aligned

## Recommended Actions Before MVP Closeout

1. **Decide source of truth for current release messaging**:
   - either reduce docs claims to “MVP scaffold/skeleton”,
   - or finish missing implementation (kernel forwarding, NOT_FOUND semantics, authz, CLI compile/visualize).
2. **Normalize public error semantics** in `system-api` for unknown job/device IDs.
3. **Update acceptance criteria examples** to match actual event/state sequence (or implement missing states).
4. **Reconcile `grpc-public.md` and `contract-map.md` wording** around optional/public `CompilationService` and command surface.
5. Add a short “Current MVP Limitations (Implemented vs Planned)” section in `docs/requirements/mvp-scope.md`.

## Verification Commands Used

- `pytest -q src/services/system-api/tests`
- `cargo test -p cli --manifest-path src/rust/Cargo.toml`
