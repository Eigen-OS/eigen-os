# Product 1.0 Wave 3 Release Readiness Checklist

**Status:** Wave 3 closure checklist template  
**Created:** 2026-06-05  

## Scope

This checklist closes Product 1.0 Wave 3 and should be completed together with:

- `docs/development/wave-3/product-1.0-wave-3-execution-plan.md`
- `docs/development/wave-3/product-1.0-wave-3-issue-pack.md`
- `docs/development/wave-3/product-1.0-wave-3-compatibility-report.md`
- `docs/development/wave-3/product-1.0-wave-3-exit-evidence-bundle.md`
- `docs/development/wave-3/product-1.0-wave-3-rfc-adr-gap-analysis.md`
- `docs/architecture/components/compiler.md`
- `docs/architecture/components/qfs.md`
- `docs/reference/eigen-lang.md`
- `docs/reference/formats/aqo.md`
- `docs/reference/formats/qfs-layout.md`

---

## Contract and governance gates

- [ ] The compiler contract matrix covers accepted syntax, forbidden constructs, canonical error behavior, and resource limits.
- [ ] The internal compiler request mapping is documented and versioned.
- [ ] AQO canonicalization, validation, and digest generation are implemented and test-covered.
- [ ] Compiler artifact persistence flows through QFS with explicit lineage and integrity metadata.
- [ ] Observability markers, bounded labels, and trace continuity are emitted and tested.
- [ ] Manifest and inventory entries are updated for any concrete proto/schema/conformance path changes.
- [ ] Every breaking or potentially breaking compiler/AQO/QFS change has migration notes and release evidence.
- [ ] The compatibility report has no unresolved `TBD` values for completed issues.

## Compiler and language gates

- [ ] Eigen-Lang v1.0 accepted subset is explicit and fixture-covered.
- [ ] Forbidden AST patterns and unsupported constructs fail deterministically.
- [ ] No user code is executed by the compiler.
- [ ] Resource limits are enforced with canonical errors.
- [ ] Diagnostics are stable across repeated runs.

## AQO gates

- [ ] AQO required fields are enforced.
- [ ] AQO canonical JSON serialization is byte-stable.
- [ ] AQO schema validation occurs before persistence or execution.
- [ ] Invalid arity, invalid measurement shapes, and unknown opcodes are rejected.
- [ ] Repeated identical compiles produce identical AQO hashes.

## QFS and artifact gates

- [ ] Compiler artifacts are written through the documented QFS L3 boundary.
- [ ] Artifact metadata includes content digest, producer, contract version, timestamps, and lineage.
- [ ] Integrity verification on read is implemented or explicitly documented as deferred.
- [ ] Missing artifact behavior is deterministic and test-covered.

## Observability and evidence gates

- [ ] Compiler contract marker metrics are emitted.
- [ ] Metric labels remain bounded and stable.
- [ ] Trace continuity survives parse, validation, emission, and persistence handoff.
- [ ] Exit evidence bundle links commands, fixtures, generated artifacts, and known limitations.
- [ ] Wave 4 handoff states that QFS maturity can proceed without reopening compiler ownership.

---

## Wave 4 handoff

Wave 4 may start after the Wave 3 closure commit. Wave 4 can rely on compiler outputs being persisted through QFS using deterministic hashes and lineage records, with Eigen-Lang and AQO already aligned to the normative references.
