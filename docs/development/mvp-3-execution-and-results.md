# MVP-3 — Execution & Results Pipeline Plan

Status: **Completed (RFCs accepted, ADR package published)**
Last updated: **2026-04-25**

## Goal

Deliver a stable and observable runtime path from compiled AQO artifact to persisted job results on `sim:local`, including deterministic terminal states and a usable CLI monitoring/retrieval flow.

## Scope of MVP-3

### 1) Kernel runtime orchestration (compile → execute → terminal state)

Deliver `eigen-kernel` runtime behavior that:

- consumes validated `SubmitJobRequest` envelopes and resolved artifact references,
- executes explicit state transitions (`PENDING → COMPILING → RUNNING → DONE|ERROR`),
- records terminal metadata (timestamps, error codes, trace context),
- guarantees idempotent terminalization (terminal state written exactly once).

#### Acceptance criteria

- Integration tests verify allowed transitions and reject invalid transition attempts.
- Terminal status is deterministic and stable across repeated status polls.
- Runtime failures map to canonical error model with actionable diagnostics.

---

### 2) Driver-manager simulator execution contract

Deliver `driver-manager` behavior that:

- accepts AQO v0.1 payload and simulator target (`sim:local`),
- executes supported operation subset (`RX`, `RY`, `RZ`, `CX`, `MEASURE`),
- returns normalized execution output (`counts` + execution metadata),
- surfaces driver/runtime errors via internal gRPC status mapping.

#### Acceptance criteria

- Positive execution fixtures produce deterministic normalized result shape.
- Unsupported target/payload paths fail with clear internal error mapping.
- Driver API compatibility is covered by tests for request/response schema parity.

---

### 3) Result persistence and retrieval contract

Deliver end-to-end artifact lifecycle that:

- persists runtime outputs in canonical QFS paths for each `job_id`,
- keeps result metadata (`shots`, target, duration, trace/job correlation),
- serves immutable result payloads through `GetJobResults`,
- returns consistent not-ready / not-found semantics before terminal completion.

#### Acceptance criteria

- E2E smoke validates `submit → watch → results` with artifact existence checks.
- Repeated `results` calls for a completed job are byte-stable/logically identical.
- Error jobs expose structured failure details and do not produce success result artifacts.

---

### 4) CLI runtime UX (`status`, `watch`, `results`)

Deliver CLI behavior that:

- shows readable lifecycle progression for active jobs,
- exits correctly on terminal states (success and failure),
- fetches and renders normalized results for completed jobs,
- preserves non-zero exit behavior and actionable messages on failures.

#### Acceptance criteria

- CLI integration tests validate human-readable status transitions and terminal handling.
- `--watch` mode exits once terminal state is reached and does not hang.
- `results` output is consistent with `GetJobResults` payload and includes key metadata.

---

### 5) Runtime observability and reliability gates

Deliver minimum runtime quality controls:

- trace propagation across `system-api → kernel → driver-manager`,
- job lifecycle metrics (state counts, latency buckets, failures),
- structured logs with `job_id`, `trace_id`, service/component labels,
- CI smoke gates for runtime path and observability assertions.

#### Acceptance criteria

- Observability smoke tests pass for successful and failing execution paths.
- Metrics and logs include required correlation identifiers.
- CI blocks merge when runtime smoke or observability checks regress.

## Delivery checklist

- [x] Kernel state-machine runtime closure for execution lifecycle.
- [x] Driver-manager simulator execute path hardened and covered by contract tests.
- [x] Result persistence/retrieval contract validated with deterministic fixtures.
- [x] CLI `status/watch/results` behavior aligned with runtime contracts.
- [x] Runtime smoke + observability gates required in CI.
- [x] Documentation synchronized in reference, tutorials, and roadmap.


## Suggested execution order

1. Kernel terminal-state/idempotency guarantees.
2. Driver-manager execution contract and simulator fixtures.
3. QFS result persistence + `GetJobResults` consistency checks.
4. CLI runtime UX hardening (`status/watch/results`).
5. CI/runtime observability gates and documentation closure.

## Related documents

- MVP roadmap: [`../roadmap.md`](../roadmap.md)
- MVP-3 tracking issue: [`mvp-3-tracking-issue.md`](mvp-3-tracking-issue.md)
- MVP-3 RFC package: [`../../rfcs/0016-mvp3-kernel-driver-execution-contract.md`](../../rfcs/0016-mvp3-kernel-driver-execution-contract.md), [`../../rfcs/0017-mvp3-results-retrieval-and-cli-runtime-ux.md`](../../rfcs/0017-mvp3-results-retrieval-and-cli-runtime-ux.md), [`../../rfcs/0018-mvp3-runtime-observability-and-release-gates.md`](../../rfcs/0018-mvp3-runtime-observability-and-release-gates.md)
- MVP scope: [`../requirements/mvp-scope.md`](../requirements/mvp-scope.md)
- MVP DoD: [`mvp-definition-of-done.md`](mvp-definition-of-done.md)
- Contract freeze checklist: [`mvp-contract-freeze-checklist.md`](mvp-contract-freeze-checklist.md)
- Public gRPC reference: [`../reference/api/grpc-public.md`](../reference/api/grpc-public.md)
- Internal gRPC reference: [`../reference/api/grpc-internal.md`](../reference/api/grpc-internal.md)
