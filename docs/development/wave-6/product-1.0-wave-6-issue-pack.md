# Product 1.0 Wave 6 Issue Pack

**Wave:** Product 1.0 Wave 6 — Driver Manager and QDriver final contract  
**Status:** Planning baseline  
**Parent execution plan:** `docs/development/wave-6/product-1.0-wave-6-execution-plan.md`  
**Source of truth:** `docs/architecture/**`, `docs/reference/**`

---

## W6-01 — Final QDriver v1 contract and kernel-facing transport alignment

### Goal

Align the kernel-facing driver manager contract with the final QDriver v1 semantics defined in the accepted RFC/ADR baseline.

### Normative references

- `docs/architecture/components/driver-manager.md`
- `docs/reference/api/grpc-internal.md`
- `docs/reference/api/qdriver.md`
- `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`
- `docs/adr/0030-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`

### Required implementation slices

1. Reconcile the accepted QDriver method set with the current driver-manager service surface.
2. Preserve deterministic capability negotiation and unsupported-operation handling.
3. Keep response shapes and gRPC status mapping stable.
4. Add a canonical reference for the final contract if the docs/reference surface needs one.
5. Ensure generated bindings and service stubs match the canonical contract.

### Required tests

- QDriver conformance happy path.
- Unsupported capability / unsupported backend rejection.
- Version / compatibility mismatch.
- Deterministic transport metadata and error mapping.

### Exit evidence

- QDriver conformance suite report.
- Proto / API diff summary.
- Compatibility note describing the final transport shape.

### Required issue completion block MUST retain and complete this block before closure:

### Summary

-

### Validation

- [] Tests added/updated
- [] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Public API facade | Compiler contract | AQO | QFS | Metrics | Trace context | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W6-02 — Driver Manager capability registry and device profile negotiation

### Goal

Make device capabilities, topology hints, and device profiles versioned and queryable as the canonical source of truth for provider selection and hardware-aware execution.

### Normative references

- `docs/architecture/components/driver-manager.md`
- `docs/architecture/components/qrtx.md`
- `docs/reference/api/grpc-internal.md`

### Required implementation slices

1. Normalize device profile metadata.
2. Version capability descriptors.
3. Separate snapshot data from live session state.
4. Add stable device lookup and profile negotiation semantics.
5. Preserve simulator/provider parity entries.

### Required tests

- Device profile fixture round-trip.
- Unknown profile / unknown device rejection.
- Deterministic capability snapshot ordering.
- Profile negotiation fallback behavior.

### Exit evidence

- Capability registry fixture.
- Device profile matrix.
- Snapshot and lookup tests.

### Required issue completion block MUST retain and complete this block before closure:

### Summary

-

### Validation

- [] Tests added/updated
- [] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Public API facade | Compiler contract | AQO | QFS | Metrics | Trace context | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W6-03 — Session pooling, lifecycle governance, and calibration semantics

### Goal

Define and test how driver sessions are created, reused, refreshed, calibrated, and shut down.

### Normative references

- `docs/architecture/components/driver-manager.md`
- `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`
- `docs/adr/0030-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`

### Required implementation slices

1. Add explicit session lifecycle states.
2. Define pooling / reuse / refresh semantics.
3. Define calibration lifecycle behavior.
4. Keep shutdown and restart behavior safe.
5. Ensure lifecycle transitions remain deterministic.

### Required tests

- Session reuse across compatible executions.
- Session invalidation after failure or rollback.
- Calibration artifact reference stability.
- Lifecycle restart safety.

### Exit evidence

- Session lifecycle fixture.
- Calibration lifecycle evidence.
- Restart behavior report.

### Required issue completion block MUST retain and complete this block before closure:

### Summary

-

### Validation

- [] Tests added/updated
- [] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Public API facade | Compiler contract | AQO | QFS | Metrics | Trace context | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W6-04 — Normalized results and error mapping

### Goal

Keep execution outputs and provider failures normalized into the canonical Eigen OS result and error model.

### Normative references

- `docs/reference/error-model.md`
- `docs/reference/error-mapping.md`
- `docs/architecture/components/driver-manager.md`
- `docs/reference/api/grpc-internal.md`

### Required implementation slices

1. Normalize counts, metadata, and execution timing.
2. Map provider and backend failures to stable gRPC statuses.
3. Preserve retryability and precondition metadata.
4. Keep unsupported-operation errors deterministic.
5. Ensure response shapes remain backend-independent.

### Required tests

- Counts normalization fixture.
- Error-to-status mapping fixture.
- Retryable vs non-retryable failure mapping.
- Unsupported format rejection.

### Exit evidence

- Normalization matrix.
- Error mapping report.
- Conformance assertions for response shape.

### Required issue completion block MUST retain and complete this block before closure:

### Summary

-

### Validation

- [] Tests added/updated
- [] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Public API facade | Compiler contract | AQO | QFS | Metrics | Trace context | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W6-05 — Provider sandboxing, secrets lifecycle, and supply-chain isolation

### Goal

Keep provider credentials, provider SDK behavior, and backend execution isolated from the public surface and from unsafe runtime paths.

### Normative references

- `docs/architecture/components/driver-manager.md`
- `docs/reference/security/authz.md` if needed by implementation
- `docs/architecture/components/security-isolation.md` if referenced by implementation
- `docs/reference/orchestration-observability-contract.md`

### Required implementation slices

1. Resolve secrets only through the security/secrets path.
2. Enforce sandbox or process isolation rules for provider code.
3. Keep provider configuration explicit and versioned.
4. Add fail-closed behavior for missing or revoked secrets.
5. Document the supply-chain and provider-configuration boundary.

### Required tests

- Secret resolution allow/deny.
- Revoked secret rejection.
- Sandbox policy rejection.
- Provider config validation.
- Audit trail emission for secret lifecycle events.

### Exit evidence

- Secret lifecycle test report.
- Sandbox policy enforcement evidence.
- Audit / deny-event samples.

### Required issue completion block MUST retain and complete this block before closure:

### Summary

-

### Validation

- [] Tests added/updated
- [] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Public API facade | Compiler contract | AQO | QFS | Metrics | Trace context | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W6-06 — Official simulator reference backend and provider matrix parity

### Goal

Keep the simulator as the canonical reference backend and define the official provider matrix / tolerance policy used for conformance.

### Normative references

- `rfcs/0045-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`
- `docs/adr/0031-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`
- `docs/architecture/components/driver-manager.md`

### Required implementation slices

1. Keep the simulator as the default conformance backend.
2. Make provider matrix membership explicit.
3. Version tolerance profiles and drift policy.
4. Add parity fixtures for official providers.
5. Make rollback and demotion behavior auditable.

### Required tests

- Simulator parity fixture.
- Official provider matrix fixture.
- Tolerance profile regression gate.
- Rollback governance fixture.

### Exit evidence

- Provider matrix report.
- Tolerance profile artifact.
- Rollback / demotion rehearsal evidence.

### Required issue completion block MUST retain and complete this block before closure:

### Summary

-

### Validation

- [] Tests added/updated
- [] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Public API facade | Compiler contract | AQO | QFS | Metrics | Trace context | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```

---

## W6-07 — Observability, release evidence, and rollback governance

### Goal

Make the wave auditable with bounded logs, bounded metrics, trace continuity, and release evidence that proves provider behavior is stable.

### Normative references

- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/intelligent-runtime-observability-contract.md`
- `docs/architecture/components/observability.md`
- `docs/architecture/components/driver-manager.md`

### Required implementation slices

1. Add bounded driver-manager metrics.
2. Preserve trace continuity across kernel → driver-manager → provider adapter.
3. Emit structured logs with stable fields.
4. Link rollback / quarantine events to the release evidence bundle.
5. Keep release artifacts reproducible.

### Required tests

- Observability smoke test.
- Trace continuity fixture.
- Bounded-label regression gate.
- Rollback evidence fixture.

### Exit evidence

- Metrics snapshot.
- Trace continuity report.
- Release evidence bundle.

### Required issue completion block MUST retain and complete this block before closure:

### Summary

-

### Validation

- [] Tests added/updated
- [] Documentation updated (if contracts/behavior changed)

### Versioning & Compatibility (required)

- **Version Impact:** <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces:** <!-- Internal API | Public API facade | Compiler contract | AQO | QFS | Metrics | Trace context | Compatibility matrix | Migration docs -->
- **Compatibility:** <!-- Backward-compatible | Breaking (requires MAJOR) -->
- **Breaking Marker:** <!-- true | false -->
- **Migration Notes:** <!-- Required when Breaking Marker=true (or Version Impact=MAJOR); otherwise "None" is allowed -->

### Release Notes Draft

```markdown
### Added
-
### Changed
-
### Fixed
-
```
