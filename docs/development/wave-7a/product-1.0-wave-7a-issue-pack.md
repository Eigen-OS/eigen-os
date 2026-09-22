# Product 1.0 Wave 7a Issue Pack

This document is a ready-to-use set of GitHub issues for **Product 1.0 Wave 7a — GNN Optimizer and intelligent runtime**.

**Context sources:**
- `docs/development/product-1.0-contract-alignment-plan.md`
- `docs/development/wave-7a/product-1.0-wave-7a-execution-plan.md`
- `docs/development/product-1.0-contract-inventory.md`
- `docs/development/product-1.0-version-policy.md`
- `docs/reference/api/grpc-internal.md`
- `docs/reference/intelligent-runtime-observability-contract.md`
- `docs/reference/compiler-observability-contract.md`
- `docs/architecture/components/gnn-optimizer.md`
- `docs/architecture/components/compiler.md`
- `docs/architecture/components/neuro-symbolic-core.md`
- `docs/architecture/components/observability.md`
- `docs/architecture/components/qrtx.md`
- `rfcs/0057-product-1.0-optimizer-production-path.md`
- `docs/adr/0049-product-1.0-optimizer-production-path.md`

---

## Every implementation issue MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Internal API | Kernel orchestration | Metrics | Trace context | Compatibility matrix | Migration docs -->
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

- **Milestone:** `Product 1.0 Wave 7a GNN Optimizer and Intelligent Runtime`
- **Suggested labels:** `product-1.0`, `product-1.0-wave-7a`, `gnn-optimizer`, `intelligent-runtime`, `internal-api`, `observability`, `compatibility`, `conformance`

---

## Priority and ownership proposal

| Issue | Priority | Proposed owner group |
|---|---|---|
| W7A-01 Optimizer service server/client wiring and Kernel/QRTX handoff | P0 | GNN Optimizer + Kernel/QRTX |
| W7A-02 Model registry and version promotion policy | P0 | GNN Optimizer + Architecture |
| W7A-03 Deterministic fallback and confidence thresholds | P0 | GNN Optimizer + Reliability |
| W7A-04 Optimization candidate traces, metrics, and dashboards | P0 | Observability + GNN Optimizer |
| W7A-05 Quality regression gates and release evidence bundle | P1 | Architecture/Governance + Tech Writing |
| W7A-06 Inventory and manifest synchronization for Wave 7a surfaces | P1 | Architecture + Docs |

---

## Issues

### W7A-01 — Optimizer service server/client wiring and Kernel/QRTX handoff

**Type:** Internal API Contract / Runtime Integration
**Labels:** `product-1.0-wave-7a`, `gnn-optimizer`, `internal-api`, `kernel`, `p0`

**Problem:** Wave 7a requires the optimizer to be callable through the real Kernel/QRTX execution path rather than fixture-only adapters.

**Scope**
- Wire Kernel/QRTX to the optimizer service server/client path.
- Preserve the frozen optimizer contract shape while replacing fixture-only dispatch.
- Map compiler/IR inputs into optimizer requests and return normalized optimizer responses.
- Keep trace and request identifiers stable across the handoff.
- Ensure the execution path remains deterministic when optimizer selection is enabled.

**Acceptance Criteria**
- Kernel/QRTX can invoke optimizer service in the production path.
- Handoff preserves deterministic identifiers and trace continuity.
- Existing contract tests still pass.
- No new public API surface is introduced.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Internal API | Kernel orchestration | Metrics | Trace context | Compatibility matrix | Migration docs -->
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

### W7A-02 — Model registry and version promotion policy

**Type:** Governance / Contract Policy
**Labels:** `product-1.0-wave-7a`, `gnn-optimizer`, `registry`, `policy`, `p0`

**Problem:** The optimizer cannot become a production path without a documented and deterministic model registry/version promotion policy.

**Scope**
- Define the registry backend for the first Wave 7a slice.
- Define how a model becomes promotable.
- Define version selection, rollback, and quarantine behavior.
- Define how registry decisions are recorded for audit and release evidence.
- Keep registry semantics aligned with the frozen optimizer contract and the version policy.

**Acceptance Criteria**
- Registry behavior is versioned and deterministic.
- Promotion and rollback rules are explicit and test-covered.
- Registry policy is documented as part of the Wave 7a evidence trail.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Internal API | Kernel orchestration | Metrics | Trace context | Compatibility matrix | Migration docs -->
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

### W7A-03 — Deterministic fallback and confidence thresholds

**Type:** Reliability / Runtime Behavior
**Labels:** `product-1.0-wave-7a`, `gnn-optimizer`, `fallback`, `confidence`, `p0`

**Problem:** Production use of the optimizer must not block deterministic execution when the optimizer is unavailable or confidence is below threshold.

**Scope**
- Define confidence thresholds and unavailability policy.
- Add deterministic fallback behavior when thresholds are not met.
- Ensure fallback choice is visible in traces, logs, and release evidence.
- Make fallback behavior explicit for compiler/driver execution paths.
- Keep fallback stable across repeated identical inputs.

**Acceptance Criteria**
- Fallback behavior is deterministic and documented.
- Unavailable and low-confidence paths are handled explicitly.
- Traceability includes a fallback reason and model version where applicable.
- Contract behavior remains compatible for existing consumers.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Internal API | Kernel orchestration | Metrics | Trace context | Compatibility matrix | Migration docs -->
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

### W7A-04 — Optimization candidate traces, metrics, and dashboards

**Type:** Observability / Contract Evidence
**Labels:** `product-1.0-wave-7a`, `observability`, `metrics`, `tracing`, `p0`

**Problem:** The optimizer path must produce operator-visible evidence, but labels and telemetry must remain bounded and compatible with the intelligent-runtime observability contract.

**Scope**
- Emit optimization candidate traces with the required fields:
  - objective,
  - score breakdown,
  - topology context,
  - model version,
  - confidence,
  - fallback reason.
- Add or update metrics in a way that remains bounded and compatible with the observability contract.
- Add dashboard fixtures and alert fixtures for the intelligent-runtime surface.
- Preserve trace continuity across Kernel/QRTX, optimizer, and downstream handoff points.
- Avoid unbounded metric labels or raw payload leakage.

**Acceptance Criteria**
- Candidate traces are emitted in the documented shape.
- Metrics are scrapeable, bounded, and stable.
- Dashboards and alerts exist for the Wave 7a runtime surface.
- Trace continuity survives fallback and promotion paths.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Internal API | Kernel orchestration | Metrics | Trace context | Compatibility matrix | Migration docs -->
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

### W7A-05 — Quality regression gates and release evidence bundle

**Type:** Conformance / Release Governance
**Labels:** `product-1.0-wave-7a`, `conformance`, `release-evidence`, `p1`

**Problem:** Wave 7a needs release-quality proof that optimizer behavior, fallback behavior, and observability behavior stay aligned across regressions.

**Scope**
- Add quality regression gates using fixed fixtures.
- Define which failures block release and which are informational only.
- Create or update the Wave 7a compatibility report.
- Create or update the Wave 7a release-readiness checklist.
- Create or update the Wave 7a exit evidence bundle.

**Acceptance Criteria**
- Regression fixtures are enforced in CI or equivalent gating.
- Compatibility report has no unresolved `TBD` values for completed issues.
- Evidence bundle records commands, artifacts, limitations, and commit SHA.
- Release-readiness checklist is complete.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Internal API | Kernel orchestration | Metrics | Trace context | Compatibility matrix | Migration docs -->
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

### W7A-06 — Inventory and manifest synchronization for Wave 7a surfaces

**Type:** Documentation / Governance
**Labels:** `product-1.0-wave-7a`, `inventory`, `manifest`, `docs`, `p1`

**Problem:** Wave 7a is only complete when the inventory and any machine-readable manifest rows reflect the production optimizer path and observability surfaces.

**Scope**
- Update `docs/development/product-1.0-contract-inventory.md` for any concrete Wave 7a contract mapping changes.
- Ensure the GNN Optimizer, compiler↔optimizer handoff, and optimization explainability rows remain synchronized with implementation reality.
- Ensure the manifest references, if present, are updated in the same PR as contract mapping changes.
- Update any docs that refer to fixture-only behavior once production path is adopted.
- Keep the inventory aligned with RFC-0057 and ADR-0049.

**Acceptance Criteria**
- Inventory rows are synchronized with the implemented Wave 7a surfaces.
- Any changed contract mapping has corresponding documentation updates.
- No stale fixture-only wording remains where production behavior is now authoritative.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Internal API | Kernel orchestration | Metrics | Trace context | Compatibility matrix | Migration docs -->
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

## Wave 7a closure reminder

Wave 7a is complete only when the optimizer production path is callable through Kernel/QRTX, deterministic fallback is documented and tested, observability is bounded and stable, quality regression gates are in place, and the inventory/manifest are synchronized with the implemented surfaces.
