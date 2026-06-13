# Product 1.0 Wave 10 Issue Pack

This document is a ready-to-use set of GitHub issues for **Product 1.0 Wave 10 — Observability, trace continuity, and bounded telemetry**.

**Context sources:**
- `docs/development/product-1.0-contract-alignment-plan.md`
- `docs/development/product-1.0-contract-inventory.md`
- `docs/development/product-1.0-version-policy.md`
- `docs/development/wave-10/product-1.0-wave-10-execution-plan.md`
- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/intelligent-runtime-observability-contract.md`
- `docs/reference/cluster-runtime-observability-contract.md`
- `docs/reference/benchmark-observability-contract.md`
- `docs/architecture/components/observability.md`
- `docs/howto/run-observability.md`

---

## Every implementation issue MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Metrics | Traces | Logs | Dashboards | Alerts | Compatibility matrix | Migration docs -->
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

- **Milestone:** `Product 1.0 Wave 10 Observability, Trace Continuity, and Bounded Telemetry`
- **Suggested labels:** `product-1.0`, `product-1.0-wave-10`, `observability`, `telemetry`, `trace`, `metrics`, `dashboards`, `alerts`, `runbooks`, `conformance`, `release-evidence`, `docs`

---

## Priority and ownership proposal

| Issue | Priority | Proposed owner group |
|---|---|---|
| W10-01 Observability contract markers and bounded metric labels | P0 | Observability; System API; Kernel/QRTX |
| W10-02 Trace continuity, correlation fields, and structured logs | P0 | Observability; System API; Kernel/QRTX; Runtime owners |
| W10-03 Observability parity for orchestration, runtime, cluster, and benchmark | P0 | Observability; Kernel/QRTX; Resource Manager; Benchmark |
| W10-04 Conformance gating, release-readiness, and evidence bundle | P1 | Architecture/Governance; Docs; Observability |

---

## Issues

### W10-01 — Observability contract markers and bounded metric labels

**Type:** Metrics / Contract Surface  
**Labels:** `product-1.0-wave-10`, `observability`, `metrics`, `bounded-labels`, `p0`

**Problem:** Every observability surface must expose its contract marker metric and keep labels bounded and secret-free.

**Scope**
- Align exporter surfaces to `docs/architecture/components/observability.md` and the specialized observability contracts.
- Ensure the stable marker metric exists for each in-scope exporter.
- Keep metric labels bounded, enumerable, and deterministic.
- Add or update conformance tests for marker presence and label cardinality.

**Acceptance Criteria**
- Marker metrics are visible on every in-scope observability surface.
- No metric family introduces unbounded labels or sensitive payload leakage.
- Conformance fixtures fail closed when a marker metric is missing or malformed.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Metrics | Traces | Logs | Dashboards | Alerts | Compatibility matrix | Migration docs -->
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

### W10-02 — Trace continuity, correlation fields, and structured logs

**Type:** Tracing / Logging Contract  
**Labels:** `product-1.0-wave-10`, `observability`, `trace`, `logs`, `p0`

**Problem:** Operators need deterministic correlation across ingress, orchestration, runtime, cluster, and benchmark flows.

**Scope**
- Preserve `traceparent` / `trace_id` propagation across supported flows.
- Ensure logs carry the stable correlation fields required by the observability contracts.
- Keep replay and durable artifacts trace-correlatable without unbounded labels.
- Add fixtures proving correlation survives submit-to-results and runtime decisioning paths.

**Acceptance Criteria**
- Trace continuity is preserved across the supported Wave 10 paths.
- Structured logs include required correlation fields and remain secret-free.
- Replay evidence can reconstruct the lifecycle of a job or runtime decision.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Metrics | Traces | Logs | Dashboards | Alerts | Compatibility matrix | Migration docs -->
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

### W10-03 — Observability parity for orchestration, runtime, cluster, and benchmark

**Type:** Runtime / Distributed Observability Contract  
**Labels:** `product-1.0-wave-10`, `observability`, `runtime`, `cluster`, `benchmark`, `dashboards`, `alerts`, `p0`

**Problem:** The observability contracts must agree across orchestration, intelligent runtime, cluster runtime, and benchmark surfaces.

**Scope**
- Align orchestration metrics with `docs/reference/orchestration-observability-contract.md`.
- Align runtime decision telemetry with `docs/reference/intelligent-runtime-observability-contract.md`.
- Align cluster runtime telemetry with `docs/reference/cluster-runtime-observability-contract.md`.
- Align benchmark telemetry with `docs/reference/benchmark-observability-contract.md`.
- Update dashboards and alerts to the canonical metric families and bounded labels.

**Acceptance Criteria**
- Exporters satisfy their contract markers and bounded-label rules.
- Dashboards and alerts reflect the canonical telemetry semantics.
- Degraded, fallback, and replay paths remain observable and traceable.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Metrics | Traces | Logs | Dashboards | Alerts | Compatibility matrix | Migration docs -->
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

### W10-04 — Conformance gating, release-readiness, and evidence bundle

**Type:** Conformance / Release Governance  
**Labels:** `product-1.0-wave-10`, `observability`, `conformance`, `release-evidence`, `p1`

**Problem:** Wave 10 needs release-quality proof that observability contracts, trace continuity, dashboards, alerts, and runbooks stay aligned across regressions.

**Scope**
- Add quality regression gates using fixed fixtures for observability surfaces.
- Define which observability regressions block release and which are informational only.
- Create or update the Wave 10 compatibility report.
- Create or update the Wave 10 release-readiness checklist.
- Create or update the Wave 10 exit evidence bundle.

**Acceptance Criteria**
- Regression fixtures are enforced in CI or equivalent gating.
- Compatibility report has no unresolved `TBD` values for completed issues.
- Evidence bundle records commands, artifacts, limitations, and commit SHA information.
- Release-readiness checklist is complete.

## Required issue completion block MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Metrics | Traces | Logs | Dashboards | Alerts | Compatibility matrix | Migration docs -->
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
