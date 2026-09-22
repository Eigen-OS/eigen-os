# Product 1.0 Wave 4 Execution Plan

**Wave:** Product 1.0 Wave 4 — QFS data fabric maturity, security alignment, public mirror closure, and release evidence  
**Status:** Completed — closure evidence published  
**Created:** 2026-06-06  
**Parent plan:** `docs/development/product-1.0-contract-alignment-plan.md`  
**Inventory:** `docs/development/product-1.0-contract-inventory.md`  
**Version policy:** `docs/development/product-1.0-version-policy.md`  
**Source of truth:** `docs/architecture/**`, `docs/reference/**`

---

## 1. Goal

Wave 4 turns the QFS contract from a partially implemented artifact store into a mature data-fabric boundary with durable lineage, checkpoints, and live-resource semantics. It also closes the remaining Product 1.0 public-surface gaps around authorization, REST parity, Knowledge Base integration, observability, and release evidence so that runtime decisions, artifacts, and policy state are all traceable through the same contract-first path.

Wave 4 is a **major internal contract alignment wave**. It may change QFS internal storage behavior, checkpoint semantics, live qubit / reservation semantics, security enforcement details, and non-canonical public mirror plumbing when required to reconcile implementation with the normative references. Public `eigen.api.v1` semantics must remain compatible unless a specific public RFC/ADR approves the change.

The Wave 4 closure record is complete once the compatibility report, release-readiness checklist, exit evidence bundle, and RFC/ADR gap analysis are published alongside the Wave 4 slice evidence.

---

## 2. Normative source map

| Wave 4 area | Canonical source | Implementation surface | Primary evidence |
|---|---|---|---|
| QFS L3 artifact store | `docs/reference/formats/qfs-layout.md`; `docs/architecture/components/qfs.md` | QFS storage backend, artifact manifests, integrity checks | Artifact persistence and round-trip tests |
| QFS L2 checkpoint / state store | `docs/reference/formats/qfs-layout.md`; `docs/architecture/components/qfs.md` | Checkpoint envelope, restore path, retention policy | Checkpoint compatibility tests |
| QFS L1 live qubit / reservation semantics | `docs/architecture/components/qfs.md`; `docs/architecture/contract-map.md` | Live resource manager boundary, reservation tokens, TTLs | Reservation and stale-lease tests |
| Security and isolation baseline | `docs/reference/security/authz.md`; `docs/architecture/components/security-isolation.md` | Authn/authz, service identity, audit sink, fail-closed policy | Security conformance tests |
| Public REST mirror | `docs/reference/api/rest-public.md`; `docs/reference/api/benchmark-run.md`; `docs/reference/api/explain-backend-selection.md` | REST schema artifacts, request/response mapping, error envelope parity | REST schema and error tests |
| Knowledge Base public records and decision logs | `docs/architecture/components/knowledge-base.md`; `docs/reference/api/grpc-public.md` | KB record APIs, provenance hooks, decision-log ingestion | KB record and lineage tests |
| Observability and release evidence | `docs/reference/orchestration-observability-contract.md`; `docs/reference/benchmark-observability-contract.md`; `docs/reference/cluster-runtime-observability-contract.md` | Contract markers, bounded labels, trace continuity | Metrics / trace continuity tests |

---

## 3. Wave 4 scope

### In scope

1. Finalize the QFS artifact layout and metadata contract for durable artifact persistence.
2. Implement immutable storage behavior, digest checks, and retention rules for QFS L3.
3. Define the QFS checkpoint envelope and restore compatibility checks for QFS L2.
4. Decide and implement the QFS L1 ownership model for live qubit / reservation semantics.
5. Close the security baseline with authenticated ingress, service identity, fail-closed policy, and immutable audit records.
6. Add REST schema artifacts and conformance tests for the public mirror endpoints.
7. Wire Knowledge Base record and decision-log paths into the runtime and benchmark flows.
8. Emit contract markers, bounded-label metrics, and trace continuity evidence for the above boundaries.
9. Publish the Wave 4 compatibility, readiness, exit-evidence, and RFC/ADR closure records.

### Out of scope

- Full Resource Manager scheduling authority closure, which remains the Wave 5 concern.
- Full Driver Manager finalization, which remains the Wave 6 concern.
- Optimizer productionization, which remains the Wave 7 concern.
- Public API breaking changes beyond the approved mirror/schema envelope work.

---

## 4. Delivery sequence

| Step | Issue | Dependency | Outcome |
|---:|---|---|---|
| 1 | W4-01 QFS L3 artifact persistence, metadata, and integrity | Wave 3 artifact handoff complete | Stable artifact store with lineage and checksum verification |
| 2 | W4-02 QFS L2 checkpoint envelope and restore compatibility | W4-01 | Durable checkpointing with explicit compatibility checks |
| 3 | W4-03 QFS L1 live qubit / reservation ownership decision and implementation slice | W4-01, W4-02 | One explicit authority owns live-resource semantics |
| 4 | W4-04 Security and isolation hardening | Wave 1 public surface exists; authz contract available | Fail-closed ingress with service identity and audit trail |
| 5 | W4-05 Public REST schema and error parity | W4-04 | REST mirror has schema artifacts and canonical errors |
| 6 | W4-06 Knowledge Base record and decision-log integration | W4-01 through W4-05 | Runtime decisions are queryable and provenance-linked |
| 7 | W4-07 Wave 4 observability, compatibility, and release evidence | All W4 issues | Closure docs, readiness checklist, exit evidence bundle, and gap analysis are complete |

---

## 5. Contract decisions required before implementation

1. **QFS L1 ownership:** confirm whether live qubit / reservation semantics live in QFS, Resource Manager, or a split authority with a stable internal boundary.
2. **Checkpoint envelope schema:** confirm the exact fields required for restore compatibility, lineage, and integrity checks.
3. **Retention policy boundaries:** decide which artifact kinds are immutable, pinned, garbage-collected, or operator-deletable.
4. **Security enforcement mode:** confirm the minimum Product 1.0 authn/authz and service-identity posture for public and internal calls.
5. **REST schema policy:** decide whether the wave adds OpenAPI artifacts, JSON Schema artifacts, or both for the two current public mirror endpoints.
6. **Knowledge Base ingestion contract:** confirm the minimum decision-log payload required for replay and audit.

---

## 6. Definition of done

Wave 4 is 100% complete when:

- QFS L3 artifacts are persisted through a stable layout with integrity and lineage metadata.
- QFS L2 checkpoints have a documented envelope and restore compatibility tests.
- QFS L1 ownership is explicit and live-resource semantics are contract-tested.
- Public ingress follows the security baseline with method-level authorization and immutable audit evidence.
- REST mirror endpoints have schema artifacts, canonical errors, and parity tests.
- Knowledge Base record and decision-log flows are wired into the runtime path.
- Contract marker metrics, bounded labels, and trace continuity are present for the new boundaries.
- The Wave 4 compatibility report, release-readiness checklist, exit evidence bundle, and RFC/ADR gap analysis have no unresolved `TBD` values.
- The Product 1.0 manifest and contract inventory are synchronized to the final Wave 4 slice map.

---

## 7. Handoff to Wave 5

Wave 5 may start when Wave 4 proves that artifact persistence, checkpoint semantics, live-resource coordination, public mirror parity, and release evidence are deterministic and durable. At that point, scheduling/resource authority can be promoted without reopening the QFS, KB, REST, or security boundaries.
