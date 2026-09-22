# Product 1.0 Wave 3 Execution Plan

**Wave:** Product 1.0 Wave 3 — Compiler, Eigen-Lang, and AQO closure  
**Status:** Ready for implementation planning  
**Created:** 2026-06-05  
**Parent plan:** `docs/development/product-1.0-contract-alignment-plan.md`  
**Inventory:** `docs/development/product-1.0-contract-inventory.md`  
**Version policy:** `docs/development/product-1.0-version-policy.md`  
**Governance baseline:** `docs/architecture/components/compiler.md`; `docs/reference/eigen-lang.md`; `docs/reference/formats/aqo.md`  
**Sources of truth:** `docs/architecture/**`, `docs/reference/**`

---

## 1. Goal

Wave 3 makes compilation a production-grade deterministic contract boundary. After Wave 2, Kernel/QRTX is the lifecycle authority; Wave 3 uses that stable runtime control plane to align the compiler, Eigen-Lang contract, AQO contract, and compiler-to-QFS artifact handoff to the source-of-truth documentation.

Wave 3 is a **major internal contract alignment wave**. It may change `eigen.internal.v1` compiler behavior, compiler metadata, AQO emission, and compiler artifact persistence details when required to reconcile implementation with the normative references. Public `eigen.api.v1` behavior must remain compatible with Wave 1 unless a separate public RFC/ADR explicitly approves a public change.

---

## 2. Normative source map

| Wave 3 area | Canonical source | Implementation surface | Primary evidence |
|---|---|---|---|
| Eigen-Lang syntax and safety model | `docs/reference/eigen-lang.md`; `docs/architecture/components/compiler.md` | `src/services/eigen-compiler`; grammar/AST validation helpers | Golden parser/allowlist tests |
| Compiler contract and deterministic pipeline | `docs/architecture/components/compiler.md` | `src/services/eigen-compiler`; internal compile RPCs | Stage-by-stage compiler tests |
| AQO canonical format and invariants | `docs/reference/formats/aqo.md` | AQO emitter/validator; compiler result serializers | AQO fixture and schema tests |
| Compiler-to-QFS artifact persistence | `docs/reference/formats/qfs-layout.md`; `docs/architecture/components/qfs.md` | `src/services/eigen-compiler`; `src/rust/crates/qfs` | Artifact layout and persistence tests |
| JobSpec/request mapping | `docs/reference/jobspec.md`; `docs/reference/api/grpc-internal.md` | System API → Kernel/QRTX → compiler request shaping | Request mapping tests |
| Compiler observability | `docs/reference/orchestration-observability-contract.md`; `docs/reference/cluster-runtime-observability-contract.md`; `docs/reference/error-model.md` | Compiler metrics, traces, structured errors | Metrics and trace continuity tests |

---

## 3. Wave 3 scope

### In scope

1. Finalize the accepted Eigen-Lang v1.0 subset and AST allowlist.
2. Remove ambiguous compiler behavior that is not supported by the source-of-truth docs.
3. Enforce import/function/decorator and expression restrictions with canonical error mapping.
4. Align compiler internal requests with JobSpec and Kernel-owned lifecycle context.
5. Produce AQO v1.0 deterministically, including canonical ordering, metadata, and provenance.
6. Validate AQO against the reference contract before returning or persisting it.
7. Persist compiler artifacts through the QFS L3 boundary with explicit metadata and lineage.
8. Emit compiler trace, digest, and bounded-label metrics that prove deterministic behavior.
9. Expand the golden/conformance suite for accepted, rejected, and replayed compile paths.

### Out of scope

- Full Resource Manager scheduling authority closure.
- Full optimizer service productionization beyond the declared post-AQO hook surface.
- Public `eigen.api.v1` breaking changes.
- Kernel lifecycle ownership work, which remains a Wave 2 concern.
- Provider-specific backend execution semantics beyond compiler-facing contract hooks.

---

## 4. Delivery sequence

| Step | Issue | Dependency | Outcome |
|---:|---|---|---|
| 1 | W3-01 Eigen-Lang v1.0 grammar/AST allowlist and safety model | Wave 2 closure; source docs stable | Accepted subset, forbidden-construct matrix, and error taxonomy |
| 2 | W3-02 Internal compiler RPC alignment and JobSpec-to-compiler request mapping | W3-01 | Compiler requests carry canonical metadata and versioned semantics |
| 3 | W3-03 AQO canonicalization, schema validation, and deterministic emission | W3-01, W3-02 | AQO bytes are canonical, validated, and reproducible |
| 4 | W3-04 Compiler artifact persistence handoff to QFS | W3-03 | Compiler outputs persist through the QFS contract, not ad-hoc paths |
| 5 | W3-05 Compiler observability, metrics, and replay evidence | W3-02 through W3-04 | Compile traces/metrics/digests are stable and bounded |
| 6 | W3-06 Wave 3 compatibility, migration notes, and exit evidence | All W3 issues | Closure report, readiness checklist, and evidence bundle are complete |

---

## 5. Contract decisions required before implementation

1. **Accepted Eigen-Lang subset:** enumerate every construct that is valid in v1.0 and every construct that must fail with canonical errors.
2. **Input precedence:** confirm how source bytes, source references, and JobSpec metadata are resolved when multiple inputs are present.
3. **AQO metadata minimums:** confirm the required compiler metadata fields and the stable ordering rules for hashes and fixtures.
4. **QFS artifact layout:** confirm the canonical compiler output paths and the metadata records required for lineage and retention.
5. **Optimizer hook surface:** confirm which post-AQO annotations are authoritative versus advisory and how they are serialized.
6. **Internal SemVer policy:** classify compiler and AQO implementation deltas as MAJOR/MINOR/PATCH according to the Product 1.0 version policy.

---

## 6. Definition of done

Wave 3 is 100% complete when:

- The compiler implements the documented Eigen-Lang v1.0 allowlist and rejects forbidden constructs canonically.
- Internal compiler requests, metadata, and versioning match the source-of-truth contracts.
- AQO output is deterministic, schema-validated, and reproducible byte-for-byte for identical inputs.
- Compiler output artifacts persist through the documented QFS boundary with lineage and integrity metadata.
- Compiler observability includes contract markers, bounded labels, deterministic digests, and trace continuity.
- Golden tests cover minimal, parameterized, invalid, unsupported, and repeated compile cases.
- Product 1.0 manifest/inventory are updated when proto/schema/conformance mappings become concrete.
- The Wave 3 compatibility report, release-readiness checklist, and exit evidence bundle have no unresolved `TBD` values.

---

## 7. Handoff to Wave 4

Wave 4 may start when Wave 3 proves that compiler outputs, AQO artifacts, and metadata are persisted through the QFS contract with deterministic hashes and stable lineage records. Wave 4 can then mature QFS storage, checkpoints, and live-resource semantics without reopening compiler ownership or reintroducing ad-hoc artifact paths.
