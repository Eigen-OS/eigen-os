# Product 1.0 Wave 3 Compatibility Report

**Status:** Wave 3 closure record, aligned to compiler / AQO / QFS source-of-truth docs  
**Scope:** Eigen-Lang safety model, compiler request mapping, AQO canonicalization, compiler-to-QFS persistence, compiler observability, Wave 3 closure governance

Wave 3 closure is recorded as documentation-complete for the compiler/AQO/QFS slice. The rows below capture the compatibility status for every W3 issue and remove all remaining `TBD` placeholders from the closure record.

| Issue | Version Impact | Affected Interfaces | Compatibility | Breaking Marker | Migration Notes | Release Notes Draft | Evidence |
|---|---|---|---|---|---|---|---|
| W3-01 Eigen-Lang v1.0 grammar/AST allowlist and safety model | MINOR | Compiler contract; Internal API; Error mapping | Backward-compatible | false | None | Added: Eigen-Lang v1.0 allowlist enforcement, forbidden-construct rejection, canonical compiler errors; Changed: compiler safety rules now follow the documented subset; Fixed: ambiguous syntax and unsupported construct handling | W3-E01 |
| W3-02 Internal compiler RPC alignment and JobSpec-to-compiler request mapping | MINOR | Internal API; Compiler contract; JobSpec; Trace context | Backward-compatible | false | None | Added: canonical request metadata, request digest normalization, and deterministic JobSpec mapping; Changed: compiler request shaping now follows the kernel-owned lifecycle context; Fixed: missing source-precedence and unsupported request combinations | W3-E02 |
| W3-03 AQO canonicalization, schema validation, and deterministic emission | MINOR | Compiler contract; AQO; Compatibility matrix | Backward-compatible | false | None | Added: canonical AQO JSON serialization, schema validation, and stable digests; Changed: AQO output now follows the documented canonical ordering and invariants; Fixed: invalid opcode, arity, measurement-shape, and qubit-index rejection | W3-E03 |
| W3-04 Compiler artifact persistence handoff to QFS | MINOR | Compiler contract; QFS; Migration docs | Backward-compatible | false | Consumers must treat QFS L3 artifact references as authoritative and stop relying on ad-hoc local artifact paths | Added: QFS-backed compiler artifact metadata, lineage, and integrity records; Changed: compiler persistence now flows through the documented QFS boundary; Fixed: duplicate-write and missing-sidecar handling | W3-E04 |
| W3-05 Compiler observability, metrics, and replay evidence | MINOR | Metrics; Trace context; Compatibility matrix | Backward-compatible | false | None | Added: compiler contract marker metrics, bounded labels, deterministic digest logging, and replay evidence; Changed: trace continuity now spans parse, validation, emission, and persistence handoff; Fixed: duplicate replay observability gaps | W3-E05 |
| W3-06 Wave 3 compatibility report, migration notes, and exit evidence bundle | PATCH | Compatibility matrix; Migration docs; Evidence bundle | Backward-compatible | false | None | Added: closure evidence bundle and Wave 4 handoff links; Changed: Wave 3 closure records now point to compiler/AQO/QFS slices; Fixed: unresolved `TBD` values in the closure package | W3-E06 |
| W3-07 Inventory and plan synchronization for Wave 3 concrete mappings | PATCH | Inventory; Parent plan; Docs links | Backward-compatible | false | None | Added: concrete Wave 3 inventory rows and stable slice mappings; Changed: parent plan references now include compiler/QFS closure slices; Fixed: stale Wave 3 doc links | W3-E07 |
| W3-08 RFC/ADR finalization or explicit no-new-governance decision | PATCH | Governance docs | Backward-compatible | false | None | Added: explicit no-new-governance decision record; Changed: Wave 3 may close under the existing compiler/AQO/QFS source-of-truth docs; Fixed: ambiguity about whether a new RFC/ADR is required | W3-E08 |

---

## 1. Compatibility rules

Wave 3 changes follow these rules:

1. Compiler changes that alter accepted Eigen-Lang constructs, forbidden constructs, metadata requirements, AQO bytes, artifact layout, or compiler error mapping are **breaking** unless explicitly additive and backward-compatible.
2. AQO schema or canonicalization changes that alter canonical bytes, field semantics, or required invariants are **breaking** (MAJOR).
3. Compiler-to-QFS path changes that rename or remove artifact paths, metadata records, or lineage requirements are **breaking** unless only additive.
4. Internal compiler RPC changes that remove, rename, or change documented request metadata or response semantics are **breaking** unless additive.
5. Public `eigen.api.v1` behavior from Wave 1 must remain compatible. Any public breaking change requires separate public RFC/ADR approval.
6. Additive metadata fields, metrics, or trace attributes use `MINOR` when old consumers continue to function.
7. Documentation-only or non-semantic fixes use `PATCH` or `NONE` according to the Product 1.0 version policy.
8. Every breaking change requires migration notes, release notes, conformance fixture updates, and exit evidence.
9. Every changed Product 1.0 contract mapping must update `contracts/product-1.0/manifest.json` and `docs/development/product-1.0-contract-inventory.md` in the same implementation PR.

---

## 2. Issue compatibility ledger

| Issue | Version Impact | Affected Interfaces | Compatibility | Breaking Marker | Migration Notes | Release Notes Draft | Evidence |
|---|---|---|---|---|---|---|---|
| W3-01 Eigen-Lang v1.0 grammar/AST allowlist and safety model | MINOR | Compiler contract; Internal API; Error mapping | Backward-compatible | false | None | Added: Eigen-Lang v1.0 allowlist enforcement, forbidden-construct rejection, canonical compiler errors | W3-E01 |
| W3-02 Internal compiler RPC alignment and JobSpec-to-compiler request mapping | MINOR | Internal API; Compiler contract; JobSpec; Trace context | Backward-compatible | false | None | Added: canonical request metadata and deterministic JobSpec mapping | W3-E02 |
| W3-03 AQO canonicalization, schema validation, and deterministic emission | MINOR | Compiler contract; AQO; Compatibility matrix | Backward-compatible | false | None | Added: canonical AQO serialization and schema validation | W3-E03 |
| W3-04 Compiler artifact persistence handoff to QFS | MINOR | Compiler contract; QFS; Migration docs | Backward-compatible | false | Consumers must treat QFS L3 artifact references as authoritative and stop relying on ad-hoc local artifact paths | Added: QFS-backed compiler artifact metadata and lineage records | W3-E04 |
| W3-05 Compiler observability, metrics, and replay evidence | MINOR | Metrics; Trace context; Compatibility matrix | Backward-compatible | false | None | Added: compiler contract marker metrics and replay evidence | W3-E05 |
| W3-06 Wave 3 compatibility report, migration notes, and exit evidence bundle | PATCH | Compatibility matrix; Migration docs; Evidence bundle | Backward-compatible | false | None | Added: closure evidence bundle and Wave 4 handoff links | W3-E06 |
| W3-07 Inventory and plan synchronization for Wave 3 concrete mappings | PATCH | Inventory; Parent plan; Docs links | Backward-compatible | false | None | Added: concrete Wave 3 inventory rows and stable slice mappings | W3-E07 |
| W3-08 RFC/ADR finalization or explicit no-new-governance decision | PATCH | Governance docs | Backward-compatible | false | None | Added: explicit no-new-governance decision record | W3-E08 |

---

## 3. W3-01 Detailed Compatibility Analysis

**Version Impact:** MINOR  
**Affected Interfaces:** Compiler contract; Internal API; Error mapping  
**Compatibility:** Backward-compatible  
**Breaking Marker:** false  
**Migration Notes:** None

The implemented allowlist codifies the documented Eigen-Lang v1.0 subset. Unsupported or undocumented constructs fail with canonical compiler errors, while compliant callers continue to compile unchanged.

---

## 4. W3-02 Detailed Compatibility Analysis

**Version Impact:** MINOR  
**Affected Interfaces:** Internal API; Compiler contract; JobSpec; Trace context  
**Compatibility:** Backward-compatible  
**Breaking Marker:** false  
**Migration Notes:** None

The internal compiler request surface now carries canonical metadata and deterministic JobSpec mapping without changing the accepted request contract for compliant callers.

---

## 5. W3-03 Detailed Compatibility Analysis

**Version Impact:** MINOR  
**Affected Interfaces:** Compiler contract; AQO; Compatibility matrix  
**Compatibility:** Backward-compatible  
**Breaking Marker:** false  
**Migration Notes:** None

AQO output is canonicalized, schema-validated, and reproducible. Any fixture refresh is driven by the documented canonical form rather than by ad-hoc serialization behavior.

---

## 6. W3-04 Detailed Compatibility Analysis

**Version Impact:** MINOR  
**Affected Interfaces:** Compiler contract; QFS; Migration docs  
**Compatibility:** Backward-compatible  
**Breaking Marker:** false  
**Migration Notes:** Consumers must resolve compiler artifacts through QFS L3 references; legacy local-path lookups are no longer authoritative.

Compiler outputs now persist through the documented QFS boundary with lineage and integrity metadata. The handoff is compatible with the normative layout because the storage path contract is the documented source of truth.

---

## 7. W3-05 Detailed Compatibility Analysis

**Version Impact:** MINOR  
**Affected Interfaces:** Metrics; Trace context; Compatibility matrix  
**Compatibility:** Backward-compatible  
**Breaking Marker:** false  
**Migration Notes:** None

Compiler observability is additive: contract marker metrics remain bounded, trace continuity is preserved, and replay evidence is attached without removing existing observability signals.

---

## 8. W3-06 Detailed Compatibility Analysis

**Version Impact:** PATCH  
**Affected Interfaces:** Compatibility matrix; Migration docs; Evidence bundle  
**Compatibility:** Backward-compatible  
**Breaking Marker:** false  
**Migration Notes:** None

This closure issue is documentation-only. It records the compatibility decisions, migration notes, evidence IDs, and Wave 4 handoff without changing runtime behavior.

---

## 9. W3-07 Detailed Compatibility Analysis

**Version Impact:** PATCH  
**Affected Interfaces:** Inventory; Parent plan; Docs links  
**Compatibility:** Backward-compatible  
**Breaking Marker:** false  
**Migration Notes:** None

The inventory and parent plan are synchronized with the concrete compiler/AQO/QFS slice mappings so the implementation record matches the current source-of-truth documentation.

---

## 10. W3-08 Detailed Compatibility Analysis

**Version Impact:** PATCH  
**Affected Interfaces:** Governance docs  
**Compatibility:** Backward-compatible  
**Breaking Marker:** false  
**Migration Notes:** None

Wave 3 stays within the existing compiler/AQO/QFS source-of-truth docs, so no new RFC/ADR is required for closure. That decision is now explicit and linked to the closure package.

---

## 11. Closure requirements

Wave 3 closure requires:

- ✓ No `TBD` values remain in the W3-06, W3-07, and W3-08 closure rows
- ✓ Version Impact, Compatibility, and Breaking Marker are defined for every W3 issue
- ✓ Migration notes are present where needed and explicitly `None` where no migration is required
- ✓ Release notes drafts are populated for every W3 issue
- ✓ Evidence links are present for W3-E01 through W3-E08
- ✓ Golden parser / AQO / persistence evidence is mapped in the exit bundle
- ✓ Wave 4 handoff states that QFS maturity can proceed without reopening compiler ownership

---

## 12. Wave 3 closure statement

Wave 3 closure documentation is aligned to the compiler/AQO/QFS slices described by the source-of-truth docs. The closure package now contains concrete compatibility rows, migration notes, evidence links, and an explicit Wave 4 handoff. Wave 4 may begin with the compiler boundary closed and durable storage maturity continuing under QFS without reopening compiler ownership.
