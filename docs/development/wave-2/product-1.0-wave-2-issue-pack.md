# Product 1.0 Wave 2 Issue Pack

This document is a ready-to-use set of GitHub issues for **Product 1.0 Wave 2 — Kernel/QRTX becomes lifecycle authority**.

**Context sources:**
- `docs/development/product-1.0-contract-alignment-plan.md`
- `docs/development/wave-2/product-1.0-wave-2-execution-plan.md`
- `docs/development/product-1.0-contract-inventory.md`
- `docs/development/product-1.0-version-policy.md`
- `docs/reference/api/grpc-internal.md`
- `docs/architecture/components/qrtx.md`
- `docs/architecture/contract-map.md`
- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/cluster-runtime-observability-contract.md`
- `docs/reference/error-model.md`
- `docs/reference/error-mapping.md`
- `rfcs/0050-product-1.0-kernel-qrtx-lifecycle-authority.md`
- `docs/adr/0036-product-1.0-kernel-qrtx-lifecycle-authority.md`

---

## Every implementation issue MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Internal API | Public API facade | Kernel state | QFS | Metrics | Trace context | Compatibility matrix | Migration docs -->
- **Compatibility**: <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker**: <!-- true | false -->
- **Migration Notes**: <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

## Release Notes Draft
```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## Milestone and labels

- **Milestone:** `Product 1.0 Wave 2 Kernel Lifecycle Authority`
- **Suggested labels:** `product-1.0`, `product-1.0-wave-2`, `kernel`, `qrtx`, `internal-api`, `lifecycle`, `orchestration`, `compatibility`, `conformance`

---

## Priority and ownership proposal

| Issue | Priority | Proposed owner group |
|---|---|---|
| W2-01 Internal KernelGateway contract matrix and canonical state machine | P0 | Kernel/QRTX + Architecture |
| W2-02 Durable/replayable kernel job state store and transition validator | P0 | Kernel/QRTX + Runtime Reliability |
| W2-03 System API lifecycle delegation cutover to Kernel/QRTX | P0 | System API + Kernel/QRTX |
| W2-04 Product 1.0 orchestration DAG control-plane skeleton | P0 | Kernel/QRTX + Compiler/Optimizer/Runtime owners |
| W2-05 Deadline propagation and cancellation fan-out | P0 | Kernel/QRTX + Driver Manager + Resource Manager |
| W2-06 Retry governance tied to canonical retryability | P1 | Kernel/QRTX + Reliability + Error Model owners |
| W2-07 Orchestration observability and trace continuity gate | P1 | Observability + Kernel/QRTX |
| W2-08 Wave 2 compatibility report, migration notes, and exit evidence bundle | P1 | Architecture/Governance + Tech Writing |

---

## Issues

### W2-01 — Internal KernelGateway contract matrix and canonical state machine

**Type:** Internal API Contract / Governance
**Labels:** `product-1.0-wave-2`, `kernel`, `internal-api`, `proto`, `compatibility`, `p0`

**Problem:** The current internal KernelGateway surface is smaller than the Product 1.0 reference. Implementation must not move lifecycle authority until the internal proto/reference/state-machine gaps are explicit and versioned.

**Scope**
- Build a method/message/field matrix from `docs/reference/api/grpc-internal.md` to `proto/eigen/internal/v1/kernel_gateway.proto` and shared internal types.
- Define canonical lifecycle states, terminal states, state aliases, transition rules, and invalid-transition error mapping.
- Decide event subscription semantics for job updates, including heartbeat, cursor/replay behavior, deadline behavior, and cancellation behavior.
- Define internal request metadata: security context, tenant/project, request ID, trace context, deadline, retry policy, and idempotency carry-through from Wave 1.
- Update Product 1.0 inventory/manifest mappings if concrete proto/test paths change.

**Acceptance Criteria**
- Matrix covers enqueue, status, cancel, results, updates/events, dispatch rationale, deadlines, retries, security context, and trace context.
- Canonical state-transition table is documented and has no ambiguous terminal-state behavior.
- Version impact and migration notes are recorded for any internal API breaking change.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
- **Compatibility**: <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker**: <!-- true | false -->
- **Migration Notes**: <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

## Release Notes Draft
```markdown
### Added
- 
### Changed
- 
### Fixed
- 
```

---

### W2-02 — Durable/replayable kernel job state store and transition validator

**Type:** Runtime Reliability / Kernel State
**Labels:** `product-1.0-wave-2`, `kernel`, `state-store`, `replay`, `p0`

**Problem:** Product 1.0 requires Kernel/QRTX to own lifecycle state. MVP state shortcuts are not sufficient for deterministic recovery, invalid-transition rejection, or audit evidence.

**Scope**
- Implement or define the first Product 1.0 state store abstraction for kernel jobs.
- Persist or replay enough data to reconstruct job ID, normalized request digest, lifecycle state, stage, timestamps, result references, cancellation intent, deadline, retry attempts, and last canonical error.
- Enforce transition validation in one kernel-owned path.
- Add crash/restart or replay fixture tests appropriate to the selected persistence grade.
- Document operational limitations if the first slice is fixture-backed rather than production-durable.

**Acceptance Criteria**
- Kernel state transitions are single-authority and testable.
- Invalid transitions fail with canonical internal errors and do not mutate state.
- Replay/restart tests prove deterministic reconstruction or explicitly bounded fixture behavior.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
- **Compatibility**: <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker**: <!-- true | false -->
- **Migration Notes**: <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

## Release Notes Draft
```markdown
### Added
- 
### Changed
- 
### Fixed
- 
```

---

### W2-03 — System API lifecycle delegation cutover to Kernel/QRTX

**Type:** Boundary Migration / Gateway Runtime
**Labels:** `product-1.0-wave-2`, `system-api`, `kernel`, `delegation`, `p0`

**Problem:** Public Wave 1 behavior is stable, but System API must stop owning Product 1.0 lifecycle mutations. Without a cutover, internal implementation remains inconsistent with architecture.

**Scope**
- Introduce or complete the System API-to-Kernel client/adapter for submit, watch/status, cancel, and result-reference retrieval.
- Preserve Wave 1 public envelope, idempotency, payload-limit, and canonical public error behavior.
- Map public request metadata into normalized internal metadata without leaking public-only fields into downstream services.
- Add regression tests proving public behavior remains unchanged while lifecycle state is delegated.
- Document migration from any MVP System API state store to kernel-owned state.

**Acceptance Criteria**
- Product 1.0 public lifecycle requests use Kernel/QRTX for authoritative state.
- System API direct lifecycle mutations are removed, disabled, or explicitly legacy-gated.
- Existing Wave 1 public conformance tests continue to pass.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
- **Compatibility**: <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker**: <!-- true | false -->
- **Migration Notes**: <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

## Release Notes Draft
```markdown
### Added
- 
### Changed
- 
### Fixed
- 
```

---

### W2-04 — Product 1.0 orchestration DAG control-plane skeleton

**Type:** Kernel Orchestration / Runtime Architecture
**Labels:** `product-1.0-wave-2`, `kernel`, `orchestration-dag`, `runtime`, `p0`

**Problem:** Kernel/QRTX must coordinate Product 1.0 lifecycle stages as a deterministic DAG rather than ad-hoc service calls.

**Scope**
- Model canonical DAG stages: validate/enqueue, compile, optimize, schedule, execute, persist, record knowledge/observability, finalize.
- Define stage input/output records and stable stage IDs for tracing and replay.
- Provide placeholder or real service-call adapters for compiler, optimizer, resource manager/scheduler, driver manager, QFS, and knowledge/observability handoff points.
- Ensure stage failures map to canonical lifecycle state and error metadata.
- Add submit-to-results integration tests with successful and failed stage paths.

**Acceptance Criteria**
- DAG execution produces deterministic lifecycle state and stage records.
- Stage boundaries are observable and replay-safe.
- Missing downstream production services are represented by explicit fixtures/adapters, not hidden System API shortcuts.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
- **Compatibility**: <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker**: <!-- true | false -->
- **Migration Notes**: <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

## Release Notes Draft
```markdown
### Added
- 
### Changed
- 
### Fixed
- 
```

---

### W2-05 — Deadline propagation and cancellation fan-out

**Type:** Reliability / Runtime Control
**Labels:** `product-1.0-wave-2`, `kernel`, `deadline`, `cancellation`, `p0`

**Problem:** Product 1.0 cancellation and deadlines must be enforced by Kernel/QRTX and propagated to downstream work, reservations, and result persistence.

**Scope**
- Define deadline normalization from public and internal requests.
- Propagate cancellation intent to queued, compiling, optimizing, scheduled, executing, and persisting stages.
- Release or mark resource reservations when cancellation/deadline occurs.
- Ensure cancellation races are deterministic for terminal states.
- Add tests for cancellation while queued, compiling, executing, and finalizing where dependencies exist.

**Acceptance Criteria**
- Cancellation fan-out is idempotent and produces canonical terminal state.
- Deadline expiry maps to canonical timeout behavior.
- Trace and metrics records show cancellation/deadline propagation without unbounded labels.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
- **Compatibility**: <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker**: <!-- true | false -->
- **Migration Notes**: <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

## Release Notes Draft
```markdown
### Added
- 
### Changed
- 
### Fixed
- 
```

---

### W2-06 — Retry governance tied to canonical retryability

**Type:** Runtime Reliability / Error Semantics
**Labels:** `product-1.0-wave-2`, `kernel`, `retries`, `errors`, `p1`

**Problem:** Retries must be governed by canonical retryability metadata and bounded policy; otherwise Wave 2 can hide errors, duplicate downstream work, or produce non-deterministic lifecycle state.

**Scope**
- Define retry policy input: max attempts, backoff, retryable reasons, non-retryable reasons, and deadline interaction.
- Use `docs/reference/error-model.md` and `docs/reference/error-mapping.md` as the taxonomy for retry decisions.
- Persist retry attempt records and final failure reason in kernel state.
- Emit retry metrics/traces required by orchestration observability.
- Add tests for retryable, non-retryable, exhausted, and deadline-interrupted retries.

**Acceptance Criteria**
- Retry behavior is deterministic, bounded, and state-store visible.
- Non-retryable failures do not retry.
- Exhausted retries produce canonical terminal error state and evidence.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
- **Compatibility**: <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker**: <!-- true | false -->
- **Migration Notes**: <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

## Release Notes Draft
```markdown
### Added
- 
### Changed
- 
### Fixed
- 
```

---

### W2-07 — Orchestration observability and trace continuity gate

**Type:** Observability / Conformance
**Labels:** `product-1.0-wave-2`, `observability`, `metrics`, `tracing`, `p1`

**Problem:** Lifecycle authority movement must not be invisible. Kernel/QRTX must emit contract metrics and preserve trace continuity from public ingress through internal DAG stages.

**Scope**
- Emit required orchestration contract markers and stage metrics with bounded labels.
- Preserve trace/request IDs from System API through Kernel/QRTX and downstream adapters.
- Add logs/audit records for enqueue, transition, cancel, retry, dispatch rationale, result reference, and terminal state.
- Add smoke/conformance tests for Prometheus output and trace continuity.
- Document any metric intentionally deferred to later scheduler/resource waves.

**Acceptance Criteria**
- Kernel/QRTX exposes `eigen_orch_contract_info` or approved equivalent contract marker.
- Required labels are bounded and fixture-tested.
- Trace continuity survives retry and cancellation paths.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
- **Compatibility**: <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker**: <!-- true | false -->
- **Migration Notes**: <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

## Release Notes Draft
```markdown
### Added
- 
### Changed
- 
### Fixed
- 
```

---

### W2-08 — Wave 2 compatibility report, migration notes, and exit evidence bundle

**Type:** Governance / Release Evidence
**Labels:** `product-1.0-wave-2`, `compatibility`, `release-evidence`, `p1`

**Problem:** Wave 2 can include major internal changes. Closure requires explicit compatibility, migration, and evidence records before Wave 3 begins.

**Scope**
- `docs/development/wave-2/product-1.0-wave-2-compatibility-report.md`
- `docs/development/wave-2/product-1.0-wave-2-release-readiness-checklist.md`
- `docs/development/wave-2/product-1.0-wave-2-exit-evidence-bundle.md`.
- Update RFC/ADR gap analysis if implementation discovers ungoverned contract decisions.
- Update Product 1.0 manifest/inventory for concrete proto/schema/conformance mappings.

**Acceptance Criteria**
- Every Wave 2 issue has completed versioning and release-note blocks.
- All breaking internal changes have migration notes and release evidence.
- Exit evidence includes exact commands, artifacts, owners, and known limitations.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
- **Compatibility**: <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker**: <!-- true | false -->
- **Migration Notes**: <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

## Release Notes Draft
```markdown
### Added
- 
### Changed
- 
### Fixed
- 
```
