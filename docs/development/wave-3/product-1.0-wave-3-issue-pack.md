# Product 1.0 Wave 3 Issue Pack

This document is a ready-to-use set of GitHub issues for **Product 1.0 Wave 3 — Compiler, Eigen-Lang, and AQO closure**.

**Context sources:**
- `docs/development/product-1.0-contract-alignment-plan.md`
- `docs/development/wave-3/product-1.0-wave-3-execution-plan.md`
- `docs/development/product-1.0-contract-inventory.md`
- `docs/development/product-1.0-version-policy.md`
- `docs/architecture/components/compiler.md`
- `docs/architecture/components/qfs.md`
- `docs/reference/eigen-lang.md`
- `docs/reference/formats/aqo.md`
- `docs/reference/formats/qfs-layout.md`
- `docs/reference/jobspec.md`
- `docs/reference/api/grpc-internal.md`
- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/cluster-runtime-observability-contract.md`
- `docs/reference/error-model.md`
- `rfcs/0051-product-1.0-compiler-aqo-closure.md`
- `docs/adr/0037-product-1.0-compiler-aqo-closure.md`

---

## Every implementation issue MUST retain and complete this block before closure:

## Summary
-
## Validation
- [ ] Tests added/updated
- [ ] Documentation updated (if contracts/behavior changed)

## Versioning & Compatibility (required)
- **Version Impact**: <!-- MAJOR | MINOR | PATCH | NONE -->
- **Affected Interfaces**: <!-- Internal API | Public API facade | Compiler contract | AQO | QFS | Metrics | Trace context | Compatibility matrix | Migration docs -->
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

- **Milestone:** `Product 1.0 Wave 3 Compiler AQO Closure`
- **Suggested labels:** `product-1.0`, `product-1.0-wave-3`, `compiler`, `aqo`, `eigen-lang`, `qfs`, `internal-api`, `compatibility`, `conformance`

---

## Priority and ownership proposal

| **Issue** | **Priority** | **Proposed owner group** |
|---|---|---|
| W3-01 Eigen-Lang v1.0 grammar/AST allowlist and safety model | P0 | Compiler + Architecture |
| W3-02 Internal compiler RPC alignment and JobSpec-to-compiler request mapping | P0 | Compiler + System API + Kernel/QRTX |
| W3-03 AQO canonicalization, schema validation, and deterministic emission | P0 | Compiler + AQO/QFS owners |
| W3-04 Compiler artifact persistence handoff to QFS | P0 | Compiler + QFS + Kernel/QRTX |
| W3-05 Compiler observability, metrics, and replay evidence | P1 | Compiler + Observability |
| W3-06 Wave 3 compatibility report, migration notes, and exit evidence bundle | P1 | Architecture/Governance + Tech Writing |
| W3-07 Inventory and plan synchronization for Wave 3 concrete mappings | P1 | Architecture + Governance |
| W3-08 RFC/ADR finalization or explicit no-new-governance decision | P1 | Architecture + RFC/ADR owners |

---

## Issues

### W3-01 — Eigen-Lang v1.0 grammar/AST allowlist and safety model

**Type:** Language Contract / Compiler Safety
**Labels:** `product-1.0-wave-3`, `compiler`, `eigen-lang`, `safety`

**Problem:** The compiler must enforce a canonical accepted subset of Eigen-Lang v1.0. Ambiguous syntax, undocumented constructs, and unsafe execution paths must be eliminated before AQO closure.

#### Scope

- Build a complete construct matrix from `docs/reference/eigen-lang.md` and `docs/architecture/components/compiler.md`.
- Define allowed AST nodes, forbidden nodes, allowed imports, allowed builtins, allowed decorators, and allowed expressions.
- Formalize canonical compiler error mapping for syntax, unsupported features, forbidden constructs, missing source, and resource limits.
- Ensure the compiler never executes user code and never imports out-of-allowlist modules.
- Add parser/validator fixtures for accepted and rejected source snippets.
- Update Product 1.0 inventory/manifest mappings if grammar/schema/test paths become concrete.

#### Acceptance Criteria

- Accepted subset is explicit and test-covered.
- Forbidden AST/path rules fail deterministically with canonical errors.
- Compiler safety model is documented and enforced.
- Version impact and migration notes are recorded for any behavior change.

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

### W3-02 — nternal compiler RPC alignment and JobSpec-to-compiler request mapping

**Type:** Internal API Contract / Request Shaping
**Labels:** `product-1.0-wave-3`, `compiler`, `internal-api`, `jobspec`

**Problem:** Compiler requests must carry canonical metadata and align with Kernel-owned lifecycle context. JobSpec-to-compiler mapping must be deterministic and versioned.

#### Scope

- Align internal compiler RPCs to the normative compiler reference and internal API expectations.
- Define request metadata: request ID, trace context, deadline, retry policy, security context, tenant/project scope, and source precedence.
- Map JobSpec fields to compiler inputs, options, and target metadata.
- Normalize compiler request digests and option canonicalization.
- Define failure behavior for invalid input combinations, missing source references, and unsupported target metadata.
- Update manifest/inventory mappings for any concrete request/proto path changes.

#### Acceptance Criteria

- Request mapping is deterministic and documented.
- Canonical metadata is present for compile requests.
- Invalid request combinations fail with canonical errors.
- Any breaking internal change carries migration notes.

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

### W3-03 — AQO canonicalization, schema validation, and deterministic emission

**Type:** Schema / Serialization / Conformance
**Labels:** `product-1.0-wave-3`, `aqo`, `compiler`, `conformance`

**Problem:** AQO must be emitted as canonical deterministic bytes and validated against the reference contract before persistence or downstream execution.

#### Scope

- Implement canonical AQO JSON serialization with stable ordering and no insignificant whitespace.
- Enforce AQO required fields and opcode/arity/parameter invariants from `docs/reference/formats/aqo.md`.
- Reject unknown opcodes, invalid measurement shapes, invalid qubit indices, and unsupported transport assumptions.
- Produce stable AQO digests and metadata.
- Add golden tests for valid and invalid AQO samples.
- Add schema validation and round-trip checks for the compiler output path.

#### Acceptance Criteria

- Identical inputs yield identical AQO bytes and hashes.
- AQO validation occurs before persistence.
- Canonical errors are returned for all structural and semantic violations.

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

### W3-04 — Compiler artifact persistence handoff to QFS

**Type:** Persistence Boundary / Contract Handoff
**Labels:** `product-1.0-wave-3`, `compiler`, `qfs`

**Problem:** Compiler outputs must be persisted through the QFS L3 contract, with lineage and integrity metadata, rather than via ad-hoc local paths.

#### Scope

- Define the canonical compiler output directory and artifact names in QFS terms.
- Persist AQO, compiler metadata, diagnostics, and optional sidecar artifacts through QFS L3.
- Record content digests, producer identity, contract version, timestamps, and lineage.
- Enforce retention and immutability expectations for compiler outputs.
- Add tests for missing artifact references, duplicate writes, and replayed artifact reads.
- Document what is authoritative versus advisory in compiler sidecar artifacts.

#### Acceptance Criteria

- No compiler output escapes the QFS contract boundary.
- Artifact metadata includes lineage and integrity data.
- Persistence behavior is deterministic and conformance-tested.

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

### W3-05 — Compiler observability, metrics, and replay evidence

**Type:** Observability / Conformance
**Labels:** `product-1.0-wave-3`, `observability`, `metrics`, `tracing`, `compiler`

**Problem:** Compiler behavior must be observable with bounded labels and deterministic replay evidence.

#### Scope

- Emit compiler contract marker metrics with bounded labels.
- Preserve trace/request context through parsing, validation, AQO emission, and QFS persistence.
- Add structured logs with stable correlation fields.
- Add conformance tests for stage timing, validation failures, digest emission, and replay/duplicate compile behavior.
- Document any intentionally deferred telemetry.

#### Acceptance Criteria

- Contract marker metrics are present.
- Trace continuity survives compilation and persistence.
- Labels are bounded and stable.
- Replay evidence is fixture-backed and test-covered.

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

### W3-06 — Wave 3 compatibility report, migration notes, and exit evidence bundle

**Type:** Governance / Closure
**Labels:** `product-1.0-wave-3`, `compatibility`, `migration`, `evidence`

**Problem:** Wave 3 cannot close without a formal compatibility report, migration notes, and evidence bundle linking compiler/AQO/QFS conformance to the source-of-truth docs.

#### Scope

- Build the compatibility report for all W3 issues.
- Record version impact, compatibility status, breaking markers, migration notes, release notes drafts, and evidence IDs.
- Draft the exit evidence bundle with commands, artifacts, expected results, and actual results.
- Ensure no unresolved `TBD` values remain for completed Wave 3 items.
- Link Wave 3 closure artifacts to Wave 4 handoff.

#### Acceptance Criteria

- Every W3 issue has a concrete compatibility row.
- Evidence IDs and artifact links are present.
- Wave 4 handoff is explicit and unambiguous.

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

### W3-07 — Inventory and plan synchronization for Wave 3 concrete mappings

**Type:** Governance / Documentation Sync
**Labels:** `product-1.0-wave-3`, `inventory`, `docs`, `governance`

**Problem:** Once Wave 3 mappings become concrete, the parent plan and inventory must reflect the exact proto/schema/test paths and ownership.

#### Scope

- Update `docs/development/product-1.0-contract-inventory.md` for compiler, Eigen-Lang, AQO, and QFS slice mappings.
- Update `docs/development/product-1.0-contract-alignment-plan.md` Wave 3 section with concrete implementation artifacts.
- Verify that all canonical references resolve.
- Ensure compatibility statuses reflect implementation reality.
- Add drift-gate coverage if needed.

#### Acceptance Criteria

- Inventory and parent plan are synchronized with Wave 3 concrete paths.
- No stale references remain for implemented W3 slices.
- Any new concrete path has a conformance test mapping.

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

### W3-08 — RFC/ADR finalization or explicit no-new-governance decision

**Type:** Governance / Decision Gate
**Labels:** `product-1.0-wave-3`, `rfc`, `adr`, `governance`

**Problem:** If Wave 3 remains within the existing compiler/AQO/QFS source-of-truth docs, no new RFC/ADR is needed. If any scope expands the contract, it must be governed explicitly before implementation.

#### Scope

- Confirm whether Wave 3 can be completed under the existing normative docs.
- If yes, record the no-new-governance decision.
- If no, draft and approve the required RFC and ADR before implementation.
- Link the decision to the issue pack and compatibility report.
- Record any contract-expansion boundaries clearly.

#### Acceptance Criteria

- A clear yes/no governance decision exists.
- If new governance is required, it is created and linked.
- If no new governance is required, the decision is recorded and justified.

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