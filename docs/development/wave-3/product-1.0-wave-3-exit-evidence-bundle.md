# Product 1.0 Wave 3 Exit Evidence Bundle

**Status:** Wave 3 closure evidence draft for W3-01 through W3-08  
**Scope:** Eigen-Lang safety model, compiler request mapping, AQO canonicalization, compiler-to-QFS persistence, compiler observability, governance closure  
**Created:** 2026-06-05  
**Updated:** 2026-06-05

---

## 1. Evidence index

| Evidence ID | Requirement | Command / artifact | Expected result | Actual result | Owner | Link |
|---|---|---|---|---|---|---|
| W3-E01 | Eigen-Lang grammar/AST allowlist and safety model | Parser/allowlist unit tests; language fixture suite | Accepted subset passes; forbidden constructs fail canonically | Pending | Compiler | TBD |
| W3-E02 | Internal compiler RPC alignment and JobSpec mapping | Internal compiler request tests; JobSpec mapping fixtures | Requests carry canonical metadata; source precedence is deterministic | Pending | Compiler + System API + Kernel/QRTX | TBD |
| W3-E03 | AQO canonicalization and schema validation | AQO golden tests; schema validation suite | Identical inputs yield identical AQO bytes and hashes | Pending | Compiler | TBD |
| W3-E04 | Compiler artifact persistence through QFS | QFS persistence tests; artifact layout fixtures | Compiler outputs persist through QFS L3 with lineage and integrity metadata | Pending | Compiler + QFS | TBD |
| W3-E05 | Compiler observability and trace continuity | Metrics/trace tests; scrape validation | Bounded metrics and trace continuity are present | Pending | Compiler + Observability | TBD |
| W3-E06 | Compatibility report, migration notes, and closure readiness | `docs/development/wave-3/product-1.0-wave-3-compatibility-report.md`; checklist review | No TBD in completed rows; all breaking markers explained; migration paths documented | Pending | Architecture/Governance | TBD |
| W3-E07 | Inventory and plan synchronization | `docs/development/product-1.0-contract-inventory.md`; `docs/development/product-1.0-contract-alignment-plan.md` | Wave 3 concrete mappings are reflected in inventory and parent plan | Pending | Architecture/Governance | TBD |
| W3-E08 | RFC/ADR decision record | `docs/development/wave-3/product-1.0-wave-3-rfc-adr-gap-analysis.md` | Explicit no-new-governance decision or linked RFC/ADR approval | Pending | Architecture/Governance | TBD |

---

## 2. W3-E01 Evidence Details

### Requirement
The compiler must accept only the documented Eigen-Lang v1.0 subset and reject forbidden constructs with canonical errors.

### Tests to execute
- language parsing fixtures for accepted snippets
- allowlist/forbidden construct rejection tests
- unsupported feature tests
- resource limit and invalid input tests

### Expected result
The accepted subset is stable and safe; forbidden constructs fail deterministically and do not execute user code.

### Known limitations
- None once the fixture suite is complete.

---

## 3. W3-E02 Evidence Details

### Requirement
Compiler requests must map JobSpec and kernel-owned request context into canonical internal compile inputs.

### Tests to execute
- request metadata propagation tests
- source precedence tests
- request digest/canonicalization tests
- missing source reference tests
- unsupported target metadata tests

### Expected result
Identical request inputs produce deterministic request digests and metadata; invalid combinations fail canonically.

### Known limitations
- None once request mapping tests are complete.

---

## 4. W3-E03 Evidence Details

### Requirement
AQO must be emitted canonically and validated before persistence or downstream use.

### Tests to execute
- AQO golden fixtures
- canonical JSON serialization tests
- opcode/arity/parameter invariant tests
- invalid measurement and invalid opcode tests
- identical-input repeated compile tests

### Expected result
AQO bytes are byte-stable and reproducible across repeated compiles with identical inputs.

### Known limitations
- None once golden fixtures are complete.

---

## 5. W3-E04 Evidence Details

### Requirement
Compiler outputs must persist through the documented QFS L3 boundary with metadata and lineage.

### Tests to execute
- artifact write/read tests
- lineage and metadata persistence tests
- integrity verification tests
- missing artifact reference tests
- duplicate-write or replay-read tests

### Expected result
Artifact layout is deterministic, lineage-aware, and consistent with the QFS contract.

### Known limitations
- If integrity verification is deferred, the limitation must be recorded explicitly.

---

## 6. W3-E05 Evidence Details

### Requirement
Compiler observability must include contract markers, bounded labels, and trace continuity.

### Tests to execute
- metrics scrape validation
- trace continuity tests
- stage timing tests
- deterministic digest logging tests
- validation failure observability tests

### Expected result
The compiler emits bounded, stable observability data without leaking unbounded identifiers.

### Known limitations
- None once metrics and trace tests are complete.

---

## 7. W3-E06 Evidence Details

### Requirement
Wave 3 closure documentation must have no unresolved `TBD` values for completed items.

### Artifacts
- `docs/development/wave-3/product-1.0-wave-3-compatibility-report.md`
- `docs/development/wave-3/product-1.0-wave-3-release-readiness-checklist.md`

### Expected result
Compatibility rows, release notes drafts, and migration notes are complete for all completed issues.

---

## 8. W3-E07 Evidence Details

### Requirement
Parent plan and inventory must reflect the Wave 3 concrete paths and conformance mappings.

### Artifacts
- `docs/development/product-1.0-contract-alignment-plan.md`
- `docs/development/product-1.0-contract-inventory.md`

### Expected result
The plan and inventory include the concrete compiler/AQO/QFS paths and a clean handoff to Wave 4.

---

## 9. W3-E08 Evidence Details

### Requirement
A governance decision must exist explaining whether Wave 3 needs new RFC/ADR work.

### Artifacts
- `docs/development/wave-3/product-1.0-wave-3-rfc-adr-gap-analysis.md`
- RFC/ADR, if required

### Expected result
The record clearly states either:
- no new governance is needed, or
- a new RFC/ADR has been approved and linked.

---

## 10. Known limitations template

Known limitations for Wave 3 closure must be recorded here before release. Examples that require explicit acceptance if present:

- some compiler diagnostics remain fixture-backed rather than production-durable;
- AQO sidecar artifacts are advisory rather than authoritative;
- QFS integrity verification is present only for a subset of storage profiles;
- observability labels are bounded but a subset of dashboards is still deferred to Wave 4;
- optimizer hook artifacts are emitted but not yet production-promoted.

---

## 11. Wave 3 acceptance mapping

| Acceptance criterion | Evidence IDs | Status |
|---|---|---|
| Accepted Eigen-Lang subset is explicit and test-covered | W3-E01 | Pending |
| Compiler request mapping is deterministic and versioned | W3-E02 | Pending |
| AQO output is canonical and reproducible | W3-E03 | Pending |
| Compiler outputs persist through QFS with lineage | W3-E04 | Pending |
| Observability is bounded and trace-continuous | W3-E05 | Pending |
| Compatibility and migration closure is complete | W3-E06 | Pending |
| Inventory and parent plan are synchronized | W3-E07 | Pending |
| Governance decision is explicit | W3-E08 | Pending |

---

## 12. Closure statement

**Wave 3 Status: EVIDENCE TEMPLATE**

When the evidence rows are populated and all completed items are marked accordingly, Wave 3 can be closed and Wave 4 can begin. Wave 4 may rely on compiler outputs already being deterministic, schema-validated, and persisted through QFS with lineage records.
