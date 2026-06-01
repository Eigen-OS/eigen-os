# Product 1.0 Version Policy

**Status:** Wave 0 baseline
**Applies to:** Product `1.0.0` contract-alignment work
**Source of truth:** `docs/architecture/**`, `docs/reference/**`, `contracts/product-1.0/manifest.json`
**Created:** 2026-06-01

---

## 1. Decision

Product `1.0.0` is the release target for the contract-alignment program. It is not the same thing as every individual contract package version in the repository.

Eigen OS uses four version dimensions:

| Dimension | Meaning | Product 1.0 policy |
|---|---|---|
| Product release version | Market/release identity for the integrated platform | The alignment program targets Product `1.0.0`. |
| Contract package version | SemVer for a normative API, schema, wire format, observability surface, or component contract | Each contract keeps its existing SemVer unless Wave 0 explicitly freezes a replacement. Examples: JobSpec `1.0.0`, intelligent-runtime observability `2.1.0`, orchestration observability `3.1.0`. |
| Protobuf namespace version | Stable package/path namespace such as `eigen.api.v1` or `eigen.internal.v1` | `v1` remains a namespace compatibility line, not a Product release number. |
| Implementation package/crate version | Package-manager version for a service, crate, or generated artifact | May remain pre-`1.0.0` until the corresponding Product 1.0 slice is implemented and released. |

Product `1.0.0` therefore means: every contract listed in the Product 1.0 manifest has an owner, a compatibility status, a conformance-test mapping, and release evidence proving enforcement.

---

## 2. Relationship to Eigen OS `1.3.0` architecture language

Some architecture documents describe the target architecture as Eigen OS `1.3.0` because previous phase work used that architecture scope for kernel, data-fabric, policy, and plugin hardening. For the Product 1.0 alignment stream:

1. `docs/architecture/contract-map.md` remains the authoritative boundary map for the mature architecture shape.
2. Product `1.0.0` is the first integrated release target that must align implementation to the mature contract map.
3. Existing contract package versions greater than `1.0.0` are preserved when they already express evolved but backward-compatible contract families.
4. A Product 1.0 release may include contract package versions such as `2.1.0` or `3.1.0` when those contracts are the frozen source of truth for that subsystem.

---

## 3. Freeze rules for Wave 0

During Wave 0, a contract is considered frozen for implementation planning when all of the following are true:

- it is present in `contracts/product-1.0/manifest.json`,
- it has a non-empty owning component,
- it has at least one canonical source document,
- every canonical source document path resolves,
- it has a planned or existing proto/schema mapping,
- it has a planned or existing conformance-test mapping,
- its implementation and compatibility status are explicit.

Wave 1+ implementation PRs MUST update the manifest in the same commit as any change to a Product 1.0 contract source, proto/schema mapping, or conformance-test mapping.

---

## 4. Breaking-change policy

A Wave 1+ change is breaking if it changes any frozen Product 1.0 contract in a way that violates the contract's SemVer policy, removes a documented field/method/metric/error reason, changes lifecycle semantics, changes canonical error mapping, or changes required security/authz behavior.

Breaking changes require:

1. manifest update,
2. migration notes,
3. compatibility report update,
4. conformance fixture update,
5. release evidence entry.

---

## 5. Implementation-status vocabulary

| Status | Meaning |
|---|---|
| `documented` | Source-of-truth contract exists; implementation may be partial. |
| `partial` | Some code/proto/tests exist but do not fully enforce the contract. |
| `planned` | Contract is accepted for Product 1.0 but implementation artifacts are not yet present. |
| `implemented` | Contract is fully enforced with conformance evidence. |

---

## 6. Compatibility-status vocabulary

| Status | Meaning |
|---|---|
| `frozen-for-wave-0` | Contract is stable enough to begin implementation planning. |
| `needs-alignment` | Contract source exists, but implementation/proto/tests are known to lag. |
| `planned` | Contract is in Product 1.0 scope but requires future schema/proto/test work. |
| `compatible` | Implementation and conformance evidence prove compatibility. |
