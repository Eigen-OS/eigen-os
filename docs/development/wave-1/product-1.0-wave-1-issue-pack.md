# Product 1.0 Wave 1 Issue Pack

This document is a ready-to-use set of GitHub issues for **Product 1.0 Wave 1 — Public API, JobSpec, and error model closure**.

**Context sources:**
- `docs/development/product-1.0-contract-alignment-plan.md`
- `docs/development/wave-1/product-1.0-wave-1-execution-plan.md`
- `docs/development/product-1.0-contract-inventory.md`
- `docs/development/product-1.0-version-policy.md`
- `docs/reference/api/grpc-public.md`
- `docs/reference/jobspec.md`
- `docs/reference/error-model.md`
- `docs/reference/error-mapping.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`
- `rfcs/0049-product-1.0-public-api-jobspec-error-boundary.md`

---

## Every implementation issue MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
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

- **Milestone:** `Product 1.0 Wave 1 Public Boundary Closure`
- **Suggested labels:** `product-1.0`, `product-1.0-wave-1`, `api`, `jobspec`, `errors`, `compatibility`, `conformance`

---

## Priority and ownership proposal

| Issue | Priority | Proposed owner group |
|---|---|---|
| W1-01 Public proto/reference coverage matrix and envelope decisions | P0 | API Platform + Architecture |
| W1-02 Public gRPC envelopes, version negotiation, and compatibility rejection | P0 | System API + API Platform |
| W1-03 SubmitJob idempotency, payload limits, and request persistence | P0 | System API + Runtime Reliability |
| W1-04 JobSpec 1.0 schema, parser/normalizer, canonical digest, and fixtures | P0 | CLI + System API + Packaging |
| W1-05 Canonical public error model and error mapping conformance | P0 | System API + Developer Experience |
| W1-06 CLI/SDK public submission conformance baseline | P1 | CLI/SDK + Developer Experience |
| W1-07 Public API observability markers and trace continuity smoke gate | P1 | Observability + System API |
| W1-08 Wave 1 compatibility report, migration notes, and release evidence bundle | P1 | Architecture/Governance + Tech Writing |

---

## Issues

### W1-01 — Public proto/reference coverage matrix and envelope decisions

**Type:** API Contract / Governance  
**Labels:** `product-1.0-wave-1`, `api`, `proto`, `compatibility`, `p0`

**Problem:** Public reference docs and current `eigen.api.v1` protos must be reconciled before behavior changes; otherwise implementation can accidentally preserve MVP gaps as Product 1.0 behavior.

**Scope**
- Build a method/message/field matrix from public reference docs to `proto/eigen/api/v1/*`.
- Decide which public envelopes are required, optional, or explicitly deferred.
- Decide REST mirror scope for Wave 1: implement, defer, or remove from Product 1.0 scope.
- Update manifest/inventory mappings when planned schema/test paths become concrete.

**Acceptance Criteria**
- Coverage matrix lists every public method, request, response, status/error detail, and marker metric.
- Deferred or breaking public behavior has explicit compatibility rationale.
- RFC 0049 / ADR 0035 are updated if decisions change normative behavior.

---

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
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

### W1-02 — Public gRPC envelopes, version negotiation, and compatibility rejection

**Type:** API Contract / Gateway Runtime  
**Labels:** `product-1.0-wave-1`, `system-api`, `grpc`, `versioning`, `p0`

**Problem:** Product 1.0 public calls require stable request metadata and deterministic compatibility rejection instead of ad-hoc MVP request handling.

**Scope**
- Add/align public envelope fields: `contract_version`, `request_id`, `idempotency_key`, `trace_context`, `deadline`, and tenant/project context when in scope.
- Implement version negotiation and rejection for unsupported/incompatible contract versions.
- Add negative tests for missing, malformed, future, and unsupported versions.

**Acceptance Criteria**
- Public gateway accepts documented compatible versions and rejects incompatible versions with canonical errors.
- Envelope defaults are deterministic and documented.
- Compatibility report declares whether any existing client payload must migrate.

---

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
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

### W1-03 — SubmitJob idempotency, payload limits, and request persistence

**Type:** API Behavior / Reliability  
**Labels:** `product-1.0-wave-1`, `submit-job`, `idempotency`, `payload-limits`, `p0`

**Problem:** `SubmitJob` must be safe for retries and bounded before Wave 2 delegates lifecycle to Kernel/QRTX.

**Scope**
- Normalize request payloads before idempotency comparison.
- Persist idempotency records with configurable TTL.
- Return the same `job_id` for same key plus same normalized request.
- Return canonical conflict/precondition error for same key plus different normalized request.
- Enforce payload limits before forwarding to internal services.

**Acceptance Criteria**
- Idempotency replay and conflict tests cover success, duplicate, mismatch, TTL expiry, and persistence restart profile if supported.
- Payload-limit tests prove oversized requests fail before forwarding.
- Metrics include accepted/replayed/conflict/limit outcomes with bounded labels.

---

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
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

### W1-04 — JobSpec 1.0 schema, parser/normalizer, canonical digest, and fixtures

**Type:** JobSpec Contract / Client Input  
**Labels:** `product-1.0-wave-1`, `jobspec`, `cli`, `schema`, `p0`

**Problem:** JobSpec is the public job input contract; Wave 1 must make CLI and System API parse identical inputs into identical canonical payloads.

**Scope**
- Add or finalize a versioned JobSpec 1.0 JSON Schema/YAML fixture set.
- Implement shared parser/normalizer behavior for CLI and System API.
- Generate deterministic canonical digest and package metadata.
- Cover minimal, full, invalid, future-compatible, and migration fixture cases.
- Map JobSpec scheduling/security/observability fields into the internal request envelope without leaking internal-only fields to clients.

**Acceptance Criteria**
- CLI and System API produce byte-stable normalized output/digest for identical JobSpec fixtures.
- Invalid inputs map to canonical validation errors.
- Compatibility report documents accepted previous JobSpec versions and migration behavior.

---

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
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

### W1-05 — Canonical public error model and error mapping conformance

**Type:** Error Contract / Conformance  
**Labels:** `product-1.0-wave-1`, `errors`, `conformance`, `p0`

**Problem:** Public callers need stable status codes, reason codes, retryability, and structured details before internal service ownership changes.

**Scope**
- Implement public error normalization using `docs/reference/error-model.md`.
- Implement public mapping coverage from `docs/reference/error-mapping.md`.
- Add structured `google.rpc.Status` details where supported.
- Add conformance tests for validation, auth, idempotency conflict, version mismatch, payload limit, deadline, cancellation, unavailable, and internal failures.

**Acceptance Criteria**
- Every public negative fixture asserts status, reason, retryability, and detail shape.
- No raw internal exception or provider-specific error leaks through public API.
- Breaking status/reason changes include MAJOR marker and migration notes.

---

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
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

### W1-06 — CLI/SDK public submission conformance baseline

**Type:** Client Contract / Developer Experience  
**Labels:** `product-1.0-wave-1`, `cli`, `sdk`, `conformance`, `p1`

**Problem:** Clients must generate Product 1.0-compliant envelopes and JobSpec payloads so future SDKs inherit one conformance baseline.

**Scope**
- Update CLI submission path for canonical envelope, trace context, idempotency key behavior, and JobSpec normalization.
- Add file-based and inline JobSpec tests.
- Define SDK conformance expectations before adding additional language SDKs.
- Document migration from legacy CLI payload shapes if any are removed or changed.

**Acceptance Criteria**
- CLI conformance tests submit minimal/full fixtures and assert normalized public payloads.
- SDK baseline describes required request metadata and negative-test obligations.
- Release notes explain user-visible CLI changes.

---

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
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

### W1-07 — Public API observability markers and trace continuity smoke gate

**Type:** Observability Contract / Operations  
**Labels:** `product-1.0-wave-1`, `metrics`, `tracing`, `observability`, `p1`

**Problem:** Wave 1 needs public-boundary observability evidence so operators can diagnose external request failures without internal lifecycle coupling.

**Scope**
- Add public API contract marker metric with contract version and bounded outcome labels.
- Propagate W3C trace context from CLI/SDK through System API request handling.
- Add smoke tests for marker emission, bounded labels, and trace/request correlation.
- Document metric additions in compatibility report.

**Acceptance Criteria**
- Metrics are additive or explicitly versioned if names change.
- Label cardinality is bounded by tests.
- Exit evidence includes sample scrape/log/trace correlation.

---

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
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

### W1-08 — Wave 1 compatibility report, migration notes, and release evidence bundle

**Type:** Release Governance / Evidence  
**Labels:** `product-1.0-wave-1`, `release`, `compatibility`, `evidence`, `p1`

**Problem:** Wave 1 cannot close until every public-boundary change has compatibility, migration, and release-note evidence.

**Scope**
- Complete `docs/development/wave-1/product-1.0-wave-1-compatibility-report.md`.
- Complete `docs/development/wave-1/product-1.0-wave-1-exit-evidence-bundle.md`.
- Update manifest/inventory status for implemented slices.
- Attach release notes and migration notes for every MAJOR or behavior-changing issue.

**Acceptance Criteria**
- All W1-01..W1-07 acceptance criteria map to objective evidence.
- Compatibility report has no unknown Version Impact or Breaking Marker entries.
- Release readiness checklist is fully checked before Wave 2 starts.

---

## Required issue completion block MUST retain and complete this block before closure:

## Summary
- 
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- API | CLI payloads | Plugin envelopes | Compatibility matrix | JobSpec | AQO | QFS | Metrics -->
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
