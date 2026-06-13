# Product 1.0 Wave 9 Issue Pack

This document is a ready-to-use set of GitHub issues for **Product 1.0 Wave 9 — Security, identity, policy, and isolation**.

**Context sources:**
- `docs/development/product-1.0-contract-alignment-plan.md`
- `docs/development/product-1.0-contract-inventory.md`
- `docs/development/product-1.0-version-policy.md`
- `docs/development/wave-9/product-1.0-wave-9-execution-plan.md`
- `docs/reference/api/grpc-public.md`
- `docs/reference/api/grpc-internal.md`
- `docs/reference/error-model.md`
- `docs/reference/security/authz.md`
- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/intelligent-runtime-observability-contract.md`
- `docs/architecture/components/security-isolation.md`
- `docs/architecture/components/driver-manager.md`
- `docs/architecture/components/observability.md`
- `docs/architecture/components/knowledge-base.md`
- `rfcs/0009-security-isolation-mvp.md`
- `docs/adr/0002-mvp1-contract-baseline.md`

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

- **Milestone:** `Product 1.0 Wave 9 Security, Identity, Policy, and Isolation`
- **Suggested labels:** `product-1.0`, `product-1.0-wave-9`, `security`, `identity`, `policy`, `isolation`, `conformance`, `release-evidence`, `docs`

---

## Priority and ownership proposal

| Issue | Priority | Proposed owner group |
|---|---|---|
| W9-01 Authentication, authorization, and normalized security context | P0 | Security & Isolation; System API |
| W9-02 Service identity, policy snapshots, and deterministic policy decisions | P0 | Security & Isolation; Kernel/QRTX |
| W9-03 Sandbox isolation, secrets lifecycle, and provider boundary hardening | P0 | Security & Isolation; Driver Manager; Compiler |
| W9-04 Audit store, security telemetry, and replayable security evidence | P1 | Security & Isolation; Observability |
| W9-05 Security conformance, fail-closed gating, and release evidence bundle | P1 | Architecture/Governance; Docs; Security |

---

## Issues

### W9-01 — Authentication, authorization, and normalized security context

**Type:** Ingress Security / Boundary Contract  
**Labels:** `product-1.0-wave-9`, `security`, `authz`, `identity`, `p0`

**Problem:** Wave 9 needs the public ingress boundary to fail closed and propagate a normalized security context so downstream services never need to guess who is calling or which policy version was used.

**Scope**
- Make `docs/reference/security/authz.md` the canonical authn/authz contract if any wording still diverges.
- Enforce JWT/OAuth2 or the documented equivalent at the public ingress boundary.
- Propagate normalized security context and decision metadata to downstream calls.
- Normalize ingress security errors through the canonical Product 1.0 error model.
- Keep security logs, metrics, and traces free of secrets and raw payloads.

**Acceptance Criteria**
- Public ingress requests are rejected by default unless identity and policy checks succeed.
- Security context is visible to downstream components in a deterministic form.
- Authn/authz failures map to canonical errors and bounded telemetry.
- No secrets or raw payloads are emitted into logs or labels.

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

### W9-02 — Service identity, policy snapshots, and deterministic policy decisions

**Type:** Identity / Policy Contract  
**Labels:** `product-1.0-wave-9`, `identity`, `policy`, `security`, `p0`

**Problem:** Wave 9 needs internal calls to be attributable to a service identity and evaluated against versioned policy snapshots so policy drift cannot silently change runtime behavior.

**Scope**
- Define the canonical service-identity propagation mechanism for internal calls.
- Make policy decisions versioned and traceable with explicit snapshot metadata.
- Preserve deterministic replay markers on security decisions.
- Keep multi-tenant access controls explicit and documented.
- Add policy decision fixtures that prove fail-closed behavior on backend outage.

**Acceptance Criteria**
- Internal service calls are attributable to an identity that can be audited.
- Policy evaluation carries a versioned snapshot identifier.
- Replay evidence can reconstruct the policy decision path.
- Policy backend outages do not result in silent allow behavior.

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

### W9-03 — Sandbox isolation, secrets lifecycle, and provider boundary hardening

**Type:** Isolation / Secrets Contract  
**Labels:** `product-1.0-wave-9`, `isolation`, `security`, `secrets`, `p0`

**Problem:** Wave 9 needs compiler, driver-manager, and runtime plugin paths to remain isolated so provider secrets and execution sandboxes cannot leak into public or cross-tenant surfaces.

**Scope**
- Enforce sandbox-profile selection for compiler, driver-manager, and runtime plugin paths.
- Confine provider secrets to the documented secrets lifecycle integration points.
- Keep provider-specific SDK behavior outside the public contract boundary.
- Normalize provider and secrets errors into canonical Product 1.0 error shapes.
- Add tests for sandbox failure, secret redaction, and provider confinement.

**Acceptance Criteria**
- Sandbox-profile rules are explicit and test-covered.
- Secrets never traverse a public contract or a raw telemetry label.
- Provider-specific failures are normalized and retryability is correct.
- Isolation failures default to fail-closed behavior.

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

### W9-04 — Audit store, security telemetry, and replayable security evidence

**Type:** Audit / Observability Contract  
**Labels:** `product-1.0-wave-9`, `audit`, `security`, `observability`, `p1`

**Problem:** Wave 9 needs the security subsystem to leave an immutable, replayable evidence trail without leaking secrets or introducing unbounded telemetry.

**Scope**
- Define the canonical audit sink for security decisions and policy snapshots.
- Ensure security telemetry remains bounded and secret-free.
- Keep security-related trace continuity visible across the boundary decisions.
- Record evidence sufficient for replay and review of allow/deny decisions.
- Add or update security telemetry tests and operator-facing documentation.

**Acceptance Criteria**
- Security decisions are attributable and replayable from the audit trail.
- Telemetry remains bounded and does not expose raw payloads or secrets.
- Security evidence is operator-visible without requiring service-local state.
- The audit path is documented in the architecture and reference sources.

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

### W9-05 — Security conformance, fail-closed gating, and release evidence bundle

**Type:** Conformance / Release Governance  
**Labels:** `product-1.0-wave-9`, `security`, `conformance`, `release-evidence`, `p1`

**Problem:** Wave 9 needs release-quality proof that the security baseline, policy decisions, isolation, and audit evidence stay aligned across regressions.

**Scope**
- Add quality regression gates using fixed fixtures.
- Define which security failures block release and which are informational only.
- Create or update the Wave 9 compatibility report.
- Create or update the Wave 9 release-readiness checklist.
- Create or update the Wave 9 exit evidence bundle.
- Document security, audit, and isolation evidence paths.

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
