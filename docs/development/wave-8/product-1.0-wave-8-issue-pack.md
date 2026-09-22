# Product 1.0 Wave 8 Issue Pack

This document is a ready-to-use set of GitHub issues for **Product 1.0 Wave 8 — Knowledge Base and continuous learning loop**.

**Context sources:**
- `docs/development/product-1.0-contract-alignment-plan.md`
- `docs/development/wave-8/product-1.0-wave-8-execution-plan.md`
- `docs/development/product-1.0-contract-inventory.md`
- `docs/development/product-1.0-version-policy.md`
- `docs/reference/api/grpc-public.md`
- `docs/reference/api/grpc-internal.md`
- `docs/reference/intelligent-runtime-observability-contract.md`
- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/benchmark-observability-contract.md`
- `docs/architecture/components/knowledge-base.md`
- `docs/architecture/components/compiler.md`
- `docs/architecture/components/observability.md`
- `rfcs/0034-phase8a-knowledge-base-api-contract-v1.md`
- `rfcs/0035-phase8a-gnn-optimizer-service-contract-v1.md`
- `rfcs/0036-phase8a-continuous-learning-control-plane-contract-v1.md`
- `rfcs/0037-phase8a-qfs-l2-checkpoint-envelope-contract-v1.md`
- `docs/adr/0020-phase8a-knowledge-base-api-contract-v1.md`
- `docs/adr/0021-phase8a-gnn-optimizer-service-contract-v1.md`
- `docs/adr/0022-phase8a-continuous-learning-control-plane-contract-v1.md`
- `docs/adr/0023-phase8a-qfs-l2-checkpoint-envelope-contract-v1.md`

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

- **Milestone:** `Product 1.0 Wave 8 Knowledge Base and Continuous Learning Loop`
- **Suggested labels:** `product-1.0`, `product-1.0-wave-8`, `knowledge-base`, `learning-loop`, `observability`, `privacy`, `conformance`, `docs`

---

## Priority and ownership proposal

| Issue | Priority | Proposed owner group |
|---|---|---|
| W8-01 Knowledge Base records, decision logs, and provenance | P0 | Knowledge Base  Kernel/QRTX |
| W8-02 Optimization Knowledge Base deterministic reuse and query backend | P0 | Knowledge Base + Compiler + GNN Optimizer |
| W8-03 Continuous learning control plane and dataset assembly governance | P0 | Knowledge Base + Benchmark Service + Architecture |
| W8-04 Trace continuity and observability for KB/learning surfaces | P1 | Observability + Kernel/QRTX + Benchmark Service |
| W8-05 Privacy, retention, conformance, and release evidence bundle | P1 | Architecture/Governance + Docs + Security |

---

## Issues

### W8-01 — Knowledge Base records, decision logs, and provenance

**Type:** Data Contract / Decision Lineage
**Labels:** `product-1.0-wave-8`, `knowledge-base`, `provenance`, `lineage`, `p0`

**Problem:** Wave 8 needs the Knowledge Base to be more than a public record store; decision logs, provenance, and replay metadata must become first-class, queryable, and auditable.

**Scope**
- Make decision-log append/query behavior part of the authoritative KB surface.
- Preserve provenance, immutability, and bounded pagination semantics.
- Ensure tenant/project scoping remains explicit and deterministic.
- Keep raw payload leakage out of logs, records, and metric labels.
- Align public API documentation with the implemented record and decision-log surface.

**Acceptance Criteria**
- Decision logs are appendable and queryable through documented KB APIs.
- Provenance and replay metadata remain stable across repeated identical inputs.
- KB record and log retrieval stay bounded and deterministic.
- No raw payload leakage is introduced into logs or labels.

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

### W8-02 — Optimization Knowledge Base deterministic reuse and query backend

**Type:** Runtime Intelligence / Query Contract
**Labels:** `product-1.0-wave-8`, `knowledge-base`, `optimizer`, `query`, `p0`

**Problem:** Wave 8 needs an optimization-memory layer that can retrieve reusable knowledge deterministically instead of depending on ad hoc heuristics or opaque backend behavior.

**Scope**
- Define the OKB query surface or a documented pluggable backend interface.
- Support structural and vector query modes under bounded, deterministic semantics.
- Keep candidate selection replay-safe and version-pinned.
- Attach bounded explainability metadata to every returned candidate.
- Preserve compatibility with the frozen optimizer and compiler contract shapes.

**Acceptance Criteria**
- Reuse decisions are replay-stable under fixed seeds and fixed inputs.
- Query outputs include bounded provenance and explainability references.
- Any backend adapter remains behind a documented interface.
- No unstable labels or raw payloads are emitted.

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

### W8-03 — Continuous learning control plane and dataset assembly governance

**Type:** Governance / Learning Loop
**Labels:** `product-1.0-wave-8`, `learning-loop`, `governance`, `dataset`, `p0`

**Problem:** Wave 8 must turn runtime learning into a governed process with explicit dataset assembly, promotion, rollback, and privacy rules instead of an implicit data dump.

**Scope**
- Define the continuous-learning control plane and its deterministic trigger policy.
- Govern dataset assembly from optimizer, runtime, and benchmark evidence.
- Add promotion freeze, shadow validation, canary, and rollback controls.
- Establish retention, deletion, and quarantine rules for invalid batches.
- Record model lineage and evaluation evidence in the Knowledge Base.

**Acceptance Criteria**
- Dataset assembly is reproducible and policy-governed.
- Promotion and rollback rules are explicit and test-covered.
- Invalid or sensitive records are quarantined or rejected by policy.
- Learning-loop evidence is queryable in the KB.

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

### W8-04 — Trace continuity and observability for KB/learning surfaces

**Type:** Observability / Contract Evidence
**Labels:** `product-1.0-wave-8`, `observability`, `tracing`, `metrics`, `p1`

**Problem:** Wave 8 must preserve trace continuity from Kernel/QRTX through optimizer and benchmark surfaces into the Knowledge Base while keeping labels bounded and compatible with observability contracts.

**Scope**
- Preserve `request_id`, `trace_id`, and `traceparent` continuity across KB-related flows.
- Add or update bounded metrics for KB/learning surfaces without unbounded labels.
- Expose dashboards and alerts for decision-log pressure, learning-loop failures, and privacy/quarantine events.
- Ensure trace and metric artifacts remain operator-visible without leaking raw payloads.
- Keep observability aligned with the stable runtime contracts.

**Acceptance Criteria**
- Trace continuity survives append, query, and promotion paths.
- Metrics are scrapeable, bounded, and stable.
- Dashboards and alerts exist for the Wave 8 learning surface.
- No raw payload leakage is introduced into metrics or labels.

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

### W8-05 — Privacy, retention, conformance, and release evidence bundle

**Type:** Conformance / Release Governance
**Labels:** `product-1.0-wave-8`, `privacy`, `retention`, `conformance`, `release-evidence`, `p1`

**Problem:** Wave 8 needs release-quality proof that privacy, retention, learning-loop governance, and observability stay aligned across regressions.

**Scope**
- Add quality regression gates using fixed fixtures.
- Define which failures block release and which are informational only.
- Create or update the Wave 8 compatibility report.
- Create or update the Wave 8 release-readiness checklist.
- Create or update the Wave 8 exit evidence bundle.
- Document privacy, deletion, and quarantine evidence paths.

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
