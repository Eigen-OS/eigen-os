# Product 1.0 Wave 4 Issue Pack

**Wave:** Product 1.0 Wave 4 — QFS maturity, security alignment, REST parity, and Knowledge Base integration  
**Status:** Planning baseline  
**Parent execution plan:** `docs/development/wave-4/product-1.0-wave-4-execution-plan.md`

---

# W4-01 — QFS L3 artifact persistence, metadata, and integrity

## Goal

Promote QFS L3 from a local artifact helper into the canonical Product 1.0 artifact fabric with lineage, retention, integrity, and immutable persistence semantics.

## Normative references

- `docs/reference/formats/qfs-layout.md`
- `docs/architecture/components/qfs.md`
- `docs/architecture/contract-map.md`
- `docs/reference/error-model.md`

## Required implementation slices

1. Add storage backend abstraction for local filesystem and object-store profiles.
2. Persist canonical metadata:
   - digest,
   - producer,
   - schema version,
   - timestamps,
   - lineage,
   - retention policy.
3. Enforce immutable writes for `compiled/` and `results/` artifacts.
4. Implement integrity verification on read.
5. Add migration tooling or compatibility notes for existing local layouts.
6. Add artifact pinning and retention hooks.

## Required tests

- Duplicate immutable write rejection.
- Corrupted artifact digest rejection.
- Missing artifact → canonical `NOT_FOUND`.
- Backend outage → canonical `UNAVAILABLE`.
- Stable lineage metadata persistence.

## Exit evidence

- QFS lineage fixtures.
- Integrity verification report.
- Retention-policy compatibility notes.

## Required issue completion block MUST retain and complete this block before closure:

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

# W4-02 — QFS L2 checkpoint envelope and restore compatibility

## Goal

Define and enforce the Product 1.0 checkpoint envelope contract for replay-safe restore behavior.

## Normative references

- `docs/reference/formats/qfs-layout.md`
- `docs/architecture/components/qfs.md`
- `docs/reference/multi-device-execution-contract.md`

## Required implementation slices

1. Define checkpoint envelope schema.
2. Add atomic checkpoint write/read/delete semantics.
3. Add restore compatibility validation.
4. Persist restore lineage and checkpoint provenance.
5. Define checkpoint retention and cleanup policy.

## Required tests

- Corrupted checkpoint rejection.
- Version-incompatible restore rejection.
- Missing checkpoint mapping.
- Atomic restore replay.
- Checkpoint retention enforcement.

## Exit evidence

- Checkpoint schema fixtures.
- Restore replay evidence.
- Compatibility matrix.

## Required issue completion block MUST retain and complete this block before closure:

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

# W4-03 — QFS L1 live qubit / reservation ownership

## Goal

Resolve the ownership boundary for live-resource semantics and implement reservation tokens, leases, and stale cleanup behavior.

## Normative references

- `docs/architecture/components/qfs.md`
- `docs/architecture/contract-map.md`
- `docs/reference/multi-device-execution-contract.md`

## Required implementation slices

1. Decide final ownership:
   - QFS-owned,
   - Resource Manager-owned,
   - or split authority with stable boundary.
2. Implement reservation tokens and lease TTLs.
3. Add stale reservation cleanup and failover semantics.
4. Wire reservations into Kernel/QRTX scheduling hooks.
5. Emit reservation observability metrics.

## Required tests

- Lease expiry.
- Double reservation rejection.
- Failover recovery.
- Reservation replay determinism.

## Exit evidence

- Ownership ADR.
- Reservation lifecycle fixtures.
- Failover replay report.

## Required issue completion block MUST retain and complete this block before closure:

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

# W4-04 — Security and isolation hardening

## Goal

Turn Product 1.0 security from MVP middleware into a fail-closed contract boundary.

## Normative references

- `docs/reference/security/authz.md`
- `docs/architecture/components/security-isolation.md`
- `docs/reference/error-model.md`
- `docs/reference/error-mapping.md`

## Required implementation slices

1. Add JWT/OAuth2 validation.
2. Add service-to-service identity.
3. Implement versioned RBAC/ABAC policy snapshots.
4. Propagate normalized security context internally.
5. Add immutable audit sink and replay markers.
6. Enforce fail-closed policy behavior.
7. Add sandbox enforcement hooks.

## Required tests

- Expired token rejection.
- Invalid scope rejection.
- Policy backend outage fail-closed behavior.
- Audit sink persistence.
- Trace continuity with sanitized security metadata.

## Exit evidence

- Security conformance report.
- Policy snapshot fixtures.
- Audit replay evidence.

## Required issue completion block MUST retain and complete this block before closure:

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

# W4-05 — Public REST schema and error parity

## Goal

Close the Product 1.0 REST mirror gap with explicit schema artifacts and canonical error parity.

## Normative references

- `docs/reference/api/rest-public.md`
- `docs/reference/api/benchmark-run.md`
- `docs/reference/api/explain-backend-selection.md`

## Required implementation slices

1. Add OpenAPI or JSON Schema artifacts under `contracts/product-1.0/`.
2. Ensure REST responses map to canonical errors.
3. Add deterministic request hashing and idempotency parity.
4. Enforce authn/authz parity with gRPC.
5. Add REST observability contract markers.

## Required tests

- REST/gRPC parity fixtures.
- Canonical error mapping.
- Invalid payload validation.
- Trace propagation.
- Authn/authz parity.

## Exit evidence

- Schema bundle (`contracts/product-1.0/public-rest.openapi.json`).
- REST compatibility report.
- Public parity matrix.

## Required issue completion block MUST retain and complete this block before closure:

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

# W4-06 — Knowledge Base records and decision-log integration

## Goal

Wire runtime decision lineage into the Product 1.0 Knowledge Base contract.

## Normative references

- `docs/architecture/components/knowledge-base.md`
- `docs/reference/api/grpc-public.md`
- `docs/reference/error-model.md`

## Required implementation slices

1. Finalize KB record and decision-log ingestion paths.
2. Persist provenance and replay metadata.
3. Add deterministic query semantics for replay-safe retrieval.
4. Add anonymization and retention enforcement.
5. Wire runtime and benchmark flows into KB ingestion.

## Required tests

- Record upsert/query replay.
- Provenance persistence.
- Anonymization enforcement.
- KB fallback behavior.
- Decision-log lineage validation.

## Exit evidence

- `docs/development/wave-4/product-1.0-wave-4-w4-06-exit-evidence-bundle.md`
- `docs/development/wave-4/product-1.0-wave-4-w4-06-privacy-policy-compatibility-report.md`
- KB replay bundle.
- Provenance lineage fixtures.

## Required issue completion block MUST retain and complete this block before closure:

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

# W4-07 — Wave 4 observability, compatibility, and release evidence

## Goal

Produce the closure and release evidence proving that Wave 4 contracts are enforced end-to-end.

## Required deliverables

- `docs/development/wave-4/product-1.0-wave-4-compatibility-report.md`
- `docs/development/wave-4/product-1.0-wave-4-release-readiness-checklist.md`
- `docs/development/wave-4/product-1.0-wave-4-exit-evidence-bundle.md`
- `docs/development/wave-4/product-1.0-wave-4-rfc-adr-gap-analysis.md`

## Required evidence

- Contract marker metrics.
- Trace continuity proof.
- Conformance test inventory.
- Migration notes for all MAJOR deltas.
- Manifest alignment proof.

## Required issue completion block MUST retain and complete this block before closure:

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
