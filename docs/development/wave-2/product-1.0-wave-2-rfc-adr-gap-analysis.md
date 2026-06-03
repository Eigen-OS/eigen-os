# Product 1.0 Wave 2 RFC/ADR Gap Analysis

## Goal

Identify whether the current RFC/ADR set is sufficient for **Wave 2 — Kernel/QRTX becomes lifecycle authority** in the Product 1.0 contract-alignment program.

## Inputs

- `docs/development/product-1.0-contract-alignment-plan.md`
- `docs/development/product-1.0-contract-inventory.md`
- `docs/development/product-1.0-version-policy.md`
- `docs/development/wave-2/product-1.0-wave-2-execution-plan.md`
- `docs/reference/api/grpc-internal.md`
- `docs/architecture/components/qrtx.md`
- `docs/architecture/contract-map.md`
- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/cluster-runtime-observability-contract.md`
- `docs/reference/multi-device-execution-contract.md`
- `rfcs/0016-mvp3-kernel-driver-execution-contract.md`
- `rfcs/0026-phase5-cluster-runtime-control-plane-contract-v1.md`
- `rfcs/0027-phase5-distributed-queue-and-delivery-semantics-v1.md`
- `rfcs/0028-phase5-distributed-tracing-and-execution-topology-contract-v1.md`
- `rfcs/0038-phase8b-qrtx-scheduling-and-lifecycle-hardening-contract-v1.md`
- `rfcs/0040-phase8b-runtime-data-observability-and-slo-gates-v1.md`
- `rfcs/0049-product-1.0-public-api-jobspec-error-boundary.md`

---

## Coverage matrix

| Wave 2 requirement | Existing spec coverage | Gap decision |
|---|---|---|
| Kernel/QRTX as canonical lifecycle authority instead of System API-owned MVP state | MVP and phase RFCs describe kernel execution and lifecycle hardening, but not the Product 1.0 cutover from Wave 1 public gateway semantics to kernel-owned lifecycle state. | **Gap: formalize Product 1.0 kernel authority cutover.** |
| Internal KernelGateway coverage for enqueue, status, cancel, results, updates/events, dispatch rationale, deadlines, retries, security context, and trace context | `docs/reference/api/grpc-internal.md` describes target service methods and metadata; current proto/RFC coverage is narrower and split across earlier phases. | **Gap: formalize Wave 2 internal API expansion and compatibility policy.** |
| Canonical lifecycle state machine and invalid-transition errors | Earlier docs list states, but do not provide a Product 1.0 transition table tied to canonical error mapping and replay evidence. | **Gap: formalize state machine and invalid-transition obligations.** |
| Durable or replayable kernel job state store | Phase lifecycle hardening discusses reliability, but not the Product 1.0 evidence requirements for replay/restart before Wave 3. | **Gap: formalize state-store minimum and closure evidence.** |
| System API lifecycle delegation while preserving Wave 1 public behavior | RFC 0049 stabilizes public behavior but intentionally defers internal ownership movement. | **Gap: formalize delegation contract and public-regression gate.** |
| Orchestration DAG skeleton for compile, optimize, schedule, execute, persist, record, finalize | Architecture docs describe data flow and QRTX responsibility; earlier RFCs do not define the Product 1.0 DAG handoff needed by Wave 3. | **Gap: formalize DAG stage records and placeholder adapter rules.** |
| Deadline propagation, cancellation fan-out, and retry governance | Existing error, tracing, queue, and lifecycle RFCs cover pieces, but not a single Product 1.0 kernel-owned rule set. | **Gap: formalize deadline/cancel/retry governance.** |
| Orchestration observability and trace continuity evidence | Observability contracts exist and are normative; Wave 2 needs binding implementation gates for kernel ownership movement. | **Gap: formalize Wave 2 observability gates.** |
| Compatibility/migration discipline for internal major changes | RFC 0032 and Product 1.0 version policy are sufficient. | **No new gap; apply strictly.** |

---

## Decision

A dedicated Product 1.0 Wave 2 RFC and ADR are required because existing MVP/phase RFCs do not encode the complete Product 1.0 lifecycle-authority cutover from System API to Kernel/QRTX.

- **Action:** introduce `rfcs/0050-product-1.0-kernel-qrtx-lifecycle-authority.md`.
- **ADR impact:** publish `docs/adr/0036-product-1.0-kernel-qrtx-lifecycle-authority.md` and index it in `docs/adr/README.md`.
- **Versioning impact:** RFC 0050 explicitly permits MAJOR internal API and lifecycle-behavior changes when required to align `eigen.internal.v1` and Kernel/QRTX with Product 1.0. Public Wave 1 behavior remains protected unless a separate public RFC/ADR approves a breaking public change.

---

## Follow-up checklist

- [ ] Review RFC 0050 with Kernel/QRTX, System API, Runtime Reliability, Observability, and Architecture/Governance owners.
- [ ] Keep ADR 0036 synchronized with accepted RFC 0050 decisions.
- [ ] Update the Wave 2 compatibility report when internal methods, lifecycle states, errors, metrics, or state persistence semantics change.
- [ ] Ensure every Wave 2 GitHub issue contains the required Versioning & Compatibility and Release Notes Draft blocks.
- [ ] Update Product 1.0 manifest/inventory when planned proto/schema/conformance mappings become concrete.
