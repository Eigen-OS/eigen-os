# Product 1.0 Wave 2 Execution Plan

**Wave:** Product 1.0 Wave 2 — Kernel/QRTX becomes lifecycle authority
**Status:** Ready for implementation planning
**Created:** 2026-06-02
**Parent plan:** `docs/development/product-1.0-contract-alignment-plan.md`
**Inventory:** `docs/development/product-1.0-contract-inventory.md`
**Version policy:** `docs/development/product-1.0-version-policy.md`
**RFC/ADR baseline:** `rfcs/0050-product-1.0-kernel-qrtx-lifecycle-authority.md`; `docs/adr/0036-product-1.0-kernel-qrtx-lifecycle-authority.md`
**Sources of truth:** `docs/architecture/**`, `docs/reference/**`

---

## 1. Goal

Wave 2 moves Product 1.0 lifecycle authority from MVP-era System API state handling into Kernel/QRTX. After this wave, System API remains the public gateway and compatibility boundary, while Kernel/QRTX owns the canonical internal lifecycle state machine, orchestration DAG, retries, deadlines, cancellation fan-out, result references, and orchestration observability.

Wave 2 is a **major internal contract alignment wave**. It may introduce breaking changes to `eigen.internal.v1` and internal lifecycle behavior when required to reconcile implementation with the Product 1.0 architecture and references. Public `eigen.api.v1` behavior must remain compatible with Wave 1 unless a separate public RFC/ADR explicitly approves a breaking public change.

---

## 2. Normative source map

| Wave 2 area | Canonical source | Implementation surface | Primary evidence |
|---|---|---|---|
| Kernel/QRTX lifecycle authority | `docs/architecture/components/qrtx.md`; `docs/reference/api/grpc-internal.md` | `proto/eigen/internal/v1/kernel_gateway.proto`; `src/rust/crates/eigen-kernel` | Kernel conformance and integration tests |
| Internal metadata, security, trace context | `docs/reference/api/grpc-internal.md`; `docs/architecture/components/security-isolation.md` | Internal proto common types; System API-to-kernel adapter | Metadata propagation tests |
| Public-to-internal delegation | `docs/architecture/components/system-api.md`; Wave 1 public boundary docs | `src/services/system-api` adapter/client | Public API regression tests plus delegation tests |
| Orchestration DAG | `docs/architecture/data-flow.md`; `docs/architecture/contract-map.md`; `docs/reference/api/grpc-internal.md` | Kernel workflow planner/executor | Submit-to-results integration tests |
| Retry/deadline/cancellation semantics | `docs/reference/error-model.md`; `docs/reference/error-mapping.md`; `docs/reference/api/grpc-internal.md` | Kernel retry controller; downstream service clients | Retryability and cancellation integration tests |
| Results references and persistence handoff | `docs/reference/formats/qfs-layout.md`; `docs/architecture/components/qfs.md` | Kernel/QFS boundary and public result facade | Result-reference tests; QFS fixture checks |
| Orchestration observability | `docs/reference/orchestration-observability-contract.md`; `docs/reference/cluster-runtime-observability-contract.md` | Observability exporter; kernel tracing | Metrics/tracing conformance tests |
| Multi-device split/merge readiness | `docs/reference/multi-device-execution-contract.md`; `docs/architecture/components/resource-manager.md`; `docs/architecture/components/driver-manager.md` | Kernel DAG extension points; Resource Manager/Driver Manager requests | Split/merge interface fixture tests |

---

## 3. Wave 2 scope

### In scope

1. Expand and align internal KernelGateway service contracts for enqueue, status, cancel, results, event subscription, dispatch rationale, deadline/retry policy, security context, and trace context.
2. Define and enforce a canonical Product 1.0 lifecycle state machine with invalid-transition errors.
3. Introduce durable or replayable kernel job state ownership.
4. Move lifecycle mutation authority out of System API into Kernel/QRTX delegation paths.
5. Implement the orchestration DAG skeleton for compile, optimize, schedule, execute, persist, observe/record, and finalize.
6. Propagate deadlines and cancellations to compiler, optimizer, scheduler/resource manager, driver manager, QFS, and knowledge/observability handoff points as each integration exists.
7. Govern retries through canonical error retryability metadata and bounded retry policy.
8. Emit orchestration metrics/logs/traces required by the orchestration and cluster-runtime observability contracts.
9. Add end-to-end and crash/restart evidence proving lifecycle state is deterministic and replay-safe.

### Out of scope

- Full compiler/Eigen-Lang/AQO closure; owned by Wave 3.
- Full Resource Manager scheduling authority closure; governed by later scheduling/resource waves unless needed as a Wave 2 stubbed dependency.
- Public REST API mirror implementation.
- New public lifecycle states or public `eigen.api.v1` breaking changes unless separately approved.
- Provider-specific driver execution semantics beyond cancellation/deadline/retry propagation hooks.

---

## 4. Delivery sequence

| Step | Issue | Dependency | Outcome |
|---:|---|---|---|
| 1 | W2-01 Internal KernelGateway contract matrix and state model | Wave 1 closure | Accepted internal proto/reference/state-machine delta plan |
| 2 | W2-02 Durable/replayable kernel job state store | W2-01 | Kernel owns persisted lifecycle records and transition validation |
| 3 | W2-03 System API lifecycle delegation cutover | W2-01, W2-02 | System API delegates lifecycle mutations and reads to Kernel/QRTX |
| 4 | W2-04 Orchestration DAG control-plane skeleton | W2-02 | Compile→optimize→schedule→execute→persist→finalize DAG is modeled |
| 5 | W2-05 Deadline and cancellation fan-out | W2-03, W2-04 | Cancellation/deadline semantics reach downstream tasks and reservations |
| 6 | W2-06 Retry governance and canonical failure taxonomy | W2-04 | Retryable/non-retryable failures are deterministic and observable |
| 7 | W2-07 Orchestration observability and trace continuity | W2-03 through W2-06 | Contract metrics/traces/log markers are emitted with bounded labels |
| 8 | W2-08 Wave 2 compatibility, migration, and exit evidence | All W2 issues | Closure report, readiness checklist, and evidence bundle are complete |

---

## 5. Contract decisions required before implementation

1. **State names and aliases:** internal states must map to canonical states in `docs/reference/api/grpc-internal.md`. Any legacy aliases must be documented as migration behavior.
2. **Event stream shape:** decide whether `PollJobUpdates` remains server streaming or is replaced/augmented by a cursor-based event subscription for replay.
3. **Result reference model:** define whether kernel returns QFS handles, signed references, logical artifact IDs, or public-facade references.
4. **Dispatch rationale:** decide minimum Product 1.0 rationale payload required for audit/explainability without leaking provider-private data.
5. **Persistence grade:** choose durable store, replay log, or deterministic in-memory fixture store for the first implementation slice; production closure requires restart/replay evidence.
6. **Internal SemVer:** classify `eigen.internal.v1` deltas as MAJOR/MINOR/PATCH under the Product 1.0 version policy and document migration steps.

---

## 6. Definition of done

Wave 2 is 100% complete when:

- KernelGateway internal proto/reference coverage has no unexplained gaps.
- Kernel/QRTX owns the canonical lifecycle state machine and rejects invalid transitions canonically.
- System API no longer mutates lifecycle state directly for Product 1.0 public requests.
- Public Wave 1 behavior remains regression-tested while internal ownership changes.
- The orchestration DAG records deterministic stage transitions and result references.
- Cancellation, deadline, and retry policy are propagated and tested across queued, compiling, executing, and persistence paths where dependencies exist.
- Orchestration metrics, logs, and traces satisfy the relevant reference contracts with bounded labels.
- Crash/restart or replay tests prove lifecycle state can be reconstructed or safely resumed.
- Product 1.0 manifest/inventory are updated when proto/schema/conformance mappings become concrete.
- The Wave 2 compatibility report, migration notes, release-readiness checklist, and exit evidence bundle have no unresolved `TBD` values.

---

## 7. Handoff to Wave 3

Wave 3 may start when Wave 2 evidence proves that Kernel/QRTX can orchestrate a compilation placeholder or real compilation request through deterministic lifecycle states without relying on System API-owned state. Wave 3 then replaces compiler placeholders with the production Eigen-Lang/AQO contract boundary while preserving Kernel-owned lifecycle, deadline, cancellation, retry, and observability semantics.
