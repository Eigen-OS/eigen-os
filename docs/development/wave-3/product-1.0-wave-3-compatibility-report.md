# Product 1.0 Wave 3 Compatibility Report

**Status:** W3-04 closure draft  
**Scope:** compiler artifact persistence, QFS L3 boundary, lineage metadata, integrity metadata, immutability semantics

| Issue | Version Impact | Affected Interfaces | Compatibility | Breaking Marker | Migration Notes | Release Notes Draft | Evidence |
|---|---|---|---|---|---|---|---|
| W3-04 Compiler artifact persistence handoff to QFS | MINOR | Compiler contract; QFS; compiler metadata; compiled artifact layout | Backward-compatible | false | None | Added: QFS v1 compiled artifact metadata, lineage, and immutable sidecar write behavior; Changed: compiler persistence now uses canonical compiled artifact names; Fixed: duplicate-write and missing-sidecar handling | W3-E04 |
| W3-05 Compiler observability, metrics, and replay evidence | MINOR | Metrics, tracing, compiler logs, compatibility matrix, migration docs | Backward-compatible | false | None | Added: compiler contract marker metrics, bounded stage timing, replay counter, stage correlation logs; Changed: compiler observability contract now has a dedicated reference; Fixed: replay/duplicate compile evidence is fixture-backed | W3-E05 |

## W3-04 closure requirements

- Canonical compiled artifact names are documented.
- Metadata includes lineage and integrity data.
- Duplicate writes are rejected.
- Replay reads are validated.
- Sidecars are explicitly marked authoritative or advisory.
- Contract marker metrics are present.
- Trace continuity survives compilation.
- Labels are bounded and stable.
- Replay evidence is fixture-backed and test-covered.

---

## 1. Compatibility rules

Wave 3 changes follow these rules:

1. Compiler changes that alter accepted Eigen-Lang constructs, forbidden constructs, metadata requirements, AQO bytes, artifact layout, or compiler error mapping are **breaking** unless explicitly additive and backward-compatible.
2. AQO schema or canonicalization changes that alter the canonical bytes, field semantics, or required invariants are **breaking** (MAJOR).
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
| W3-01 Eigen-Lang v1.0 grammar/AST allowlist and safety model | TBD | Compiler contract; Internal API; Error mapping | TBD | TBD | TBD | TBD | W3-E01 |
| W3-02 Internal compiler RPC alignment and JobSpec-to-compiler request mapping | TBD | Internal API; Compiler contract; JobSpec | TBD | TBD | TBD | TBD | W3-E02 |
| W3-03 AQO canonicalization, schema validation, and deterministic emission | TBD | Compiler contract; AQO; Compatibility matrix | TBD | TBD | TBD | TBD | W3-E03 |
| W3-04 Compiler artifact persistence handoff to QFS | TBD | Compiler contract; QFS; Migration docs | TBD | TBD | TBD | TBD | W3-E04 |
| W3-05 Compiler observability, metrics, and replay evidence | TBD | Metrics; Trace context; Compatibility matrix | TBD | TBD | TBD | TBD | W3-E05 |
| W3-06 Wave 3 compatibility report, migration notes, and exit evidence bundle | PATCH | Compatibility matrix; Migration docs | Backward-compatible | false | None | Added: closure evidence bundle; Changed: Wave 3 closure records now point to compiler/AQO/QFS slices | W3-E06 |
| W3-07 Inventory and plan synchronization for Wave 3 concrete mappings | PATCH | Inventory; Parent plan; Docs links | Backward-compatible | false | None | Added: concrete Wave 3 inventory rows; Changed: plan references now include compiler/QFS slices | W3-E07 |
| W3-08 RFC/ADR finalization or explicit no-new-governance decision | PATCH | Governance docs | Backward-compatible | false | None | Added: governance decision record; Changed: Wave 3 can proceed without contract expansion or with explicit RFC/ADR | W3-E08 |

---

## 3. W3-01 Detailed Compatibility Analysis

### Version Impact: TBD

The final version impact depends on the accepted Eigen-Lang subset and whether the current implementation already matches the normative allowlist. If only clarifying documentation and tests are needed, the issue may stay `PATCH` or `MINOR`. If the accepted language or safety model changes, it is `MAJOR`.

### Affected Interfaces

1. **Compiler contract**
   - Accepted AST nodes
   - Forbidden constructs
   - Import/function/decorator allowlists
   - Resource-limit behavior
   - Canonical compiler error mapping

2. **Internal API**
   - Compiler request shaping and request metadata
   - Validation and failure semantics
   - Trace/request context propagation

### Compatibility Statement

**Backward-compatible only if** the implementation merely codifies the already-documented subset without expanding or narrowing behavior.

If the allowlist or forbidden-construct matrix changes current behavior, it is not backward-compatible.

### Migration Notes

- Document any construct that becomes unsupported.
- Add explicit test fixtures for newly rejected forms.
- Update compiler diagnostics and release notes for any changed error mapping.

---

## 4. W3-02 Detailed Compatibility Analysis

### Version Impact: TBD

Compiler request mapping may be additive if the request envelope and metadata are extended without changing current callers. Any change to input precedence, required metadata, or normalized digest rules can become breaking if it changes observed behavior.

### Affected Interfaces

1. **Internal API**
   - Compiler request messages
   - Request metadata
   - JobSpec-to-compiler mapping

2. **Compiler contract**
   - Source precedence
   - Option canonicalization
   - Target metadata interpretation

### Compatibility Statement

Backward-compatible only if the mapping is additive and old callers still submit valid compile requests.

### Migration Notes

- Add migration notes for new required fields.
- Preserve legacy accepted request forms where the source-of-truth allows them.
- Document deterministic request-digest changes if they alter cache keys or replay hashes.

---

## 5. W3-03 Detailed Compatibility Analysis

### Version Impact: TBD

AQO canonicalization is sensitive because canonical bytes are part of the compatibility surface. Any change to required fields, serialization order, or semantic invariants may be breaking.

### Affected Interfaces

1. **AQO contract**
   - Required top-level fields
   - Opcode/invariant validation
   - Canonical JSON serialization
   - Hashing/replay semantics

2. **Compiler output**
   - Deterministic AQO bytes
   - Metadata and checksum records

### Compatibility Statement

Backward-compatible only if the emitted AQO bytes and validation rules remain semantically equivalent and old fixtures continue to pass.

### Migration Notes

- Update golden fixtures for any changed canonical bytes.
- Record hash changes in release notes and evidence.
- Add schema migration notes if the AQO document shape changes.

---

## 6. W3-04 Detailed Compatibility Analysis

### Version Impact: TBD

QFS persistence changes may be additive if they only add metadata or paths. They are breaking if they rename canonical artifact locations or remove required lineage fields.

### Affected Interfaces

1. **QFS**
   - Artifact layout
   - Metadata records
   - Retention / immutability rules
   - Integrity verification behavior

2. **Compiler**
   - Artifact handoff boundary
   - Output persistence contract

### Compatibility Statement

Backward-compatible only if the compiler continues to persist through the documented QFS boundary and all existing artifact references remain valid.

### Migration Notes

- Provide mapping from legacy local artifact paths to QFS paths.
- Record any new lineage fields as additive.
- Document any transient dual-write or migration window.

---

## 7. W3-05 Detailed Compatibility Analysis

### Version Impact: TBD

Observability can be additive when new metrics and traces are bounded and old consumers remain valid. It becomes breaking if label sets become unbounded or if required contract markers disappear.

### Affected Interfaces

1. **Metrics**
   - Contract markers
   - Label sets
   - Histogram/counter families

2. **Trace context**
   - Span continuity
   - Correlation IDs
   - Stage timing

### Compatibility Statement

Backward-compatible only if metrics remain bounded and trace continuity is preserved across compile and persistence paths.

### Migration Notes

- Add new metrics without removing the existing contract markers.
- Keep labels finite and documented.
- Record any renamed metrics in the evidence bundle.

---

## 8. Closure requirements

Wave 3 closure requires:

- ✓ No TBD values in W3-06/W3-07/W3-08 rows
- ✓ Version Impact, Compatibility, Breaking Marker all defined
- ✓ Migration notes documented where needed
- ✓ Release notes drafted
- ✓ Evidence links provided (W3-E01 through W3-E08)
- ✓ Golden parser/AQO/persistence evidence included
- ✓ Wave 4 handoff states that QFS maturity can proceed without reopening compiler ownership

---

## 9. Wave 3 closure statement

Wave 3 closure documentation is aligned to the compiler/AQO/QFS slices described by the source-of-truth docs. Once the issue ledger is completed and evidence links are populated, the Wave 3 package is sufficient to close the compiler contract boundary and hand off durable storage maturity to Wave 4.
