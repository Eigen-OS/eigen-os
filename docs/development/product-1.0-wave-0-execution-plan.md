# Product 1.0 Wave 0 Execution Plan

**Status:** Wave 0 implementation guide
**Parent plan:** `docs/development/product-1.0-contract-alignment-plan.md`
**Source of truth:** `docs/architecture/**`, `docs/reference/**`
**Created:** 2026-06-01

---

## 1. Goal

Wave 0 makes Product `1.0.0` implementation unambiguous before service logic changes begin. The wave is complete only when contract ownership, versioning, canonical references, and drift checks are visible and enforceable.

---

## 2. Required deliverables

| Deliverable | Path | Acceptance criteria |
|---|---|---|
| Contract inventory | `docs/development/product-1.0-contract-inventory.md` | One row per Product 1.0 normative contract; every row has owner, source, version, proto/schema mapping, conformance-test mapping, implementation status, and compatibility status. |
| Machine-readable manifest | `contracts/product-1.0/manifest.json` | JSON validates structurally; every contract has owner and conformance-test mapping; all listed source/proto/schema paths either exist or are explicitly marked as planned. |
| Version policy | `docs/development/product-1.0-version-policy.md` | Distinguishes Product release version, contract package version, protobuf namespace version, and implementation package version. |
| Canonical-reference cleanup | Architecture/reference docs | Stale canonical links are redirected or backed by new reference docs. |
| Docs link gate | `scripts/ci/check-docs-links.py` and CI job | Fails when docs under `docs/architecture`, `docs/reference`, or Product 1.0 planning docs point at missing canonical markdown files. |
| Manifest owner/test gate | `scripts/ci/check-product-1-0-manifest.py` and CI job | Fails when a Product 1.0 manifest row has no owner, source, schema/proto mapping, conformance-test mapping, matching inventory row, or resolvable existing path. |

---

## 3. Execution order

1. Freeze version vocabulary using `docs/development/product-1.0-version-policy.md`.
2. Normalize stale architecture/reference links so canonical paths resolve.
3. Populate `docs/development/product-1.0-contract-inventory.md` from source-of-truth docs only.
4. Generate or manually update `contracts/product-1.0/manifest.json` from the inventory.
5. Add and run CI gates:
   - `python3 scripts/ci/check-docs-links.py`
   - `python3 scripts/ci/check-product-1-0-manifest.py`
6. Update README/proto README wording so release identity and protobuf namespace identity are not conflated.
7. Commit Wave 0 baseline artifacts before starting Wave 1 service logic.

---

## 4. Definition of done

Wave 0 is 100% complete when:

- all Product 1.0 contracts are discoverable from the inventory and manifest,
- all contract owners are known,
- every canonical source path resolves,
- Product release/version policy is documented,
- CI can detect missing canonical links in architecture, reference, and Product 1.0 planning docs,
- CI can detect owner/test mapping omissions, inventory/manifest drift, and unresolved existing path mappings,
- no service implementation PR is required to understand the Product 1.0 target.

---

## 5. Wave 1 handoff checklist

Before opening Wave 1 implementation work, confirm:

- public API rows in the manifest have `compatibility_status = needs-alignment` or better,
- JobSpec, error model, and error mapping rows identify concrete test suites,
- stale REST/security links are resolved,
- `proto/README.md` describes `v1` as namespace compatibility rather than MVP product version,
- the repository README describes Product 1.0 as an alignment target, not the current shipped implementation.
