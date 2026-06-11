# Product 1.0 Wave 5 Issue Pack

**Wave:** Product 1.0 Wave 5 — Resource Manager and multi-device execution  
**Status:** Closed  
**Parent execution plan:** `docs/development/wave-5/product-1.0-wave-5-execution-plan.md`  
**Source of truth:** `docs/architecture/**`, `docs/reference/**`

---

## W5-01 — Resource Manager authority and device inventory boundary

### Goal

Define the authoritative Resource Manager boundary for device inventory, capacity, and reservations, and decide whether the runtime owns this capability as a standalone service, an embedded kernel module, or a hybrid internal boundary.

### Closure summary

The wave closed on the kernel-owned internal authority model. Device inventory now comes from Driver Manager topology/capability metadata, reservations are replay-safe, and the public reservation surface remains a compatibility bridge.

### Validation

- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** NONE
- **Affected Interfaces:** Internal API; Resource Manager; Driver Manager; compatibility matrix; migration docs
- **Compatibility:** Backward-compatible
- **Breaking Marker:** false
- **Migration Notes:** None

### Release Notes Draft

```markdown
### Added
- Kernel-owned Resource Manager boundary and deterministic inventory semantics.
### Changed
- Reservation compatibility is documented as a bridge rather than the canonical authority.
### Fixed
- Boundary ownership ambiguity between QRTX, Resource Manager, and Driver Manager.
```

---

## W5-02 — Scheduling policy engine and deterministic scoring

### Goal

Implement a versioned scheduling policy engine that produces deterministic eligibility, scoring, fairness, quota, and deadline-aware decisions for identical inputs.

### Closure summary

The scheduling policy engine is now explicit, versioned, and replay-safe. Identical inputs produce identical outputs, and the policy bundle metadata is surfaced for explainability and drift control.

### Validation

- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** MINOR
- **Affected Interfaces:** Scheduler; Resource Manager; observability; compatibility matrix; migration docs
- **Compatibility:** Backward-compatible
- **Breaking Marker:** false
- **Migration Notes:** New policy metadata is additive and deterministic defaults remain stable.

### Release Notes Draft

```markdown
### Added
- Deterministic scheduler scoring and policy version metadata.
### Changed
- Dispatch rationale now reflects real scheduling state.
### Fixed
- Non-deterministic policy selection and stale placeholder rationale outputs.
```

---

## W5-03 — Reservation lifecycle and recovery semantics

### Goal

Implement and document reservation lifecycle semantics, including create, renew, bind, release, expire, and recover behavior with replay-safe lineage.

### Closure summary

Reservation lifecycle semantics are now deterministic. Double booking is rejected, expiries are swept deterministically, and persisted reservation lineage survives restart and replay.

### Validation

- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** MINOR
- **Affected Interfaces:** Internal API; Resource Manager; QRTX; compatibility matrix; migration docs
- **Compatibility:** Backward-compatible
- **Breaking Marker:** false
- **Migration Notes:** None; behavior is tightened without changing the public surface.

### Release Notes Draft

```markdown
### Added
- Replay-safe reservation recovery and deterministic expiry sweeps.
### Changed
- Reservation lifecycle is now explicitly documented and tested.
### Fixed
- Double-booking and restart-recovery ambiguity.
```

---

## W5-04 — Queue delivery and dead-letter semantics

### Goal

Define queue leases, acknowledgements, redelivery, replay, and dead-letter handling for runtime coordination.

### Closure summary

Queue semantics now distinguish lease expiry, retry, and terminal dead-letter states. Equivalent inputs replay with stable ordering and stable terminalization.

### Validation

- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** MINOR
- **Affected Interfaces:** Internal API; Resource Manager; QRTX; compatibility matrix; migration docs
- **Compatibility:** Backward-compatible
- **Breaking Marker:** false
- **Migration Notes:** None; queue behavior is an additive clarification over the compatibility bridge.

### Release Notes Draft

```markdown
### Added
- Lease, ack, redelivery, and dead-letter semantics.
### Changed
- Queue recovery behavior is now deterministic and auditable.
### Fixed
- Implicit queue recovery semantics.
```

---

## W5-05 — Multi-device split / merge contracts

### Goal

Implement the contract surface for deterministic split plans, partial shard execution, merge validation, and final result aggregation across multiple devices or workers.

### Closure summary

Split/merge contracts are now versioned, deterministic, and lineage-preserving. Shard identity, merge validation, and final aggregation all replay cleanly under fixed inputs.

### Validation

- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** MINOR
- **Affected Interfaces:** Internal API; Resource Manager; QRTX; QFS; compatibility matrix; migration docs
- **Compatibility:** Backward-compatible
- **Breaking Marker:** false
- **Migration Notes:** None; single-device compatibility remains represented as a one-shard split plan.

### Release Notes Draft

```markdown
### Added
- Deterministic split-plan manifests and merge validation semantics.
### Changed
- Multi-device execution now carries explicit lineage metadata.
### Fixed
- Placeholder split/merge behavior.
```

---

## W5-06 — Dispatch rationale and explainability

### Goal

Replace placeholder dispatch rationale with real scheduling decisions and explainability artifacts that can be inspected in tests and release evidence.

### Closure summary

Dispatch rationale is now derived from actual scheduling state and policy metadata. The output is deterministic, bounded, and suitable for audit and observability sinks.

### Validation

- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** PATCH
- **Affected Interfaces:** Internal API; observability; scheduler; Resource Manager; compatibility matrix; migration docs
- **Compatibility:** Backward-compatible
- **Breaking Marker:** false
- **Migration Notes:** None.

### Release Notes Draft

```markdown
### Added
- Real dispatch rationale derived from the scheduling state.
### Changed
- Explainability output is now stable and bounded.
### Fixed
- Placeholder rationale fields and unstable stringification.
```

---

## W5-07 — Deterministic replay and audit lineage

### Goal

Ensure that scheduling, reservation, and multi-device execution decisions are replay-safe and auditable.

### Closure summary

Replay identity and audit lineage are now persisted across schedule, split, merge, and terminalization paths. The recorded artifacts are stable across restarts and identical inputs.

### Validation

- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** PATCH
- **Affected Interfaces:** Observability; QFS; Resource Manager; QRTX; compatibility matrix; migration docs
- **Compatibility:** Backward-compatible
- **Breaking Marker:** false
- **Migration Notes:** None.

### Release Notes Draft

```markdown
### Added
- Deterministic replay identity and audit lineage evidence.
### Changed
- Replay evidence now carries stable terminalization metadata.
### Fixed
- Non-deterministic snapshot digests.
```

---

## W5-08 — Cluster/runtime observability conformance

### Goal

Add bounded metrics, structured logs, trace continuity, and dashboard-ready observability coverage for all Wave 5 surfaces.

### Closure summary

Wave 5 observability conformance is complete. Bounded metrics, trace continuity, sanitized logs, and contract-marker coverage are documented and validated for the Resource Manager and multi-device surfaces.

### Validation

- [x] Tests added/updated
- [x] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** PATCH
- **Affected Interfaces:** Metrics; logs; traces; dashboards; compatibility matrix; migration docs
- **Compatibility:** Backward-compatible
- **Breaking Marker:** false
- **Migration Notes:** None.

### Release Notes Draft

```markdown
### Added
- Wave 5 observability conformance coverage and contract markers.
### Changed
- Metrics and logs are now bounded and replay-friendly.
### Fixed
- Missing closure evidence for observability surfaces.
```
