# MVP Scope & Requirements (Baseline Freeze)

## Summary

This document fixes the **MVP baseline** for Eigen OS and records what is currently delivered versus what is explicitly missing.

- **Baseline date:** 2026-05-11
- **Purpose:** preserve MVP boundaries while the project advances through post-MVP phases.
- **Source of truth for current architecture/contracts:** `docs/architecture/*` and `docs/reference/*`.

---

## 1) MVP Baseline (what MUST be considered part of MVP)

### 1.1 Core runtime path

1. Submit JobSpec.
2. Validate and register job.
3. Compile Eigen-Lang (AST-safe subset) to AQO.
4. Execute on `sim:local` through driver-manager.
5. Persist artifacts and return status/results.

### 1.2 MVP components

- `system-api` (public API surface + request validation + authn/authz baseline)
- `eigen-kernel` (job lifecycle/state machine + orchestration glue)
- `eigen-compiler` (deterministic AST-only compilation)
- `driver-manager` (simulator backend integration)
- `eigen-cli` (submit/status/result + developer-facing flows)

### 1.3 MVP contracts and artifacts

- JobSpec as primary input contract
- AQO as canonical compilation output
- QFS layout/canonical artifact paths for per-job persistence
- Public/internal gRPC contracts for submission, status, results, and device discovery
- Baseline error model + error mapping

- JobSpec as primary input contract
- AQO as canonical compilation output
- QFS layout/canonical artifact paths for per-job persistence
- Public/internal gRPC contracts for submission, status, results, and device discovery
- Baseline error model + error mapping

- Structured logs with correlation identifiers
- Metrics/tracing baseline for core services
- API-key-style authentication baseline
- AST-only code handling (no arbitrary user-code execution in runtime)
facts are retrievable from CircuitFS

---

## 2) Current status against MVP baseline (as of 2026-05-11)

## 2.1 Delivered and stable in repository

- MVP-1, MVP-2, MVP-3 closure artifacts are present.
- Architecture and contract documentation has moved beyond MVP and covers Phases 1-7.
- Baseline execution path (submit → compile → execute → results) is documented and versioned.

## 2.2 Important clarification

The project has progressed beyond MVP (orchestration, benchmarking, intelligent runtime, distributed execution, governance/versioning), but these do **not** redefine MVP itself. They are post-MVP layers built on top of the MVP baseline.

---

## 3) Explicitly out of MVP scope

The following are valuable but **must not** be treated as MVP requirements:

- Real hardware production integrations as MVP-critical path
- Multi-node HA/failover guarantees
- Full multi-tenant policy/quotas/billing isolation
- Advanced autonomous optimization/ML as mandatory path
- Rich UI/dashboard as required interface
- Ecosystem plugin GA maturity as MVP gate
- Strict enterprise SLO/SLA commitments beyond baseline operability

---

## 4) What is missing to call MVP baseline fully “operationally closed”

> This section captures practical gaps that should be closed to make MVP status auditable and reproducible, even in a post-MVP repository.

### 4.1 Single canonical MVP conformance pack

Missing:

- A single machine-runnable conformance bundle that proves MVP end-to-end behavior from one command.
- Stable golden fixtures tying JobSpec input → AQO output → result artifact shape.

Needed outcome:

- `make test-mvp`/equivalent gate with deterministic pass/fail.

### 4.2 Production-like non-functional evidence for MVP targets

Missing:

- Published benchmark evidence tied to MVP NFR thresholds (latency, concurrency, persistence) with reproducible methodology.

Needed outcome:

- Versioned report + CI or scheduled validation job for MVP NFR claims.

### 4.3 Traceable requirement-to-test matrix for MVP only

Missing:

- A compact matrix linking each MVP FR/NFR requirement to concrete test IDs, fixtures, and CI jobs.

Needed outcome:

- `docs/requirements/mvp-traceability-matrix.md` (or equivalent) as release artifact.

### 4.4 Explicit deprecation rule for MVP contract behavior

Missing:

- Clear statement of how long MVP contract behavior remains guaranteed once post-MVP features evolve.

Needed outcome:

- Compatibility note binding MVP behavior to SemVer and migration policy.

---

## 5) Revised MVP functional requirements (frozen)

### FR-1 Submission and validation

- System accepts valid JobSpec and rejects malformed input deterministically.
- Authn/authz baseline is enforced before job acceptance.
- 
### FR-2 Compilation

- Compiler processes allowed Eigen-Lang subset only.
- AQO artifact is deterministic for equivalent input.

### FR-3 Execution

- Kernel/driver-manager execute on simulator path (`sim:local`).
- Terminal job state and normalized result payload are persisted.

### FR-4 Retrieval

- Client can query status and fetch final results.
- Error responses follow documented error model/mapping.

### FR-5 Persistence

- Job artifacts are stored in canonical QFS layout and remain retrievable for defined retention window.

### FR-6 Observability

- Core services expose baseline logs/metrics/tracing sufficient to reconstruct a failed job path.

---

## 6) Revised MVP non-functional requirements (frozen)

- **Determinism:** same input + same config ⇒ equivalent AQO and stable state transitions.
- **Recoverability:** restarts do not corrupt persisted job artifacts/state.
- **Operability:** failures are diagnosable via logs/metrics/traces without source-level debugging.
- **Security baseline:** no unsafe runtime execution of user code; API access controlled by baseline auth.
- **Compatibility discipline:** MVP contract changes must follow documented versioning/migration policy.

---

## 7) Acceptance criteria for MVP freeze validation

MVP baseline is considered valid when all conditions hold:

1. End-to-end simulator job succeeds from CLI/API with persisted artifacts.
2. Invalid input produces deterministic typed errors.
3. Status lifecycle is observable and terminal state is unique.
4. Result payload matches documented contract schema.
5. Conformance suite and traceability matrix are versioned and reproducible.

---

## 8) Relationship to post-MVP phases

- Post-MVP phases may extend runtime behavior and add new contracts.
- They must remain backward-compatible with MVP guarantees unless a versioned breaking change is explicitly declared.
- MVP baseline remains a regression floor, not an innovation ceiling.
