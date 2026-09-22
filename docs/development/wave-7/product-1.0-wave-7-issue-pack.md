# Product 1.0 Wave 7 Issue Pack

**Wave:** Product 1.0 Wave 7 — Neuro-Symbolic Compiler and GNN Optimizer
**Status:** Planning baseline
**Parent execution plan:** `docs/development/wave-7/product-1.0-wave-7-execution-plan.md`

---

## W7-01 — Neuro-Symbolic Compiler contract freeze

### Goal

Freeze the compiler contract that turns Eigen-Lang into normalized AQO / IR artifacts with deterministic error semantics.

### Normative references

- `docs/architecture/components/compiler.md`
- `docs/architecture/components/neuro-symbolic-core.md`
- `docs/reference/eigen-lang.md`
- `docs/reference/formats/aqo.md`
- `docs/reference/error-model.md`
- [RFC 0055 — Product 1.0 Neuro-Symbolic Compiler Contract](../../rfcs/0055-product-1.0-neuro-symbolic-compiler-contract.md)
- [ADR 0047 — Product 1.0 Neuro-Symbolic Compiler Contract](../../docs/adr/0047-product-1.0-neuro-symbolic-compiler-contract.md)

### Required implementation slices

1. Freeze Eigen-Lang lowering semantics.
2. Freeze compiler-side normalization rules.
3. Freeze structured error mapping for compiler failures.
4. Make output artifacts replay-safe and traceable.

### Required tests

- Deterministic compile fixture.
- Invalid Eigen-Lang rejection.
- AQO normalization fixture.
- Error mapping fixture.

### Exit evidence

- Compiler contract matrix.
- Deterministic compile replay report.
- Error taxonomy summary.

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

## W7-02 — GNN Optimizer contract freeze

### Goal

Freeze the optimizer contract that consumes compiler output and produces deterministic policy decisions, rankings, or optimization plans.

### Normative references

- `docs/architecture/components/gnn-optimizer.md`
- `docs/architecture/components/neuro-symbolic-core.md`
- `docs/reference/api/grpc-internal.md`
- `docs/reference/compiler-observability-contract.md`
- [RFC 0056 — Product 1.0 GNN Optimizer Contract](../../rfcs/0056-product-1.0-gnn-optimizer-contract.md)
- [ADR 0048 — Product 1.0 GNN Optimizer Contract](../../docs/adr/0048-product-1.0-gnn-optimizer-contract.md)

### Required implementation slices

1. Freeze optimizer input encoding.
2. Freeze optimizer scoring and ranking semantics.
3. Freeze fallback behavior when graph features are incomplete.
4. Freeze optimizer response metadata and confidence reporting.

### Required tests

- Deterministic optimizer replay.
- Graph encoding round-trip.
- Fallback path fixture.
- Confidence / explainability fixture.

### Exit evidence

- Optimizer contract matrix.
- Deterministic replay report.
- Confidence semantics note.

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

## W7-03 — Compiler ↔ Optimizer deterministic handoff

### Goal

Define the exact contract between compiler output and optimizer input so the pipeline is deterministic and versioned end to end.

### Normative references

- `docs/architecture/components/compiler.md`
- `docs/architecture/components/gnn-optimizer.md`
- `docs/architecture/components/neuro-symbolic-core.md`
- `docs/reference/formats/aqo.md`
- [RFC 0055 — Product 1.0 Neuro-Symbolic Compiler Contract](../../rfcs/0055-product-1.0-neuro-symbolic-compiler-contract.md)
- [RFC 0056 — Product 1.0 GNN Optimizer Contract](../../rfcs/0056-product-1.0-gnn-optimizer-contract.md)
- [ADR 0047 — Product 1.0 Neuro-Symbolic Compiler Contract](../../docs/adr/0047-product-1.0-neuro-symbolic-compiler-contract.md)
- [ADR 0048 — Product 1.0 GNN Optimizer Contract](../../docs/adr/0048-product-1.0-gnn-optimizer-contract.md)

### Required implementation slices

1. Define handoff schema boundaries.
2. Ensure no hidden state crosses the boundary.
3. Version the optimizer payload envelope.
4. Preserve stable identifiers across compile and optimization stages.

### Required tests

- Handoff schema validation.
- Stable identifier propagation.
- Boundary rejection for unsupported fields.
- Replay determinism fixture.

### Exit evidence

- Handoff schema document.
- Boundary compatibility report.
- Replay-safe pipeline evidence.

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

## W7-04 — Optimization explainability and observability

### Goal

Make optimization decisions explainable, traceable, and bounded for release evidence.

### Normative references

- `docs/reference/compiler-observability-contract.md`
- `docs/architecture/components/observability.md`
- `docs/architecture/components/compiler.md`
- `docs/architecture/components/gnn-optimizer.md`
- [RFC 0055 — Product 1.0 Neuro-Symbolic Compiler Contract](../../rfcs/0055-product-1.0-neuro-symbolic-compiler-contract.md)
- [RFC 0056 — Product 1.0 GNN Optimizer Contract](../../rfcs/0056-product-1.0-gnn-optimizer-contract.md)
- [ADR 0047 — Product 1.0 Neuro-Symbolic Compiler Contract](../../docs/adr/0047-product-1.0-neuro-symbolic-compiler-contract.md)
- [ADR 0048 — Product 1.0 GNN Optimizer Contract](../../docs/adr/0048-product-1.0-gnn-optimizer-contract.md)

### Required implementation slices

1. Define explainability payloads.
2. Add bounded trace and metric fields.
3. Preserve decision lineage from compiler to optimizer.
4. Expose confidence / fallback metadata.

### Required tests

- Trace continuity fixture.
- Explainability payload fixture.
- Metric bounds fixture.
- Confidence metadata validation.

### Exit evidence

- Observability contract note.
- Explainability sample bundle with compiler decision lineage, optimizer trace continuity, and fallback metadata.
- Bounded metrics report.

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

## W7-05 — Compiler artifact persistence and release evidence

### Goal

Make compiler/optimizer outputs persistable, auditable, and usable as release evidence.

### Normative references

- `docs/architecture/components/qfs.md`
- `docs/reference/formats/qfs-layout.md`
- `docs/reference/compiler-observability-contract.md`
- `docs/architecture/components/compiler.md`
- [RFC 0055 — Product 1.0 Neuro-Symbolic Compiler Contract](../../rfcs/0055-product-1.0-neuro-symbolic-compiler-contract.md)
- [ADR 0047 — Product 1.0 Neuro-Symbolic Compiler Contract](../../docs/adr/0047-product-1.0-neuro-symbolic-compiler-contract.md)

### Required implementation slices

1. Define artifact persistence paths.
2. Define release evidence bundle structure.
3. Ensure replay-safe artifact naming.
4. Tie artifact provenance to compile and optimization runs.

### Required tests

- Artifact persistence fixture.
- Provenance trace fixture.
- Evidence bundle validation.
- Replay-safe path fixture.

### Exit evidence

- Evidence bundle.
- Artifact manifest.
- Provenance report.

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
