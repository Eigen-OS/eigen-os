# Product 1.0 Wave 5 Issue Pack

**Wave:** Product 1.0 Wave 5 — Resource Manager and multi-device execution
**Status:** Planning baseline
**Parent execution plan:** `docs/development/wave-5/product-1.0-wave-5-execution-plan.md`
**Source of truth:** `docs/architecture/**`, `docs/reference/**`

---

## W5-01 — Resource Manager authority and device inventory boundary

### Goal

Define the authoritative Resource Manager boundary for device inventory, capacity, and reservations, and decide whether the runtime owns this capability as a standalone service, an embedded kernel module, or a hybrid internal boundary.

### Normative references

- `docs/architecture/contract-map.md`
- `docs/architecture/components/resource-manager.md`
- `docs/architecture/components/driver-manager.md`
- `docs/architecture/components/qrtx.md`
- `docs/reference/multi-device-execution-contract.md`
- `docs/reference/orchestration-observability-contract.md`

### Required implementation slices

1. Decide the final deployment shape for Resource Manager.
2. Define the canonical ownership boundary between Resource Manager, QRTX, and Driver Manager.
3. Implement a deterministic device/resource inventory snapshot sourced from Driver Manager topology metadata.
4. Define the reservation compatibility surface that remains valid while the target authority is being introduced.
5. Update the Product 1.0 inventory row and manifest entries for the Resource Manager boundary.
6. Add documentation for current MVP reservation behavior versus the Product 1.0 target boundary.

### Required tests

- Inventory snapshot determinism for equivalent inputs.
- Capability filtering and topology visibility correctness.
- Placeholder reservation compatibility behavior.
- Missing inventory / empty inventory handling.
- Boundary ownership regression tests for the chosen deployment shape.

### Exit evidence

- Architecture decision record or RFC acceptance.
- Updated inventory row and manifest sync.
- Compatibility notes for current placeholder reservation behavior.
- Test evidence for deterministic resource inventory snapshots.

### Required issue completion block MUST retain and complete this block before closure:

#### Summary

-

#### Validation

- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

#### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Public API facade | Scheduler | Resource Manager | Driver Manager | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

#### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W5-02 — Scheduling policy engine and deterministic scoring

### Goal

Implement a versioned scheduling policy engine that produces deterministic eligibility, scoring, fairness, quota, and deadline-aware decisions for identical inputs.

### Normative references

- `docs/architecture/contract-map.md`
- `docs/architecture/components/resource-manager.md`
- `docs/architecture/components/qrtx.md`
- `docs/reference/multi-device-execution-contract.md`
- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/intelligent-runtime-observability-contract.md`

### Required implementation slices

1. Define the scheduling policy input model, including eligibility, scoring, fairness, priority, quota, and deadline fields.
2. Introduce explicit policy versioning and policy selection semantics.
3. Ensure equivalent scheduling inputs always produce equivalent outputs.
4. Define starvation-prevention and fairness expectations for multi-tenant or multi-project workloads.
5. Add explainability hooks so the selected policy outcome is inspectable.
6. Update contract inventory and compatibility documentation for the scheduling surface.

### Required tests

- Stable ranking under identical inputs.
- Policy version mismatch handling.
- Fairness and starvation-prevention behavior.
- Deadline-sensitive decisions.
- Replay of scheduling decisions under fixed policy inputs.

### Exit evidence

- Determinism matrix for schedule decisions.
- Scheduling policy fixture set.
- Compatibility report entry for policy versioning.
- Observability evidence for scoring and dispatch rationale.

### Required issue completion block MUST retain and complete this block before closure:

#### Summary

-

#### Validation

- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

#### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Public API facade | Scheduler | Resource Manager | Observability | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

#### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W5-03 — Reservation lifecycle and recovery semantics

### Goal

Implement and document reservation lifecycle semantics, including create, renew, bind, release, expire, and recover behavior with replay-safe lineage.

### Normative references

- `docs/architecture/components/resource-manager.md`
- `docs/architecture/contract-map.md`
- `docs/reference/multi-device-execution-contract.md`
- `docs/reference/qfs-layout.md`
- `docs/reference/orchestration-observability-contract.md`

### Required implementation slices

1. Define reservation lifecycle transitions and terminal states.
2. Specify lease renewal and expiry behavior.
3. Bind reservations to jobs and tasks in a replay-safe way.
4. Define recovery behavior after restart, stale leases, or partial failure.
5. Clarify how reservation state is persisted, audited, and restored.
6. Add compatibility notes for placeholder reservation APIs until the full authority is landed.

### Required tests

- Lease expiry.
- Renew/release transition behavior.
- Double reservation rejection.
- Recovery after stale or expired leases.
- Replay determinism of reservation lifecycle state.

### Exit evidence

- Reservation lifecycle state diagram.
- Recovery and stale-lease test fixtures.
- Architecture decision record for ownership and recovery semantics.

### Required issue completion block MUST retain and complete this block before closure:

#### Summary

-

#### Validation

- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

#### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Public API facade | Resource Manager | QFS | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

#### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W5-04 — Queue delivery and dead-letter semantics

### Goal

Define queue leases, acknowledgements, redelivery, replay, and dead-letter handling for runtime coordination.

### Normative references

- `docs/architecture/contract-map.md`
- `docs/architecture/components/resource-manager.md`
- `docs/architecture/components/qrtx.md`
- `docs/reference/multi-device-execution-contract.md`
- `docs/reference/orchestration-observability-contract.md`

### Required implementation slices

1. Define queue message ownership and lease semantics.
2. Define acknowledgement and redelivery behavior.
3. Define dead-letter classification and terminal handling.
4. Specify replay-safe queue ordering guarantees.
5. Integrate queue state transitions with scheduling and reservation lifecycle.
6. Add documentation for any compatibility-only queue paths that remain during migration.

### Required tests

- Ack/retry correctness.
- Lease expiry and redelivery determinism.
- Dead-letter terminalization.
- Queue ordering under replay.
- Failure recovery after transient worker outage.

### Exit evidence

- Queue semantics doc or ADR.
- Dead-letter scenario fixtures.
- Replay evidence for queue delivery order.

### Required issue completion block MUST retain and complete this block before closure:

#### Summary

-

#### Validation

- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

#### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Resource Manager | QRTX | Driver Manager | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

#### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W5-05 — Multi-device split / merge contracts

### Goal

Implement the contract surface for deterministic split plans, partial shard execution, merge validation, and final result aggregation across multiple devices or workers.

### Normative references

- `docs/reference/multi-device-execution-contract.md`
- `docs/architecture/contract-map.md`
- `docs/architecture/components/resource-manager.md`
- `docs/architecture/components/qrtx.md`
- `docs/architecture/components/qfs.md`

### Required implementation slices

1. Define split-plan manifest requirements.
2. Define shard identity and parent-child lineage rules.
3. Define partial result collection and failure propagation semantics.
4. Define merge validation and final artifact creation.
5. Define what metadata is required for replay-safe multi-device execution.
6. Add compatibility guidance for current single-device or placeholder execution paths.

### Required tests

- Split-plan determinism.
- Shard identity stability.
- Partial failure propagation.
- Merge validation and final result aggregation.
- Replay determinism for identical distributed inputs.

### Exit evidence

- Split/merge parity matrix.
- Replay fixtures for distributed execution.
- Merge policy documentation.

### Required issue completion block MUST retain and complete this block before closure:

#### Summary

-

#### Validation

- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

#### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Resource Manager | QRTX | QFS | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

#### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W5-06 — Dispatch rationale and explainability

### Goal

Replace placeholder dispatch rationale with real scheduling decisions and explainability artifacts that can be inspected in tests and release evidence.

### Normative references

- `docs/reference/multi-device-execution-contract.md`
- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/intelligent-runtime-observability-contract.md`
- `docs/architecture/components/resource-manager.md`
- `docs/architecture/components/observability.md`

### Required implementation slices

1. Implement `GetDispatchRationale` from actual scheduling state.
2. Ensure rationale includes the policy version and decision inputs.
3. Ensure rationale is deterministic for identical inputs.
4. Define safe bounded metadata for rationale outputs.
5. Add compatibility notes for any current placeholder rationale fields.

### Required tests

- Rationale stability.
- Trace linkage to job and schedule state.
- Output parity with scheduling decisions.
- Bounded metadata and no sensitive leakage.

### Exit evidence

- Explainability contract mapping.
- Dispatch rationale fixtures.
- Observability evidence for explainability outputs.

### Required issue completion block MUST retain and complete this block before closure:

#### Summary

-

#### Validation

- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

#### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Observability | Scheduler | Resource Manager | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

#### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W5-07 — Deterministic replay and audit lineage

### Goal

Ensure that scheduling, reservation, and multi-device execution decisions are eplay-safe and auditable.

### Normative references

- `docs/architecture/components/observability.md`
- `docs/architecture/components/qfs.md`
- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/multi-device-execution-contract.md`
- `docs/reference/error-model.md`

### Required implementation slices

1. Define replay identity for scheduling and reservation decisions.
2. Persist audit lineage for schedule, split, merge, and terminalization decisions.
3. Ensure replay output is deterministic for recorded decision inputs.
4. Define how retries and replays are distinguished in evidence.
5. Document the minimal trace and event fields required for auditability.

### Required tests

- Replay digest stability.
- Audit lineage completeness.
- Restart recovery replay.
- Deterministic terminalization after replay.

### Exit evidence

- Audit lineage fixtures.
- Replay test matrix.
- Evidence bundle showing decision continuity.

### Required issue completion block MUST retain and complete this block before closure:

#### Summary

-

#### Validation

- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

#### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Observability | QFS | Resource Manager | QRTX | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

#### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W5-08 — Cluster/runtime observability conformance

### Goal

Add bounded metrics, structured logs, trace continuity, and dashboard-ready observability coverage for all Wave 5 surfaces.

### Normative references

- `docs/architecture/components/observability.md`
- `docs/architecture/contract-map.md`
- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/intelligent-runtime-observability-contract.md`
- `docs/reference/multi-device-execution-contract.md`

### Required implementation slices

1. Define observability markers for Resource Manager and multi-device execution urfaces.
2. Ensure metric labels remain bounded and deterministic.
3. Ensure trace continuity across scheduling, reservation, split/merge, and replay paths.
4. Ensure structured logs contain only safe, sanitized metadata.
5. Add compatibility notes for any temporarily missing exporters or dashboards.

### Required tests

- Bounded label checks.
- Trace continuity checks.
- Contract marker presence.
- Sanitized log output checks.
- Dashboard/exporter conformance smoke tests.

### Exit evidence

- Observability conformance report.
- Contract marker fixtures.
- Dashboard and alert notes.

### Required issue completion block MUST retain and complete this block before closure:

#### Summary

-

#### Validation

- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

#### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Metrics | Logs | Traces | Dashboards | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

#### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```
